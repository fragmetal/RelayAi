import os
import discord
import asyncio
import pymongo
import random
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

class VoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_client = pymongo.MongoClient(os.getenv('MONGO_URI'))
        self.db = self.mongo_client[os.getenv('MONGO_DB')]
        self.voice_channels = self.db['voice_channels']
        self.marked_channel_id = None  # Initialize as None
        # Load data from the database when the bot starts
        self.load_data()
        self.check_temp_channels.start()

    def cog_unload(self):
        self.check_temp_channels.cancel()

    def load_data(self):
        # Initialize a dictionary to store marked channel IDs for each guild
        self.marked_channels = {}
        
        # Fetch data from the database and populate variables as needed
        for guild_data in self.voice_channels.find({}):
            guild_id = guild_data["guild_id"]
            marked_channel_id = guild_data.get("channel_id")

            # Update the marked_channels dictionary for the guild
            if marked_channel_id:
                self.marked_channels[guild_id] = marked_channel_id

    @tasks.loop(seconds=2)
    async def check_temp_channels(self):                       
        # Check for and delete empty temporary channels
        for guild_data in self.voice_channels.find({}):
            guild = self.bot.get_guild(guild_data["guild_id"])
            if guild:
                for channel_id in guild_data.get("temp_channels", []):
                    channel = guild.get_channel(channel_id)
                    if channel and not channel.members:
                        # Remove the database record
                        self.voice_channels.update_one(
                            {"guild_id": guild_data["guild_id"]},
                            {"$pull": {"temp_channels": channel_id}}
                        )
                        await channel.delete()

    async def on_member_remove(self, member):
        # This method is called when a member leaves a guild.
        # Check if the member is the bot and delete data if necessary.
        if member.bot:
            guild_id = member.guild.id
            # Assuming you have a MongoDB connection and voice_channels collection defined
            await self.voice_channels.delete_one({"guild_id": guild_id})

    async def on_member_join(self, member):
        # Check if the guild exists in the database
        guild_id = member.guild.id
        existing_data = await self.voice_channels.find_one({"guild_id": guild_id})

        if existing_data is None:
            # The guild doesn't exist in the database, handle setup appropriately
            system_channel = member.guild.system_channel
            if system_channel is not None:
                bot_ctx = await self.bot.get_context(system_channel)
                # Assuming you have a setup command defined
                await bot_ctx.invoke(self.setup)
            else:
                # Handle the case where there's no system channel
                # You might want to send a message to a default channel or log an error.
                pass

    async def on_guild_remove(self, guild):
        # Remove data associated with the guild from the database
        guild_id = guild.id
        self.voice_channels.delete_one({"guild_id": guild_id})
    
    async def create_temp_channel(self, member, voice_channel_id):
        guild = member.guild
        
        if guild and voice_channel_id:
            voice_channel = discord.utils.get(guild.voice_channels, id=voice_channel_id)
            if not voice_channel:
                return None

            # Copy the permissions of the voice channel
            overwrites = voice_channel.overwrites

            # Add or update specific permissions for the guild's default role, the bot itself, and the member
            overwrites[guild.default_role] = discord.PermissionOverwrite(connect=False)
            overwrites[guild.me] = discord.PermissionOverwrite(connect=True, manage_channels=True)
            overwrites[member] = discord.PermissionOverwrite(connect=True, manage_channels=True, manage_roles=True)
            
            channel_name = f"⌛｜{member.display_name}'s channel"

            temp_channel = await voice_channel.category.create_voice_channel(
                name=channel_name,
                overwrites=overwrites,
                bitrate=voice_channel.bitrate,
                user_limit=voice_channel.user_limit
            )
            # Move the member to the created temporary channel
            await member.move_to(temp_channel)

            return temp_channel
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):

        if before.channel != after.channel:
            # Check if a user joins the marked voice channel
            if after.channel and after.channel.id == self.marked_channels.get(after.channel.guild.id):
                # Pass the voice channel ID that the user joined
                voice_channel_id = after.channel.id
                temp_channel = await self.create_temp_channel(member, voice_channel_id)
                # Store the temporary channel id in the database if temp_channel is not None
                if temp_channel:
                    guild_id = after.channel.guild.id
                    channel_id = temp_channel.id
                    self.voice_channels.update_one(
                        {"guild_id": guild_id},
                        {"$addToSet": {"temp_channels": channel_id}},
                        upsert=True  # Create a new document if it doesn't exist
                    )

        # Check if the member has left a temporary channel
        temp_channels = self.voice_channels.find_one({"guild_id": member.guild.id})["temp_channels"] if self.voice_channels.find_one({"guild_id": member.guild.id}) else []
        if before.channel and before.channel.id in temp_channels:
            # Get the channel and its members
            temp_channel = before.channel
            members = temp_channel.members

            # If the channel is not empty after the creator leaves
            if members:
                # Randomly select a new owner from the current members
                new_owner = random.choice(members)

                # Update the overwrites for the new owner
                overwrites = temp_channel.overwrites
                overwrites[new_owner] = discord.PermissionOverwrite(connect=True, manage_channels=True, manage_roles=True)

                # Remove the old owner's permissions
                if member in overwrites:
                    del overwrites[member]

                # Apply the updated permissions
                await temp_channel.edit(overwrites=overwrites)

                # Change the channel name to the new owner's name
                new_channel_name = f"⌛｜{new_owner.display_name}'s channel"
                await temp_channel.edit(name=new_channel_name)
            else:
                # If the channel is empty, consider deleting it or handling it accordingly
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