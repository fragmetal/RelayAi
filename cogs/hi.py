import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Get the welcome channel from .env
        welcome_channel_id = int(os.getenv("WELCOME_CHANNEL_ID"))
        welcome_channel = member.guild.get_channel(welcome_channel_id)

        if welcome_channel:
            # Create an embed for the welcome message
            embed = discord.Embed(
                title=f"Welcome to the server, {member.name}! 🎉",
                description="We're glad to have you here.",
                color=discord.Color.green()
            )
            
            # Set the thumbnail to the member's profile picture
            embed.set_thumbnail(url=member.avatar_url)
            
            # Send the embed message in the specified channel
            await welcome_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Get the goodbye channel from .env
        goodbye_channel_id = int(os.getenv("GOODBYE_CHANNEL_ID"))
        goodbye_channel = member.guild.get_channel(goodbye_channel_id)

        if goodbye_channel:
            # Create an embed for the goodbye message
            embed = discord.Embed(
                title=f"Goodbye, {member.name}! 😢",
                description="We'll miss you.",
                color=discord.Color.red()
            )
            
            # Set the thumbnail to the member's profile picture
            embed.set_thumbnail(url=member.avatar_url)
            
            # Send the embed message in the specified channel
            await goodbye_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Greetings(bot))
