import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import random

# Load environment variables from .env file
load_dotenv()

# Define a list of random welcome and goodbye messages with descriptions
welcome_messages = [
    ("Welcome to the server, {member.mention}! 🎉", "We're thrilled to have you here."),
    ("Hey there, {member.mention}! Welcome aboard! 🌟", "Glad to see you join us."),
    ("We warmly welcome {member.mention} to our community! 🚀", "Let's have some fun together."),
    ("A big hello to {member.mention}! 🌈", "You've just stepped into an awesome community."),
    ("{member.mention}, welcome to the party! 🥳", "We've been waiting for you."),
    ("Great to see {member.mention} join us! 🌟", "Your journey with us begins now."),
    ("Welcome, {member.mention}! 🌻", "We hope you'll enjoy your time here."),
    ("{member.mention}, you've made the right choice by joining us! 🌠", "Let's make great memories together."),
    ("{member.mention}, welcome to the family! 🤗", "We're like one big family here."),
    ("A warm welcome to {member.mention}! 🌞", "Your presence brightens our server."),
    ("{member.mention}, it's a pleasure to have you with us! 🎈", "We're excited for what's to come."),
    ("Welcome, {member.mention}! 🌄", "Your journey with us starts now."),
    ("{member.mention}, you've just joined an amazing community! 🚀", "We're happy you're here."),
    ("{member.mention}, welcome to our little corner of the internet! 🌐", "Get ready for a great time."),
    ("A big welcome to {member.mention}! 🎊", "We've been waiting for someone like you."),
    ("{member.mention}, you've found your way to us! 🌟", "We're here to make your day."),
    ("Welcome, {member.mention}! 🌺", "Your adventure with us begins now."),
    ("{member.mention}, you're officially part of the crew! ⚓", "Let's set sail together."),
    ("A warm welcome to {member.mention}! 🌞", "We're excited to get to know you."),
    ("{member.mention}, welcome to the server! 🎮", "Prepare for epic adventures."),
]

goodbye_messages = [
    ("Farewell, {member.mention}! 😢", "You will be missed."),
    ("{member.mention} has left the server. Goodbye! 👋", "Wishing you all the best."),
    ("It's been great having {member.mention} around. Goodbye! 🌟", "Take care out there."),
    ("{member.mention}, we'll miss you! 😔", "Thank you for being a part of our community."),
    ("Saying goodbye to {member.mention} is never easy. Farewell! 🌈", "We hope to see you again."),
    ("Goodbye, {member.mention}! May your journey be filled with happiness. 🌻", "Take care of yourself."),
    ("{member.mention}, you've been an important part of our server. Goodbye and best wishes! 🚀", "Stay awesome!"),
    ("Farewell, {member.mention}! We hope to see you again someday. 🌟", "Your presence made a difference."),
    ("{member.mention}, as you leave, take a piece of our gratitude with you. Goodbye! 🌠", "You're always welcome back."),
    ("Goodbye, {member.mention}! Your time here was cherished. 🌄", "Wishing you success and happiness."),
    ("{member.mention}, it's not goodbye; it's see you later! 🎈", "Until we meet again."),
    ("Farewell, {member.mention}! We'll hold your memory close. 🌺", "Take care on your journey."),
    ("{member.mention}, as you embark on new adventures, know that you're always welcome here. Goodbye! 🌐", "Stay in touch!"),
    ("Goodbye, {member.mention}! We hope the future brings you joy and success. 🎊", "Your impact will be remembered."),
    ("{member.mention}, thank you for the memories. Farewell! 🌞", "Stay true to yourself."),
    ("Saying goodbye to {member.mention} is bittersweet. Take care! ⚓", "Wishing you smooth seas."),
    ("Farewell, {member.mention}! Your time here was a gift. 🌄", "You'll always have a place here."),
    ("{member.mention}, as you leave, remember that you're a part of our story. Goodbye! 🌟", "Your chapter was memorable."),
    ("Goodbye, {member.mention}! Your presence made our server better. 🌈", "Don't be a stranger!"),
    ("{member.mention}, your journey continues elsewhere, but you'll always have a home here. Farewell! 🌺", "Keep shining!"),
]

class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Get the welcome channel from .env
        welcome_channel_id = int(os.getenv("HELLO_CHANNEL_ID"))
        welcome_channel = member.guild.get_channel(welcome_channel_id)

        if welcome_channel:
            # Select a random welcome message with description
            welcome_message, welcome_description = random.choice(welcome_messages)

            # Create an embed for the welcome message
            embed = discord.Embed(
                title=welcome_message.format(member=member),
                description=welcome_description.format(member=member),
                color=discord.Color.green()
            )

            # Set the thumbnail to the member's profile picture, or a default avatar if not available
            avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
            embed.set_thumbnail(url=avatar_url)

            # Send the embed message in the specified channel
            await welcome_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        # Get the goodbye channel from .env
        goodbye_channel_id = int(os.getenv("HELLO_CHANNEL_ID"))
        goodbye_channel = member.guild.get_channel(goodbye_channel_id)

        if goodbye_channel:
            # Select a random goodbye message with description
            goodbye_message, goodbye_description = random.choice(goodbye_messages)

            # Create an embed for the goodbye message
            embed = discord.Embed(
                title=goodbye_message.format(member=member),
                description=goodbye_description.format(member=member),
                color=discord.Color.red()
            )

            # Set the thumbnail to the member's profile picture, or a default avatar if not available
            avatar_url = member.avatar.url if member.avatar else member.default_avatar.url
            embed.set_thumbnail(url=avatar_url)

            # Send the embed message in the specified channel
            await goodbye_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Greetings(bot))
