import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import random

# Load environment variables from .env file
load_dotenv()

# Define a list of random welcome and goodbye messages with descriptions
welcome_messages = [
    ("Welcome to the server, {member.name}! 🎉", "We're thrilled to have you here."),
    ("Hey there, {member.name}! Welcome aboard! 🌟", "Glad to see you join us."),
    ("We warmly welcome {member.name} to our community! 🚀", "Let's have some fun together."),
    ("A big hello to {member.name}! 🌈", "You've just stepped into an awesome community."),
    ("{member.name}, welcome to the party! 🥳", "We've been waiting for you."),
    ("Great to see {member.name} join us! 🌟", "Your journey with us begins now."),
    ("Welcome, {member.name}! 🌻", "We hope you'll enjoy your time here."),
    ("{member.name}, you've made the right choice by joining us! 🌠", "Let's make great memories together."),
    ("{member.name}, welcome to the family! 🤗", "We're like one big family here."),
    ("A warm welcome to {member.name}! 🌞", "Your presence brightens our server."),
    ("{member.name}, it's a pleasure to have you with us! 🎈", "We're excited for what's to come."),
    ("Welcome, {member.name}! 🌄", "Your journey with us starts now."),
    ("{member.name}, you've just joined an amazing community! 🚀", "We're happy you're here."),
    ("{member.name}, welcome to our little corner of the internet! 🌐", "Get ready for a great time."),
    ("A big welcome to {member.name}! 🎊", "We've been waiting for someone like you."),
    ("{member.name}, you've found your way to us! 🌟", "We're here to make your day."),
    ("Welcome, {member.name}! 🌺", "Your adventure with us begins now."),
    ("{member.name}, you're officially part of the crew! ⚓", "Let's set sail together."),
    ("A warm welcome to {member.name}! 🌞", "We're excited to get to know you."),
    ("{member.name}, welcome to the server! 🎮", "Prepare for epic adventures."),
]

goodbye_messages = [
    ("Farewell, {member.name}! 😢", "You will be missed."),
    ("{member.name} has left the server. Goodbye! 👋", "Wishing you all the best."),
    ("It's been great having {member.name} around. Goodbye! 🌟", "Take care out there."),
    ("{member.name}, we'll miss you! 😔", "Thank you for being a part of our community."),
    ("Saying goodbye to {member.name} is never easy. Farewell! 🌈", "We hope to see you again."),
    ("Goodbye, {member.name}! May your journey be filled with happiness. 🌻", "Take care of yourself."),
    ("{member.name}, you've been an important part of our server. Goodbye and best wishes! 🚀", "Stay awesome!"),
    ("Farewell, {member.name}! We hope to see you again someday. 🌟", "Your presence made a difference."),
    ("{member.name}, as you leave, take a piece of our gratitude with you. Goodbye! 🌠", "You're always welcome back."),
    ("Goodbye, {member.name}! Your time here was cherished. 🌄", "Wishing you success and happiness."),
    ("{member.name}, it's not goodbye; it's see you later! 🎈", "Until we meet again."),
    ("Farewell, {member.name}! We'll hold your memory close. 🌺", "Take care on your journey."),
    ("{member.name}, as you embark on new adventures, know that you're always welcome here. Goodbye! 🌐", "Stay in touch!"),
    ("Goodbye, {member.name}! We hope the future brings you joy and success. 🎊", "Your impact will be remembered."),
    ("{member.name}, thank you for the memories. Farewell! 🌞", "Stay true to yourself."),
    ("Saying goodbye to {member.name} is bittersweet. Take care! ⚓", "Wishing you smooth seas."),
    ("Farewell, {member.name}! Your time here was a gift. 🌄", "You'll always have a place here."),
    ("{member.name}, as you leave, remember that you're a part of our story. Goodbye! 🌟", "Your chapter was memorable."),
    ("Goodbye, {member.name}! Your presence made our server better. 🌈", "Don't be a stranger!"),
    ("{member.name}, your journey continues elsewhere, but you'll always have a home here. Farewell! 🌺", "Keep shining!"),
]


class Greetings(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Get the welcome channel from .env
        welcome_channel_id = int(os.getenv("WELCOME_CHANNEL_ID"))
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
        goodbye_channel_id = int(os.getenv("GOODBYE_CHANNEL_ID"))
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
