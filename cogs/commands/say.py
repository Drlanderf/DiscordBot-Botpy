import discord
from discord import app_commands
from discord.ext import commands

from components.modal.say import SayModal


class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="say", description="Send a message as the bot")
    @app_commands.default_permissions(administrator=True)      # hidden from non-admins
    @app_commands.checks.has_permissions(administrator=True)   # and really refused to them
    @app_commands.guild_only()
    async def say(self, interaction: discord.Interaction):
        # send_modal must be the FIRST response to the command: it opens the form.
        await interaction.response.send_modal(SayModal())


async def setup(bot):
    await bot.add_cog(Say(bot))
