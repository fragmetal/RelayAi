import discord
import asyncio
import os
from dotenv import load_dotenv
from discord.ext import commands

# Load environment variables from .env file
load_dotenv()

class TemporaryVoiceChannels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temporary_channels = {}  # A dictionary to track temporary channels

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Read environment variables
        target_channel_id = int(os.getenv("TARGET_CHANNEL_ID"))
        category_id = int(os.getenv("CATEGORY_ID"))

        # Fetch the target channel and category by ID
        guild = member.guild
        target_channel = discord.utils.get(guild.voice_channels, id=target_channel_id)
        category = discord.utils.get(guild.categories, id=category_id)

        if after.channel == target_channel:
            # Member joined the target channel
            # Create a temporary channel with a unique name
            channel_name = f"⌛｜{member.name}"
            clone_channel = await category.create_voice_channel(name=channel_name, user_limit=5)

            if clone_channel:
                # Store the temporary channel information in the dictionary
                self.temporary_channels[clone_channel.id] = member.id
                # Move the member to the new channel
                await member.move_to(clone_channel)
                # Set permissions for the member
                overwrites = {
                    member: discord.PermissionOverwrite(manage_channels=True)
                }
                await clone_channel.edit(overwrites=overwrites)
                await clone_channel.send(f"Welcome {member.mention} to your private channel. You can change the channel settings yourself.")
            else:
                await member.send("Failed to create your temporary voice channel. Please try again later.")

        elif before.channel and before.channel.id in self.temporary_channels:
            # Member left a temporary channel
            user_id = self.temporary_channels[before.channel.id]
            if user_id == member.id:
                # This was the member who created the channel
                await before.channel.delete()
                del self.temporary_channels[before.channel.id]
                    
async def setup(bot):
    await bot.add_cog(TemporaryVoiceChannels(bot))