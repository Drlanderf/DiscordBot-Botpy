import discord
import yaml
from discord import app_commands
from discord.ext import commands


class Reload(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reload", description="Recharge le fichier config.yaml")
    @app_commands.default_permissions(administrator=True)       # masquée pour les non-admins
    @app_commands.checks.has_permissions(administrator=True)    # et refusée à leur place
    @app_commands.guild_only()
    async def reload(self, interaction: discord.Interaction):
        try:
            self.bot.config.recharger()  # relit data/config.yaml
            self.bot.dispatch("config_reloaded")
        except yaml.YAMLError as erreur:
            # Le fichier est mal écrit (indentation, ":" oublié...) : on garde l'ancienne config
            await interaction.response.send_message(
                f"❌ Erreur dans config.yaml, rien n'a été rechargé :\n```{erreur}```",
                ephemeral=True,
            )
            return

        await interaction.response.send_message("✅ Config rechargée.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Reload(bot))