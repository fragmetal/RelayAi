import discord
import sys
import traceback
import logging
import asyncio
from discord.ext import commands

class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.add_listener(self.on_command_error, "on_command_error")

    async def on_command_error(self, ctx, error):
        if hasattr(ctx.command, "on_error"):
            return  # Don't interfere with custom error handlers

        error = getattr(error, "original", error)  # get original error

        if isinstance(error, commands.CommandNotFound):
            await ctx.message.delete()  # Delete the command message
            sent_message = await ctx.send(f"That command does not exist. Please use `{self.bot.command_prefix}help` for a list of commands.")
            # Wait for 5 seconds
            await asyncio.sleep(3)
            # Delete the sent message
            return await sent_message.delete()

        if isinstance(error, commands.CommandError):
            # Check if ctx.command is not None before accessing its name
            command_name = ctx.command.name if ctx.command else "unknown"
            return await ctx.send(
                f"Error executing command `{command_name}`: {str(error)}")

        await ctx.send(
            "An unexpected error occurred while running that command.")
        logging.warn("Ignoring exception in command {}:".format(ctx.command))
        logging.warn("\n" + "".join(
            traceback.format_exception(
                type(error), error, error.__traceback__)))

async def setup(bot):
    await bot.add_cog(CommandErrorHandler(bot))