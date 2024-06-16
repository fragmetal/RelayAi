import os
import discord
import asyncio
import pymongo
import random
import time
from collections import deque
from discord.ext import commands
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
        self.marked_channel_id = None
        self.load_data()
        self.voice_state_update_queue = VoiceStateUpdateQueue()

    def load_data(self):
        self.marked_channels = {}
        
        for guild_data in self.voice_channels.find({}):
            guild_id = guild_data["guild_id"]
            marked_channel_id = guild_data.get("channel_id")

            if marked_channel_id:
                self.marked_channels[guild_id] = marked_channel_id

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
    async def on_voice_state_update(self, member, before, after):
        if before.channel != after.channel:
            guild_id = member.guild.id
            marked_channel_id = self.marked_channels.get(guild_id)
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

        if after.channel:
            temp_channels_data = self.voice_channels.find_one({"guild_id": member.guild.id})
            if temp_channels_data:
                for channel_info in temp_channels_data["temp_channels"]:
                    channel_id = channel_info.get("channel_id")
                    owner_id = channel_info.get("owner_id")

                    if after.channel.id == channel_id and member.id == owner_id:
                        temp_channel = after.channel
                        if temp_channel:
                            await asyncio.sleep(900)  # 15 minutes delay
                            # Retrieve the current permission overwrites for the channel
                            overwrites = temp_channel.overwrites

                            # Check if there are overwrites for the member and remove them
                            if member in overwrites:
                                overwrites.pop(member)

                            # Set new overwrites for the owner with the desired permissions
                            owner_overwrites = discord.PermissionOverwrite(connect=True, manage_channels=True, manage_roles=True)
                            overwrites[member.guild.get_member(owner_id)] = owner_overwrites

                            # Apply the updated overwrites to the channel
                            await self.voice_state_update_queue.add_to_queue((temp_channel.edit(overwrites=overwrites), "Permission overwrite"))

                            # Rename the channel to reflect the new owner's name
                            await self.voice_state_update_queue.add_to_queue((temp_channel.edit(name=f"{member.guild.get_member(owner_id).display_name}'s channel"), "Channel rename"))

        if before.channel:
            temp_channels_data = self.voice_channels.find_one({"guild_id": member.guild.id})
            if temp_channels_data:
                for channel_info in temp_channels_data["temp_channels"]:
                    channel_id = channel_info.get("channel_id")
                    owner_id = channel_info.get("owner_id")
                    creation_time = channel_info.get("creation_time")  # Load creation_time
                    if before.channel.id == channel_id and member.id == owner_id:
                        temp_channel = before.channel
                        if temp_channel:
                            current_time = time.time()
                            # Use loaded creation_time in your check
                            if current_time - creation_time > 15:  # 15 secs threshold
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
                                    # Check if the channel has been around for at least x minutes
                                    if channel_id in creation_timestamps and current_time - creation_timestamps[channel_id] > 5:  # 5 seconds
                                        self.voice_channels.update_one(
                                            {"guild_id": guild_data["guild_id"]},
                                            {"$pull": {"temp_channels": channel_id if isinstance(channel_info, int) else {"channel_id": channel_id}}}
                                        )
                                        try:
                                            await channel.delete()
                                            # Remove the channel from the creation timestamps dictionary
                                            del creation_timestamps[channel_id]
                                        except Exception as e:
                                            print(f"Failed to delete channel {channel_id}: {e}")
                                    else:
                                        # print(f"Channel {channel_id} has not existed long enough to be deleted.")
                                        pass

    @commands.command()
    async def setup(self, ctx):
        # Check if the user invoking the command is an administrator
        if ctx.author.guild_permissions.administrator:
            # Create a Discord Embed for the initial 
            await ctx.message.delete()  # Delete the user's message
            initial_embed = discord.Embed(
                title="Set or Create a Temporary Channel",
                description="Choose an option:\nOption 1: Select an Existing Channel\nOption 2: Create a New Channel",
                color=discord.Color.blue()
            )

            # Send the initial embedded message with reaction options
            message = await ctx.send(embed=initial_embed)
            await message.add_reaction("1️⃣")  # Option 1: Select an Existing Channel
            await message.add_reaction("2️⃣")  # Option 2: Create a New Channel

            # Define a check for the reaction event
            def check(reaction, user):
                return user == ctx.author and reaction.message == message

            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
                await message.delete()  # Delete the bot's message
                if str(reaction.emoji) == "1️⃣":
                    await self.handle_select_existing(ctx, message)
                elif str(reaction.emoji) == "2️⃣":
                    await self.handle_create_new(ctx, message)
            except asyncio.TimeoutError:
                await ctx.send("You took too long to react.")
        else:
            await ctx.send("Only administrators can use this command.")
            await ctx.message.delete()  # Delete the user's message

    async def handle_select_existing(self, ctx, message):
        # Logic for selecting an existing channel
        initial_embed = discord.Embed(
            title="Select an Existing Channel",
            description="Please react with the number corresponding to the channel you want to use.",
            color=discord.Color.green()
        )

        guild = ctx.guild
        existing_channels = guild.voice_channels

        if not existing_channels:
            await ctx.send("No existing voice channels to select.")
            return

        options = [f"{index + 1}. {channel.name}" for index, channel in enumerate(existing_channels)]

        # Display existing channels as a numbered list
        channels_list = "\n".join(options)
        initial_embed.add_field(name="Available Channels", value=channels_list)

        # Send the initial embedded message for selecting existing channels
        initial_message = await ctx.send(embed=initial_embed)

        for index in range(len(existing_channels)):
            await initial_message.add_reaction(f"{index + 1}\u20e3")  # Add reactions for each channel

        # Define a check for the reaction event
        def check(reaction, user):
            return user == ctx.author and reaction.message.id == initial_message.id

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)

            # Find the selected channel based on the reaction
            selected_channel_index = int(str(reaction.emoji)[:-1]) - 1

            if 0 <= selected_channel_index < len(existing_channels):
                selected_channel = existing_channels[selected_channel_index]

                # Store the selected channel's information in your database for the specific guild
                guild_id = ctx.guild.id
                channel_id = selected_channel.id
                self.voice_channels.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"channel_id": channel_id}},
                    upsert=True  # Create a new document if it doesn't exist
                )
                self.marked_channels[guild_id] = channel_id
                # Delete the initial message and previous reactions
                await initial_message.delete()
                # Send a confirmation message and delete it after 5 seconds
                confirmation_message = await ctx.send(f"You selected the channel <#{selected_channel.id}> and it has been stored in the database.")
                await asyncio.sleep(5)  # Sleep for 5 seconds
                await confirmation_message.delete()  # Delete the confirmation message
            else:
                await initial_message.delete()
                confirmation_message = await ctx.send("Invalid selection.")
                await asyncio.sleep(5)  # Sleep for 5 seconds
                await confirmation_message.delete()  # Delete the confirmation message
        except asyncio.TimeoutError:
            await initial_message.delete()
            confirmation_message = await ctx.send("You took too long to react.")
            await asyncio.sleep(5)  # Sleep for 5 seconds
            await confirmation_message.delete()  # Delete the confirmation message

    async def handle_create_new(self, ctx, message):
        # Check if the guild already has a marked voice channel
        if self.get_marked_channel_id(ctx.guild.id):
            confirmation_message =await ctx.send("A marked voice channel already exists in this server.")
            await asyncio.sleep(5)  # Sleep for 5 seconds
            await confirmation_message.delete()  # Delete the confirmation message
            return

        # Create a Discord Embed for the initial message with dynamic description
        initial_embed = discord.Embed(
            title="Create a New Marked Voice Channel",
            color=discord.Color.blue()
        )

        # Fetch the server's categories
        server_categories = ctx.guild.categories

        # Dynamically generate the description with available categories and emojis
        description = "Please choose a category for the new voice channel by reacting to this message.\n\n"

        category_emojis = {}
        for index, category in enumerate(server_categories):
            # Customize this logic to determine emojis for each category as needed
            # For now, it just uses numbers 1️⃣, 2️⃣, 3️⃣, ...
            emoji = f"{index + 1}\u20e3"
            category_emojis[emoji] = category
            description += f"{emoji} - {category.name}\n"

        initial_embed.description = description

        # Send the initial embedded message with reaction options
        message = await ctx.send(embed=initial_embed)

        # Add reactions for available categories based on the dynamically generated dictionary
        for emoji in category_emojis.keys():
            await message.add_reaction(emoji)

        # Define a check for the reaction event
        def check(reaction, user):
            return user == ctx.author and reaction.message == message and str(reaction.emoji) in category_emojis

        try:
            reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)

            # Find the selected category based on the reaction emoji
            selected_category = category_emojis[str(reaction.emoji)]

            new_channel = await selected_category.create_voice_channel("⌛｜Create")

            # Store the new channel's information in the database for the specific guild
            guild_id = ctx.guild.id
            channel_id = new_channel.id
            self.voice_channels.update_one(
                {"guild_id": guild_id},
                {"$set": {"channel_id": channel_id}},
                upsert=True  # Create a new document if it doesn't exist
            )
            self.marked_channels[guild_id] = channel_id
            # Delete the initial message and previous reactions
            await message.delete()
            confirmation_message = await ctx.send(f"Created a new voice channel <#{new_channel.id}> in the <#{selected_category.id}> category.")
            await asyncio.sleep(5)  # Sleep for 5 seconds
            await confirmation_message.delete()  # Delete the confirmation message
        except asyncio.TimeoutError:
            confirmation_message = await ctx.send("You took too long to react.")
            await asyncio.sleep(5)  # Sleep for 5 seconds
            await confirmation_message.delete()  # Delete the confirmation message

    def get_marked_channel_id(self, guild_id):
        # Helper function to get the marked channel ID for a specific guild
        document = self.voice_channels.find_one({"guild_id": guild_id})
        if document:
            return document.get("channel_id")
        else:
            return None

async def setup(bot):
    await bot.add_cog(VoiceChannels(bot))