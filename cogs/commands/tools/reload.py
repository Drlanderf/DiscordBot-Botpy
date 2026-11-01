import discord
import yaml
from discord import app_commands
from discord.ext import commands

from utils.i18n import i18n, t


class Reload(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reload", description="Reload the config.yaml file")
    @app_commands.default_permissions(administrator=True)      # hidden from non-admins
    @app_commands.checks.has_permissions(administrator=True)   # and really refused to them
    @app_commands.guild_only()
    async def reload(self, interaction: discord.Interaction):
        try:
            self.bot.config.recharger()                # re-reads data/config.yaml (and applies `language`)
            self.bot.dispatch("config_reloaded")       # tells every cog that listens to refresh itself
        except yaml.YAMLError as error:
            # The file is badly written (indentation, missing ":"...): the old config is kept
            await interaction.response.send_message(t("reload.yaml_error", error=error), ephemeral=True)
            return

        await interaction.response.send_message(t("reload.done", language=i18n.language), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Reload(bot))
