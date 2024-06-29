import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# Load environment variables from .env file
load_dotenv()

class ClearChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.bot.user.mentioned_in(message) and not message.author.bot:
            # Check if the message content is "clearchat"
            if "clearchat" in message.content.lower():
                # Check if the user is an administrator
                if message.author.guild_permissions.administrator:
                    await message.channel.send(f'{message.author.mention}, Wait a sec...')
                    # Delete the command message
                    await message.delete()
                    # Get the channel where the command was invoked
                    channel = message.channel

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
                    await message.delete()  # Delete the command message
                    sent_message = await message.channel.send(f'{message.author.mention}, You don\'t have permission to use this command.')
                    # Wait for 5 seconds
                    await asyncio.sleep(5)
                    # Delete the sent message
                    await sent_message.delete()

async def setup(bot):
    await bot.add_cog(ClearChannel(bot))