import os
import discord
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class PresenceSwitcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.presence_task = None
        self.presence_states = [
            ("with ☢️ Nuclear", discord.ActivityType.streaming),
            ("", discord.ActivityType.watching)
        ]
        self.current_presence_index = 0

    async def set_presence(self):
        # Calculate the user and bot counts in the server
        guild = self.bot.get_guild(int(os.getenv("SERVER_ID")))  # Replace with your server's ID
        if guild:
            user_count = sum(1 for member in guild.members if not member.bot)
            bot_count = sum(1 for member in guild.members if member.bot)

            # Set the presence based on the current index
            state, activity_type = self.presence_states[self.current_presence_index]
            if self.current_presence_index == 1:
                state = f"{user_count} Users {bot_count} Bots"
            activity = discord.Activity(name=state, type=activity_type)
            await self.bot.change_presence(activity=activity)

            # Cycle to the next presence state
            self.current_presence_index = (self.current_presence_index + 1) % len(self.presence_states)

    async def presence_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            await self.set_presence()
            await asyncio.sleep(15)  # Change presence every 5 seconds

    def start_presence_loop(self):
        if self.presence_task is None:
            self.presence_task = self.bot.loop.create_task(self.presence_loop())

    def stop_presence_loop(self):
        if self.presence_task:
            self.presence_task.cancel()
            self.presence_task = None

    def cog_unload(self):
        self.stop_presence_loop()

async def setup(bot):
    cog = PresenceSwitcher(bot)
    cog.start_presence_loop()
    await bot.add_cog(cog)
