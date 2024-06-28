import os
import asyncio
import discord
from discord.ext import commands
import pymongo
from dotenv import load_dotenv

load_dotenv()

class ReactionRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mongo_client = pymongo.MongoClient(os.getenv('MONGO_URI'))
        self.db = self.mongo_client[os.getenv('MONGO_DB')]
        self.reaction_roles = self.db["reaction_roles"]

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        guild_id = payload.guild_id
        user = self.bot.get_user(payload.user_id)
        reaction = payload.emoji.name
        guild = self.bot.get_guild(guild_id)
        member = guild.get_member(payload.user_id)
        # print(f"{member.name} reacted {reaction}.")

        # Check if the bot has the necessary permissions
        bot_member = guild.me
        if not bot_member.guild_permissions.manage_roles:
            print("Bot does not have permission to manage roles.")
            return

        # Look up the role in the database based on the message ID and emoji
        role_data = next((role for role in self.reaction_roles.find({
            "guild_id": guild_id,
            "reactions.message_id": payload.message_id,
            "reactions.emoji": reaction
        })), None)
        if role_data:
            reactions = role_data["reactions"]
            for reaction_entry in reactions:
                if reaction_entry["emoji"] == reaction:  # Check if the emoji matches
                    role_id = reaction_entry["role_id"]
                    role = discord.utils.get(guild.roles, id=role_id)
                    if role:
                        try:
                            await member.add_roles(role)
                        except Exception as e:
                            print(f"Error assigning role: {e}")
                    else:
                        print(f"Role with ID {role_id} not found.")
                    break  # Exit the loop after finding the matching emoji

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        guild_id = payload.guild_id
        user = self.bot.get_user(payload.user_id)
        reaction = payload.emoji.name
        guild = self.bot.get_guild(guild_id)
        member = guild.get_member(payload.user_id)
        # print(f"{member.name} unreacted {reaction}.")

        # Check if the bot has the necessary permissions
        bot_member = guild.me
        if not bot_member.guild_permissions.manage_roles:
            print("Bot does not have permission to manage roles.")
            return

        # Look up the role in the database based on the message ID and emoji
        role_data = next((role for role in self.reaction_roles.find({
            "guild_id": guild_id,
            "reactions.message_id": payload.message_id,
            "reactions.emoji": reaction
        })), None)
        if role_data:
            reactions = role_data["reactions"]
            for reaction_entry in reactions:
                if reaction_entry["emoji"] == reaction:  # Check if the emoji matches
                    role_id = reaction_entry["role_id"]
                    role = discord.utils.get(guild.roles, id=role_id)
                    if role:
                        try:
                            await member.remove_roles(role)
                        except Exception as e:
                            print(f"Error removing role: {e}")
                    else:
                        print(f"Role with ID {role_id} not found.")
                    break  # Exit the loop after finding the matching emoji

    @commands.hybrid_command()
    async def addrole(self, ctx, message_id: int, emoji: str, role: discord.Role):
        try:
            target_message = await ctx.fetch_message(message_id)
            await target_message.add_reaction(emoji)
            
            # Get the guild ID
            guild_id = ctx.guild.id
            
            # Save the reaction role data in the database
            self.reaction_roles.update_one(
                {"guild_id": guild_id},
                {"$push": {
                    "reactions": {
                        "message_id": message_id,
                        "emoji": emoji,
                        "role_id": role.id
                    }
                }},
                upsert=True  # Create a new document if it doesn't exist
            )

            await ctx.message.delete()
            sent_message = await ctx.send(f"Reaction role added for {emoji} with role {role.mention}!")
            await asyncio.sleep(5)
            await sent_message.delete()
            
        except discord.NotFound:
            sent_message = await ctx.send("Target message not found. Make sure the message ID is correct.")
            await ctx.message.delete()
            await asyncio.sleep(5)
            await sent_message.delete()

    @commands.hybrid_command()
    async def removerole(self, ctx, message_id: int, emoji: str):
        try:
            target_message = await ctx.fetch_message(message_id)
            await target_message.remove_reaction(emoji, self.bot.user)
            
            # Get the guild ID
            guild_id = ctx.guild.id
            
            # Remove the reaction role data from the database
            self.reaction_roles.update_one(
                {"guild_id": guild_id},
                {"$pull": {
                    "reactions": {
                        "message_id": message_id,
                        "emoji": emoji
                    }
                }}
            )

            await ctx.message.delete()
            sent_message = await ctx.send(f"Reaction role removed for {emoji}!")
            await asyncio.sleep(5)
            await sent_message.delete()

        except discord.NotFound:
            sent_message = await ctx.send("Target message not found. Make sure the message ID is correct.")
            await ctx.message.delete()
            await asyncio.sleep(5)
            await sent_message.delete()

async def setup(bot):
    await bot.add_cog(ReactionRolesCog(bot))
