import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

# Load environment variables from .env file
load_dotenv()

# Define the bot prefix and enable all intents
intents = discord.Intents.all()

# Define your bot and command prefix
bot = commands.Bot(command_prefix=os.getenv("BOT_PREFIX"), intents=intents)

# Define the role ID and owner ID from .env
ROLE_ID = int(os.getenv("ROLE_ID"))
OWNER_ID = int(os.getenv("OWNER_ID"))

class ClearChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @bot.command(name="cc", hidden=True)
    async def cc(self, ctx):
        # Check if the user is the bot owner or has the specified role
        if ctx.author.id == OWNER_ID or discord.utils.get(ctx.author.roles, id=ROLE_ID):
            await ctx.send(f'{ctx.author.mention}, Wait a sec...')
            # Delete the command message
            await ctx.message.delete()
            # Get the channel where the command was invoked
            channel = ctx.channel

            try:
                # Delete all messages in the channel
                await channel.purge()
                await asyncio.sleep(1)
            except discord.HTTPException as e:
                if e.status == 429:
                    # Rate limited, wait for the recommended time
                    retry_after = e.retry_after
                    await asyncio.sleep(retry_after)
                else:
                    raise
        else:
            await ctx.message.delete()  # Delete the command message
            sent_message = await ctx.send(f'{ctx.author.mention}, You don\'t have permission to use this command.')
            # Wait for 5 seconds
            await asyncio.sleep(5)
            # Delete the sent message
            await sent_message.delete()

async def setup(bot):
    await bot.add_cog(ClearChannel(bot))