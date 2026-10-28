import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import construire_embed


class Reseaux(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="reseaux", description="Envoie l'embed des réseaux sociaux")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def reseaux(self, interaction: discord.Interaction):
        section = self.bot.config.get("reseaux")
        if not section:
            await interaction.response.send_message(
                "❌ La section `reseaux` est absente de config.yaml.", ephemeral=True
            )
            return

        try:
            await interaction.channel.send(embed=construire_embed(section))
        except discord.HTTPException as erreur:  # permission manquante, embed trop grand...
            await interaction.response.send_message(f"❌ Envoi impossible : {erreur}", ephemeral=True)
            return

        await interaction.response.send_message("✅ Embed envoyé.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Reseaux(bot))