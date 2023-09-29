import discord
import asyncio
from discord.ext import commands

class tmp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # Check if the member joined the voice channel named 📞｜Create
        target_channel_name = "📞｜Create"
        # Define the temp_channel_prefix here
        temp_channel_prefix = "📞｜Room "
        if before.channel is None and after.channel and after.channel.name == target_channel_name:
            # Member joined the target channel
            # Create a temporary voice channel within a specific category
            guild = member.guild
            category_name = "Ｖｏｉｃｅ ｃｈａｔｓ"  # Replace with your category name
            i = 1
            while True:
                temp_channel_name = f"{temp_channel_prefix}{i}"
                if temp_channel_name not in [c.name for c in guild.voice_channels]:
                    break
                i += 1
            # Get the category by name
            category = discord.utils.get(guild.categories, name=category_name)
            # Create the temporary voice channel within the category
            temp_channel = await guild.create_voice_channel(temp_channel_name, category=category)
            # Move the member to the temporary channel
            await member.move_to(temp_channel)
        elif before.channel and before.channel.name.startswith(temp_channel_prefix) and len(before.channel.members) == 0:
            # Temporary channel became empty, delete it
            await before.channel.delete()

async def setup(bot):
    await bot.add_cog(tmp(bot))