import os
import discord
import asyncio
import pymongo
import random
import time
from collections import deque
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv

creation_timestamps = {}
load_dotenv()

class VoiceStateUpdateQueue:
    def __init__(self):
        self.queue = deque()
        self.is_processing = False

    async def add_to_queue(self, coro):
        self.queue.append(coro)
        if not self.is_processing:
            await self.process_queue()

    async def process_queue(self):
        self.is_processing = True
        while self.queue:
            task = self.queue.popleft()
            coro = task[0] if isinstance(task, tuple) else task
            try:
                await coro
            except Exception as e:
                print(f"An error occurred: {e}")
            await asyncio.sleep(1) 
        self.is_processing = False

class VoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_client = pymongo.MongoClient(os.getenv('MONGO_URI'))
        self.db = self.mongo_client[os.getenv('MONGO_DB')]
        self.voice_channels = self.db['voice_channels']
        self.voice_state_update_queue = VoiceStateUpdateQueue()

    async def on_member_remove(self, member):

        if member.bot:
            guild_id = member.guild.id
            await self.voice_channels.delete_one({"guild_id": guild_id})

    async def on_member_join(self, member):
        guild_id = member.guild.id
        existing_data = await self.voice_channels.find_one({"guild_id": guild_id})

        if existing_data is None:
            system_channel = member.guild.system_channel
            if system_channel is not None:
                bot_ctx = await self.bot.get_context(system_channel)
                await bot_ctx.invoke(self.setup)
            else:
                # Handle the case where there's no system channel
                # You might want to send a message to a default channel or log an error.
                pass

    async def on_guild_remove(self, guild):
        guild_id = guild.id
        self.voice_channels.delete_one({"guild_id": guild_id})

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # Get the channel and message where the reaction was added
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        # Check if the reaction is in the 'vc-dashboard' text channel
        if channel.name == 'vc-dashboard':
            # Get the member who added the reaction
            member = payload.member or await channel.guild.fetch_member(payload.user_id)

            # Update state or perform actions
            # ...
            print(f"{member.name} reacted with {payload.emoji.name} in the 'vc-dashboard' channel.")


    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        
        if before.channel != after.channel:
            guild_id = member.guild.id
            temp_channels_data = self.voice_channels.find_one({"guild_id": member.guild.id})
            
            # Retrieve 'voice_channel_id' from 'temp_channels_data'
            marked_channel_id = temp_channels_data.get("voice_channel_id") if temp_channels_data else None
            
            if after.channel and marked_channel_id and after.channel.id == marked_channel_id:
                guild = member.guild
                marked_channel = guild.get_channel(marked_channel_id)
                
                # Copy the permission overwrites from the marked channel
                overwrites = marked_channel.overwrites

                # Ensure the bot and the member have the necessary permissions
                overwrites[guild.me] = discord.PermissionOverwrite(connect=True, manage_channels=True, manage_roles=True)
                overwrites[member] = discord.PermissionOverwrite(connect=True, manage_channels=True)

                channel_name = f"{member.display_name}'s channel"
                category = after.channel.category  # Assuming the temp channel should be in the same category
                temp_channel = await category.create_voice_channel(
                    name=channel_name,
                    overwrites=overwrites,
                    bitrate=marked_channel.bitrate,
                    user_limit=marked_channel.user_limit
                )
                await member.move_to(temp_channel)

                # Save the creation time in both 'creation_timestamps' and database
                creation_time = time.time()
                creation_timestamps[temp_channel.id] = creation_time
                
                # Update the database with the new temporary channel information
                self.voice_channels.update_one(
                    {"guild_id": guild_id},
                    {"$addToSet": {
                        "temp_channels": {
                            "channel_id": temp_channel.id,
                            "owner_id": member.id,
                            "creation_time": creation_time  # Save as 'creation_time' for consistency
                        }
                    }},
                    upsert=True
                )

        if before.channel:
            temp_channels_data = self.voice_channels.find_one({"guild_id": member.guild.id})
            if temp_channels_data:
                for channel_info in temp_channels_data["temp_channels"]:
                    channel_id = channel_info.get("voice_channel_id")
                    owner_id = channel_info.get("owner_id")
                    creation_time = channel_info.get("creation_time")  
                    if before.channel.id == channel_id and member.id == owner_id:
                        temp_channel = before.channel
                        if temp_channel:
                            current_time = time.time()
                            # Use loaded creation_time in your check
                            if creation_time is not None and current_time - creation_time > 15:  # 15 secs threshold
                                members = temp_channel.members
                                if member not in members:
                                    if members:
                                        new_owner = random.choice(members)
                                        overwrites = temp_channel.overwrites
                                        overwrites[new_owner] = discord.PermissionOverwrite(connect=True, manage_channels=True)
                                        # Remove the original owner's overwrites if they exist
                                        if member in overwrites:
                                            overwrites.pop(member)
                                        coro = temp_channel.edit(overwrites=overwrites)
                                        await self.voice_state_update_queue.add_to_queue(coro)
                                        coro = temp_channel.edit(name=f"{new_owner.display_name}'s channel")
                                        await self.voice_state_update_queue.add_to_queue(coro)

                    for guild_data in self.voice_channels.find({}):
                        guild = self.bot.get_guild(guild_data["guild_id"])
                        if guild:
                            for channel_info in guild_data.get("temp_channels", []):
                                channel_id = channel_info if isinstance(channel_info, int) else channel_info["channel_id"]

                                channel = guild.get_channel(channel_id)
                                if channel and not channel.members:
                                    current_time = time.time()
                                    # Use loaded creation_time in your check
                                    if current_time - (creation_time or 0) > 3:  # 3 secs threshold
                                        self.voice_channels.update_one(
                                            {"guild_id": guild_data["guild_id"]},
                                            {"$pull": {"temp_channels": channel_id if isinstance(channel_info, int) else {"channel_id": channel_id}}}
                                        )
                                        try:
                                            await channel.delete()
                                            # No need to remove from creation_timestamps since we're using database time
                                        except Exception as e:
                                            print(f"Failed to delete channel {channel_id}: {e}")
                                    else:
                                        # print(f"Channel {channel_id} has not existed long enough to be deleted.")
                                        pass

    @commands.command()
    async def setup(self, ctx):
        if ctx.author.guild_permissions.administrator:
            await ctx.message.delete()
            initial_embed = discord.Embed(
                title="Set or Create a Temporary Channel",
                description="Choose an option:\nOption 1: Select an Existing Channel\nOption 2: Create a New Channel",
                color=discord.Color.blue()
            )
            button1 = Button(style=discord.ButtonStyle.primary, label="Select Existing Channel", custom_id="select_existing")
            button2 = Button(style=discord.ButtonStyle.primary, label="Create New Channel", custom_id="create_new")
            view = View()
            view.add_item(button1)
            view.add_item(button2)
            message = await ctx.send(embed=initial_embed, view=view)
            
            def check(interaction):
                return interaction.user == ctx.author and interaction.message == message
            
            try:
                interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
                await interaction.response.defer()
                
                await message.delete()
                if interaction.data['custom_id'] == "select_existing":
                    await self.handle_select_existing(ctx, message)
                elif interaction.data['custom_id'] == "create_new":
                    await self.handle_create_new(ctx, message)
                
            except asyncio.TimeoutError:
                await ctx.send("You took too long to react.")
        else:
            await ctx.send("Only administrators can use this command.")
            await ctx.message.delete()


    async def handle_select_existing(self, ctx, message):
        initial_embed = discord.Embed(
            title="Select an Existing Channel",
            description="Please select the channel you want to use by clicking on the corresponding button.",
            color=discord.Color.green()
        )
        guild = ctx.guild
        existing_channels = guild.voice_channels
        if not existing_channels:
            await ctx.send("No existing voice channels to select.")
            return

        # Create buttons for each existing channel
        view = discord.ui.View()
        for index, channel in enumerate(existing_channels):
            button = discord.ui.Button(style=discord.ButtonStyle.primary, label=f"{channel.name}", custom_id=f"select_{index}")
            view.add_item(button)

        initial_message = await ctx.send(embed=initial_embed, view=view)

        # Check function for interaction
        def check(interaction):
            return interaction.user == ctx.author and interaction.message.id == initial_message.id

        try:
            # Wait for the button interaction
            interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
            
            # Check if the interaction has already been responded to
            if interaction.response.is_done():
                await ctx.send("This interaction has already been handled.")
                return
            
            # Defer the interaction if it hasn't been responded to
            await interaction.response.defer()

            selected_channel_index = int(interaction.data['custom_id'].split('_')[-1])
            if 0 <= selected_channel_index < len(existing_channels):
                selected_channel = existing_channels[selected_channel_index]
                guild_id = ctx.guild.id
                voice_channel_id = selected_channel.id
                
                # Find text channel called 'vc-dashboard'
                text_channel = discord.utils.get(guild.text_channels, name='vc-dashboard')
                if text_channel is None:
                    await ctx.send("Text channel 'vc-dashboard' not found.")
                    return

                text_channel_id = text_channel.id

                self.voice_channels.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"voice_channel_id": voice_channel_id, "text_channel_id": text_channel_id}},
                    upsert=True
                )
                await initial_message.delete()
                confirmation_message = await ctx.send(f"You selected the channel <#{selected_channel.id}> and it has been stored in the database.")
                await asyncio.sleep(5)
                await confirmation_message.delete()
            else:
                await initial_message.delete()
                confirmation_message = await ctx.send("Invalid selection.")
                await asyncio.sleep(5)
                await confirmation_message.delete()
        except asyncio.TimeoutError:
            await initial_message.delete()
            confirmation_message = await ctx.send("You took too long to select.")
            await asyncio.sleep(5)
            await confirmation_message.delete()

    async def handle_create_new(self, ctx, message):
        existing_channel = self.voice_channels.find_one({"guild_id": ctx.guild.id})
        if existing_channel:
            confirmation_message = await ctx.send("A marked voice channel already exists in this server.")
            await asyncio.sleep(5)
            await confirmation_message.delete()
            return

        initial_embed = discord.Embed(
            title="Create New Marked Channels",
            description="Select a category to create a new voice and text channel.",
            color=discord.Color.blue()
        )
        server_categories = ctx.guild.categories
        if not server_categories:
            await ctx.send("No categories available to create channels.")
            return

        # Create buttons for each category
        view = View()
        for index, category in enumerate(server_categories):
            button = Button(style=discord.ButtonStyle.primary, label=f"{category.name}", custom_id=f"create_{index}")
            view.add_item(button)

        message = await ctx.send(embed=initial_embed, view=view)

        # Check function for interaction
        def check(interaction):
            return interaction.user == ctx.author and interaction.message.id == message.id

        try:
            # Wait for the button interaction
            interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
            selected_category_index = int(interaction.data['custom_id'].split('_')[-1])
            if 0 <= selected_category_index < len(server_categories):
                selected_category = server_categories[selected_category_index]
                new_voice_channel = await selected_category.create_voice_channel("⌛｜Create")
                new_text_channel = await selected_category.create_text_channel("vc-dashboard")

                # buttons = [discord.ui.Button(label=f'Button {i}', style=discord.ButtonStyle.primary) for i in range(1, 5)]
                
                # await new_text_channel.send('Choose an option:', view=discord.ui.View(*buttons))
                
                guild_id = ctx.guild.id
                voice_channel_id = new_voice_channel.id
                text_channel_id = new_text_channel.id
                self.voice_channels.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"voice_channel_id": voice_channel_id, "text_channel_id": text_channel_id}},
                    upsert=True
                )
                await message.delete()
                confirmation_message = await ctx.send(f"Created new voice channel <#{new_voice_channel.id}> and text channel <#{new_text_channel.id}> in the <#{selected_category.id}> category.")
                await asyncio.sleep(5)
                await confirmation_message.delete()
            else:
                await message.delete()
                confirmation_message = await ctx.send("Invalid selection.")
                await asyncio.sleep(5)
                await confirmation_message.delete()
        except asyncio.TimeoutError:
            await message.delete()
            confirmation_message = await ctx.send("You took too long to select.")
            await asyncio.sleep(5)
            await confirmation_message.delete()

async def setup(bot):
    await bot.add_cog(VoiceChannels(bot))