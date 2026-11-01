import discord
from discord import app_commands
from discord.ext import commands

from utils.i18n import t


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Le nom et la description sont en anglais (langue de base).
    # Leur traduction française est dans locales/fr.json, section "commands".
    @app_commands.command(name="ping", description="Check that the bot is responding")
    async def ping(self, interaction: discord.Interaction):
        latency = round(self.bot.latency * 1000)  # latency is in seconds, converted to ms
        await interaction.response.send_message(t("ping.reply", ms=latency), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Ping(bot))
