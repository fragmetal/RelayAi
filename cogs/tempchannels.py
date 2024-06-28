import os
import discord
import asyncio
import pymongo
import time
from collections import deque
from discord import Embed
from discord.ext import commands
from discord.ui import Button, Select, View
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

    async def on_guild_remove(self, guild):
        guild_id = guild.id
        self.voice_channels.delete_one({"guild_id": guild_id})

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.user.mentioned_in(message) and not message.author.bot:
            await message.delete()  # Hapus mentionan user yang memanggil bot
            embed = Embed(
                title="Halo!",
                description=f"Halo, ada yang bisa saya bantu?",
                color=discord.Color.blue()
            )
            button = Button(label="Setup", style=discord.ButtonStyle.primary, custom_id="setup_button")
            view = View()
            view.add_item(button)
            sent_message = await message.channel.send(embed=embed, view=view)
            
            async def button_callback(interaction):
                await sent_message.delete()
            
            button.callback = button_callback

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.user.voice and interaction.user.voice.channel:
                voice_channel = interaction.user.voice.channel
            else:
                await interaction.response.send_message("Anda tidak berada di voice channel!", ephemeral=True, delete_after=3)
                return

            members = voice_channel.members
            temp_channels_data = self.voice_channels.find_one({"guild_id": interaction.guild.id})
            if temp_channels_data:
                owner_id = None
                for channel_info in temp_channels_data["temp_channels"]:
                    if channel_info.get("channel_id") == voice_channel.id:
                        owner_id = channel_info.get("owner_id")

            if interaction.data["custom_id"] == "setup_button":
                if not interaction.user.guild_permissions.administrator:
                    await interaction.response.send_message("Only administrators can use this command.", ephemeral=True)
                    return

                await interaction.response.defer()
                initial_embed = discord.Embed(
                    title="Set or Create a Temporary Channel",
                    description="Choose an option from the dropdown below:",
                    color=discord.Color.blue()
                )
                options = [
                    discord.SelectOption(label="Select Existing Channel", value="select_existing"),
                    discord.SelectOption(label="Create New Channel", value="create_new")
                ]
                select = Select(placeholder="Choose an option...", options=options)
                view = View()
                view.add_item(select)
                message = await interaction.followup.send(embed=initial_embed, view=view)
                
                def check(interaction):
                    return interaction.user == interaction.user and interaction.message == message
                
                try:
                    interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
                    
                    # Check if the interaction has already been responded to
                    if not interaction.response.is_done():
                        await interaction.response.defer()
                    
                    await message.delete()
                    if interaction.data['values'][0] == "select_existing":
                        await self.handle_select_existing(interaction, message)
                    elif interaction.data['values'][0] == "create_new":
                        await self.handle_create_new(interaction, message)
                    
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to react.")

            elif interaction.data["custom_id"] == "button_1":
                if temp_channels_data:
                    if owner_id and interaction.user.id != owner_id:
                        if owner_id not in [member.id for member in members]:
                            # Pemilik lama tidak ada di voice channel, ambil alih kepemilikan
                            for channel_info in temp_channels_data["temp_channels"]:
                                if channel_info.get("channel_id") == voice_channel.id:
                                    channel_info["owner_id"] = interaction.user.id
                                    self.voice_channels.update_one(
                                        {"guild_id": interaction.guild.id, "temp_channels.channel_id": voice_channel.id},
                                        {"$set": {"temp_channels.$.owner_id": interaction.user.id}}
                                    )
                                    await voice_channel.edit(name=f"{interaction.user.display_name}'s channel")
                                    embed = discord.Embed(description="Anda sekarang adalah pemilik voice channel ini!", color=discord.Color.green())
                                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                                    return
                        else:
                            embed = discord.Embed(description="Pemilik lama masih berada di voice channel!", color=discord.Color.red())
                            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                    else:
                        embed = discord.Embed(description="Anda sudah menjadi pemilik voice channel ini atau data tidak ditemukan!", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                else:
                    embed = discord.Embed(description="Data voice channel tidak ditemukan!", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
            elif interaction.data["custom_id"] == "button_2":
                if temp_channels_data:
                    if owner_id and interaction.user.id == owner_id:
                        await self.voice_state_update_queue.add_to_queue(voice_channel.edit(user_limit=0))
                        embed = discord.Embed(description="Voice channel dibuka kuncinya!", color=discord.Color.green())
                        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                    else:
                        embed = discord.Embed(description="Anda bukan pemilik voice channel ini!", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                else:
                    embed = discord.Embed(description="Data voice channel tidak ditemukan!", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
            elif interaction.data["custom_id"] == "button_3":
                if temp_channels_data:
                    if owner_id and interaction.user.id == owner_id:
                        member_count = len(voice_channel.members)
                        await self.voice_state_update_queue.add_to_queue(voice_channel.edit(user_limit=member_count))
                        embed = discord.Embed(description=f"Voice channel dikunci untuk {member_count} member!", color=discord.Color.green())
                        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                    else:
                        embed = discord.Embed(description="Anda bukan pemilik voice channel ini!", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                else:
                    embed = discord.Embed(description="Data voice channel tidak ditemukan!", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
            elif interaction.data["custom_id"] == "button_4":
                if temp_channels_data:
                    if owner_id and interaction.user.id == owner_id:
                        options = [
                            discord.SelectOption(label=member.display_name, value=str(member.id))
                            for member in members if not member.bot and member.id != interaction.user.id
                        ]

                        if options:
                            select = discord.ui.Select(placeholder="Pilih member untuk di-mute", options=options)

                            async def select_callback(interaction):
                                member_id = int(select.values[0])
                                member = voice_channel.guild.get_member(member_id)
                                if member:
                                    # Tambahkan permission overwrite untuk mute member di voice channel ini
                                    overwrite = discord.PermissionOverwrite()
                                    overwrite.speak = False
                                    await voice_channel.set_permissions(member, overwrite=overwrite)
                                    embed = discord.Embed(description=f"{member.display_name} telah di-mute di voice channel ini!", color=discord.Color.green())
                                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                                else:
                                    embed = discord.Embed(description="Member tidak ditemukan!", color=discord.Color.red())
                                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)

                            select.callback = select_callback
                            view = discord.ui.View()
                            view.add_item(select)
                            embed = discord.Embed(description="Pilih member untuk di-mute:", color=discord.Color.blue())
                            await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=3)
                        else:
                            embed = discord.Embed(description="Tidak ada member yang bisa di-mute!", color=discord.Color.red())
                            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                    else:
                        embed = discord.Embed(description="Anda bukan pemilik voice channel ini!", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                else:
                    embed = discord.Embed(description="Data voice channel tidak ditemukan!", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
            elif interaction.data["custom_id"] == "button_5":
                if temp_channels_data:
                    if owner_id and interaction.user.id == owner_id:
                        options = [
                            discord.SelectOption(label=member.display_name, value=str(member.id))
                            for member in members if not member.bot and member.id != interaction.user.id
                        ]

                        if options:
                            select = discord.ui.Select(placeholder="Pilih member untuk di-unmute", options=options)

                            async def select_callback(interaction):
                                member_id = int(select.values[0])
                                member = voice_channel.guild.get_member(member_id)
                                if member:
                                    # Hapus permission overwrite untuk unmute member di voice channel ini
                                    await voice_channel.set_permissions(member, overwrite=None)
                                    embed = discord.Embed(description=f"{member.display_name} telah di-unmute di voice channel ini!", color=discord.Color.green())
                                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                                else:
                                    embed = discord.Embed(description="Member tidak ditemukan!", color=discord.Color.red())
                                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)

                            select.callback = select_callback
                            view = discord.ui.View()
                            view.add_item(select)
                            embed = discord.Embed(description="Pilih member untuk di-unmute:", color=discord.Color.blue())
                            await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=3)
                        else:
                            embed = discord.Embed(description="Tidak ada member yang bisa di-unmute!", color=discord.Color.red())
                            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                    else:
                        embed = discord.Embed(description="Anda bukan pemilik voice channel ini!", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                else:
                    embed = discord.Embed(description="Data voice channel tidak ditemukan!", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
            elif interaction.data["custom_id"] == "button_6":
                if temp_channels_data:
                    if owner_id and interaction.user.id == owner_id:
                        options = [
                            discord.SelectOption(label=member.display_name, value=str(member.id))
                            for member in members if not member.bot and member.id != interaction.user.id
                        ]

                        if options:
                            select = discord.ui.Select(placeholder="Pilih member untuk di-ban", options=options)

                            async def select_callback(interaction):
                                member_id = int(select.values[0])
                                member = voice_channel.guild.get_member(member_id)
                                if member:
                                    # Tambahkan permission overwrite untuk mencegah member kembali ke voice channel ini
                                    overwrite = discord.PermissionOverwrite()
                                    overwrite.connect = False
                                    await voice_channel.set_permissions(member, overwrite=overwrite)
                                    await member.move_to(None)  # Pindahkan member keluar dari voice channel
                                    embed = discord.Embed(description=f"{member.display_name} telah di-ban dari voice channel ini!", color=discord.Color.green())
                                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                                else:
                                    embed = discord.Embed(description="Member tidak ditemukan!", color=discord.Color.red())
                                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)

                            select.callback = select_callback
                            view = discord.ui.View()
                            view.add_item(select)
                            embed = discord.Embed(description="Pilih member untuk di-ban:", color=discord.Color.blue())
                            await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=3)
                        else:
                            embed = discord.Embed(description="Tidak ada member yang bisa di-ban!", color=discord.Color.red())
                            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                    else:
                        embed = discord.Embed(description="Anda bukan pemilik voice channel ini!", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                else:
                    embed = discord.Embed(description="Data voice channel tidak ditemukan!", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
            elif interaction.data["custom_id"] == "button_7":
                if temp_channels_data:
                    if owner_id and interaction.user.id == owner_id:
                        # Ambil semua member yang telah di-ban dari voice channel ini
                        banned_members = [
                            discord.SelectOption(label=member.display_name, value=str(member.id))
                            for member, overwrite in voice_channel.overwrites.items()
                            if isinstance(member, discord.Member) and not overwrite.connect
                        ][:25]  # Batasi jumlah opsi menjadi 25

                        if banned_members:
                            select = discord.ui.Select(placeholder="Pilih member untuk di-unban", options=banned_members)

                            async def select_callback(interaction):
                                member_id = int(select.values[0])
                                unban_member = voice_channel.guild.get_member(member_id)
                                if unban_member:
                                    # Hapus permission overwrite untuk mengizinkan member kembali ke voice channel ini
                                    await voice_channel.set_permissions(unban_member, overwrite=None)
                                    embed = discord.Embed(description=f"{unban_member.display_name} telah di-unban dari voice channel ini!", color=discord.Color.green())
                                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                                else:
                                    embed = discord.Embed(description="Member tidak ditemukan!", color=discord.Color.red())
                                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)

                            select.callback = select_callback
                            view = discord.ui.View()
                            view.add_item(select)
                            embed = discord.Embed(description="Pilih member untuk di-unban:", color=discord.Color.blue())
                            await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=3)
                        else:
                            embed = discord.Embed(description="Tidak ada member yang bisa di-unban!", color=discord.Color.red())
                            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                    else:
                        embed = discord.Embed(description="Anda bukan pemilik voice channel ini!", color=discord.Color.red())
                        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)
                else:
                    embed = discord.Embed(description="Data voice channel tidak ditemukan!", color=discord.Color.red())
                    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=3)

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

                    for guild_data in self.voice_channels.find({}):
                        guild = self.bot.get_guild(guild_data["guild_id"])
                        if guild:
                            for channel_info in guild_data.get("temp_channels", []):
                                channel_id = channel_info if isinstance(channel_info, int) else channel_info["channel_id"]

                                channel = guild.get_channel(channel_id)
                                if channel and not channel.members:
                                    current_time = time.time()
                                    # Use loaded creation_time in your check
                                    if current_time - (creation_time or 0) > 1:  # 1 secs threshold
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

    async def handle_select_existing(self, interaction, message):
        initial_embed = discord.Embed(
            title="Select an Existing Channel",
            description="Please select the channel you want to use from the dropdown below.",
            color=discord.Color.green()
        )
        guild = interaction.guild
        existing_channels = guild.voice_channels
        if not existing_channels:
            await interaction.followup.send("No existing voice channels to select.")
            return

        # Create dropdown options for each existing channel
        options = [
            discord.SelectOption(label=channel.name, value=str(channel.id))
            for channel in existing_channels
        ]
        select = discord.ui.Select(placeholder="Choose a channel...", options=options)
        view = discord.ui.View()
        view.add_item(select)

        initial_message = await interaction.followup.send(embed=initial_embed, view=view)

        # Check function for interaction
        def check(interaction):
            return interaction.user == interaction.user and interaction.message.id == initial_message.id

        try:
            # Wait for the dropdown interaction
            interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
            
            # Check if the interaction has already been responded to
            if not interaction.response.is_done():
                await interaction.response.defer()

            selected_channel_id = int(interaction.data['values'][0])
            selected_channel = discord.utils.get(existing_channels, id=selected_channel_id)
            guild_id = interaction.guild.id
            voice_channel_id = selected_channel.id
            
            # Find text channel called 'vc-dashboard'
            text_channel = discord.utils.get(guild.text_channels, name='vc-dashboard')
            if text_channel is None:
                await interaction.followup.send("Text channel 'vc-dashboard' not found.")
                return

            text_channel_id = text_channel.id

            self.voice_channels.update_one(
                {"guild_id": guild_id},
                {"$set": {"voice_channel_id": voice_channel_id, "text_channel_id": text_channel_id}},
                upsert=True
            )
            await initial_message.delete()
            confirmation_message = await interaction.followup.send(f"You selected the channel <#{selected_channel.id}> and it has been stored in the database.")
            await asyncio.sleep(5)
            await confirmation_message.delete()
        except asyncio.TimeoutError:
            await initial_message.delete()
            confirmation_message = await interaction.followup.send("You took too long to select.")
            await asyncio.sleep(5)
            await confirmation_message.delete()

    async def handle_create_new(self, interaction, message):
            existing_channel = self.voice_channels.find_one({"guild_id": interaction.guild.id})
            if existing_channel:
                confirmation_message = await interaction.followup.send("A marked voice channel already exists in this server.")
                await asyncio.sleep(5)
                await confirmation_message.delete()
                return

            initial_embed = discord.Embed(
                title="Create New Marked Channels",
                description="Select a category to create a new voice and text channel.",
                color=discord.Color.blue()
            )
            server_categories = interaction.guild.categories
            if not server_categories:
                await interaction.followup.send("No categories available to create channels.")
                return

            # Create dropdown options for each category
            options = [
                discord.SelectOption(label=category.name, value=str(category.id))
                for category in server_categories
            ]
            select = discord.ui.Select(placeholder="Choose a category...", options=options)
            view = discord.ui.View()
            view.add_item(select)

            message = await interaction.followup.send(embed=initial_embed, view=view)

            # Check function for interaction
            def check(interaction):
                return interaction.user == interaction.user and interaction.message.id == message.id

            try:
                # Wait for the dropdown interaction
                interaction = await self.bot.wait_for("interaction", timeout=60.0, check=check)
                selected_category_id = int(interaction.data['values'][0])
                selected_category = discord.utils.get(server_categories, id=selected_category_id)
                new_voice_channel = await selected_category.create_voice_channel("⌛｜Create")
                new_text_channel = await selected_category.create_text_channel("vc-dashboard")

                guild_id = interaction.guild.id
                voice_channel_id = new_voice_channel.id
                text_channel_id = new_text_channel.id
                self.voice_channels.update_one(
                    {"guild_id": guild_id},
                    {"$set": {"voice_channel_id": voice_channel_id, "text_channel_id": text_channel_id}},
                        upsert=True
                    )
                await message.delete()
                confirmation_message = await interaction.followup.send(f"Created new voice channel <#{new_voice_channel.id}> and text channel <#{new_text_channel.id}> in the <#{selected_category.id}> category.")
                await asyncio.sleep(5)
            except asyncio.TimeoutError:
                await message.delete()
                confirmation_message = await interaction.followup.send("You took too long to select.")
                await asyncio.sleep(5)
                await confirmation_message.delete()

async def setup(bot):
    await bot.add_cog(VoiceChannels(bot))