import os
import sys
import random
import discord 
import asyncio
import subprocess
import platform
from discord.ext import commands
from colorama import Fore, Style
from dotenv import load_dotenv
import motor.motor_asyncio
from keep_alive import keep_alive
keep_alive()
# Load environment variables from .env file
load_dotenv()

# Define the bot prefix and enable all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=os.getenv("BOT_PREFIX"), intents=intents)
bot.remove_command('help')  # Removing the default help command

# MongoDB setup
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]  # Change this to your preferred database name
bot.db = db  # Store the database connection in the bot instance


# Check if the user is the bot owner
def is_owner(ctx):
    return ctx.author.id == int(os.getenv('OWNER_ID'))

# Define the on_ready event handler
@bot.event
async def on_ready():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            cog_name = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(cog_name)
                print(Fore.GREEN + f"Module {cog_name} loaded." + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + f"Failed to load {cog_name}: {e}" + Style.RESET_ALL)

            except Exception as e:
                # Handle any exceptions that occur during setup
                print(f"Error during setup: {str(e)}")

    print(Fore.GREEN + f"Logged in as {bot.user.name}" + Style.RESET_ALL)
    print(Fore.GREEN + f"Discord.py API version: {discord.__version__}" + Style.RESET_ALL)
    print(Fore.GREEN + f"Python version: {platform.python_version()}" + Style.RESET_ALL)
    print(Fore.GREEN + f"Running on: {platform.system()} {platform.release()} ({os.name})" + Style.RESET_ALL)
    
@bot.command(name="load", hidden=True)
@commands.check(is_owner)  # Ensure only the bot owner can use these commands
async def load_extension(ctx, extension):
    try:
        bot.load_extension(f'cogs.{extension}')
        await ctx.message.delete()  # Delete the command message
        sent_message = await ctx.send(f'{ctx.author.mention}, loaded extension: {extension}')
        # Wait for 5 seconds
        await asyncio.sleep(5)
        # Delete the sent message
        await sent_message.delete()
    except Exception as e:
        await ctx.message.delete()  # Delete the command message
        sent_message = await ctx.send(f'{ctx.author.mention}, failed to load extension {extension}: {e}')
        # Wait for 5 seconds
        await asyncio.sleep(5)
        # Delete the sent message
        await sent_message.delete()

@bot.command(name="unload", hidden=True)
@commands.check(is_owner)  # Ensure only the bot owner can use these commands
async def unload_extension(ctx, extension):
    try:
        bot.unload_extension(f'cogs.{extension}')
        await ctx.message.delete()  # Delete the command message
        sent_message = await ctx.send(f'{ctx.author.mention}, unloaded extension: {extension}')
        # Wait for 5 seconds
        await asyncio.sleep(3)
        # Delete the sent message
        await sent_message.delete()
    except Exception as e:
        await ctx.message.delete()  # Delete the command message
        sent_message = await ctx.send(f'{ctx.author.mention}, failed to unload extension {extension}: {e}')
        # Wait for 5 seconds
        await asyncio.sleep(3)
        # Delete the sent message
        await sent_message.delete()

@bot.command(name="reload", hidden=True)
@commands.check(is_owner)  # Ensure only the bot owner can use this command
async def reload_extension(ctx, extension):
    try:
        bot.reload_extension(f'cogs.{extension}')
        await ctx.message.delete()  # Delete the command message
        sent_message = await ctx.send(f'{ctx.author.mention}, reloaded extension: {extension}')
        # Wait for 5 seconds
        await asyncio.sleep(3)
        # Delete the sent message
        await sent_message.delete()
    except Exception as e:
        await ctx.message.delete()  # Delete the command message
        sent_message = await ctx.send(f'{ctx.author.mention}, failed to reload extension {extension}: {e}')
        # Wait for 5 seconds
        await asyncio.sleep(3)
        # Delete the sent message
        await sent_message.delete()

@bot.command(name="restart", hidden=True)
@commands.check(is_owner)  # Ensure only the bot owner can use this command
async def relaunch_bot(ctx):
    await ctx.message.delete()  # Delete the command message
    # Start a new instance of the bot script using a subprocess
    python = sys.executable
    subprocess.Popen([python, 'bot.py'])
    
    # Exit the current bot instance gracefully without raising an exception
    os._exit(0)

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
