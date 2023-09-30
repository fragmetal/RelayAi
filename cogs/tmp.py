import discord
import asyncio
import os
from dotenv import load_dotenv
from discord.ext import commands

# Load environment variables from .env file
load_dotenv()

class tmp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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
            # Create the cloned channel faster and with the user's name
            channel_name = f"📞｜{member.name}"
            clone_channel = await category.create_voice_channel(name=channel_name, user_limit=5)

            if clone_channel:
                # Check if the member is connected to a voice channel
                if member.voice and member.voice.channel:
                    await member.move_to(clone_channel)
                    await clone_channel.send(f"Welcome {member.mention} to your private channel. You can change the channel settings yourself.")

                    # Check if the channel still exists before setting permissions
                    if clone_channel.guild.get_channel(clone_channel.id):
                        await clone_channel.set_permissions(member, manage_channels=True)
                    else:
                        # The channel doesn't exist, handle it gracefully
                        await member.send("Your temporary voice channel no longer exists.")

                else:
                    # If the member is not connected to a voice channel, delete the cloned channel
                    await clone_channel.delete()
                    await member.send("You must be connected to a voice channel to use this feature.")

                # Check if the newly created channel is empty and delete it if it is
                if clone_channel.guild.get_channel(clone_channel.id) and not clone_channel.members:
                    await clone_channel.delete()
            else:
                # Handle the case where the channel creation failed (clone_channel is None)
                await member.send("Failed to create your temporary voice channel. Please try again later.")
                    
        elif before.channel and before.channel != target_channel and len(before.channel.members) == 0:
            # Temporary channel became empty, delete it
            await before.channel.delete()

        elif before.channel and before.channel != target_channel and len(before.channel.members) == 1:
            # Owner left the temporary channel, transfer ownership to another user
            owner = before.channel.members[0]

            await before.channel.set_permissions(owner, manage_channels=False)  # Remove manage permissions from the old owner
            
            # Mention the new owner in the channel
            new_owner = before.channel.members[0]
            await before.channel.send(f"{new_owner.mention} is now the owner of this channel.")
            await before.channel.set_permissions(new_owner, manage_channels=True)  # Give manage permissions to the new owner

async def setup(bot):
    await bot.add_cog(tmp(bot))