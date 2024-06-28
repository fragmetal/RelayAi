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

load_dotenv()

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix=None, intents=intents)
bot.remove_command('help')

# MongoDB setup
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
bot.db = db

def is_owner(ctx):
    return ctx.author.id == int(os.getenv('OWNER_ID'))

async def create_or_update_message_with_buttons():
    channel_name = "vc-dashboard"  # Nama channel tempat pesan akan dibuat atau diperbarui
    for guild in bot.guilds:
        channel = discord.utils.get(guild.text_channels, name=channel_name)
        if not channel:
            print(Fore.RED + f"Channel {channel_name} tidak ditemukan di {guild.name}." + Style.RESET_ALL)
            continue

        # Cari pesan yang sudah ada dengan tombol
        async for message in channel.history(limit=100):
            if message.author == bot.user and message.components:
                await message.delete()

        view = discord.ui.View()
        button1 = discord.ui.Button(label="Kunci Channel", custom_id="button_1", style=discord.ButtonStyle.red)
        button2 = discord.ui.Button(label="Buka Kunci Channel", custom_id="button_2", style=discord.ButtonStyle.green)
        button3 = discord.ui.Button(label="Ambil Alih Channel", custom_id="button_3", style=discord.ButtonStyle.blurple)
        button5 = discord.ui.Button(label="Mute Member", custom_id="button_5", style=discord.ButtonStyle.red)
        button6 = discord.ui.Button(label="Unmute Member", custom_id="button_6", style=discord.ButtonStyle.green)
        button7 = discord.ui.Button(label="Ban Member", custom_id="button_7", style=discord.ButtonStyle.red)
        button8 = discord.ui.Button(label="Unban Member", custom_id="button_8", style=discord.ButtonStyle.green)
        view.add_item(button1)
        view.add_item(button2)
        view.add_item(button3)
        view.add_item(button5)
        view.add_item(button6)
        view.add_item(button7)
        view.add_item(button8)

        await channel.send("Pilih tindakan yang ingin Anda lakukan:", view=view)

@bot.event
async def on_ready():
    await bot.tree.sync()
    await create_or_update_message_with_buttons()
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py"):
            cog_name = f"cogs.{filename[:-3]}"
            try:
                await bot.load_extension(cog_name)
                #print(Fore.BLUE + f"Module {cog_name} loaded." + Style.RESET_ALL)
            except Exception as e:
                print(Fore.RED + f"Failed to load {cog_name}: {e}" + Style.RESET_ALL)
    print(Fore.GREEN + f"Logged in as {bot.user.name}" + Style.RESET_ALL)
    print(Fore.GREEN + f"Discord.py API version: {discord.__version__}" + Style.RESET_ALL)
    print(Fore.GREEN + f"Python version: {platform.python_version()}" + Style.RESET_ALL)
    print(Fore.GREEN + f"Running on: {platform.system()} {platform.release()} ({os.name})" + Style.RESET_ALL)

@bot.event
async def on_message(message):
    # Abaikan semua pesan teks biasa
    return

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))