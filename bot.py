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

# Menggunakan @mention sebagai prefix
bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
bot.remove_command('help')

# MongoDB setup
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGO_URI"))
db = client[os.getenv("MONGO_DB")]
bot.db = db

async def create_or_update_message_with_buttons():
    channel_name = "vc-dashboard"  # Nama channel tempat pesan akan dibuat atau diperbarui
    actions = [
        {"label": "🔄Ambil Alih Channel", "custom_id": "button_1", "style": discord.ButtonStyle.blurple, "description": "Ambil alih kepemilikan voice channel."},
        {"label": "🔒Limit Channel", "custom_id": "button_2", "style": discord.ButtonStyle.primary, "description": "Atur batas jumlah pengguna di voice channel."},
        {"label": "🚫Ban Member", "custom_id": "button_3", "style": discord.ButtonStyle.danger, "description": "Ban member dari voice channel."},
        {"label": "✅Unban Member", "custom_id": "button_4", "style": discord.ButtonStyle.success, "description": "Unban member dari voice channel."},
    ]

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
        for action in actions:
            button = discord.ui.Button(label=action["label"], custom_id=action["custom_id"], style=action["style"])
            view.add_item(button)

        embed = discord.Embed(
            title="Voice Channel Management",
            description="Pilih tindakan yang ingin Anda lakukan dengan menggunakan tombol di bawah ini:",
            color=discord.Color.blue()
        )

        for action in actions:
            embed.add_field(name=action["label"], value=action["description"], inline=False)

        await channel.send(embed=embed, view=view)

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

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))