import os
import sys
import random
import discord 
import asyncio
import subprocess
from discord.ext import commands, tasks
from colorama import Fore, Style
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

# Define the bot prefix and enable all intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=os.getenv("BOT_PREFIX"), intents=intents)
bot.remove_command('help')  # Removing the default help command

# Check if the user is the bot owner
async def is_owner(ctx):
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

    print(Fore.GREEN + "Bot is ready." + Style.RESET_ALL)
    # Get the server
    server = bot.get_guild(int(os.getenv("SERVER_ID")))
    # Create a task to update bot's activity
    bot.loop.create_task(update_activity(server))
   

@bot.command(name="load", hidden=True)
@commands.is_owner()  # Ensure only the bot owner can use these commands
async def load_extension(ctx, extension):
    try:
        await bot.load_extension(f'cogs.{extension}')
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
@commands.is_owner()  # Ensure only the bot owner can use these commands
async def unload_extension(ctx, extension):
    try:
        await bot.unload_extension(f'cogs.{extension}')
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
@commands.is_owner()  # Ensure only the bot owner can use this command
async def reload_extension(ctx, extension):
    try:
        await bot.reload_extension(f'cogs.{extension}')
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
@commands.is_owner()  # Ensure only the bot owner can use this command
async def relaunch_bot(ctx):
    await ctx.message.delete()  # Delete the command message
    # Start a new instance of the bot script using a subprocess
    python = sys.executable
    subprocess.Popen([python, 'bot.py'])
    
    # Exit the current bot instance gracefully without raising an exception
    os._exit(0)

# Function to update bot's activity
async def update_activity(server):
    while not bot.is_closed():
        # Get the number of members and bots in the server
        member_count = len([member for member in server.members if not member.bot])
        bot_count = len([member for member in server.members if member.bot])

        # Set bot's activity to "{member_count} Members and {bot_count} Bots"
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{member_count} Users {bot_count} Bots"
        )
        await bot.change_presence(activity=activity)

        # Sleep for a few seconds (e.g., 5 seconds)
        await asyncio.sleep(5)

        # Set bot's activity to "Playing Made with 💖"
        activity = discord.Activity(
            type=discord.ActivityType.playing,
            name="Made with 💖"
        )
        await bot.change_presence(activity=activity)

        # Sleep for a few seconds (e.g., 5 seconds)
        await asyncio.sleep(5)

# Log in to the bot
bot.run(os.getenv("TOKEN"))