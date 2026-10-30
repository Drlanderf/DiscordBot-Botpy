import os
import platform

import discord
from discord import app_commands
from discord.ext import commands


def depuis(date) -> str:
    """Date relative gérée par Discord ("il y a 3 minutes"), ou 'pas encore'."""
    return discord.utils.format_dt(date, "R") if date else "pas encore"


class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.demarrage = discord.utils.utcnow()

    def etat_twitch(self) -> str:
        cog = self.bot.get_cog("Twitch")
        if cog is None:
            return "⚪ Module non chargé"
        if cog.api is None:
            return "⚪ Désactivé (identifiants absents du .env)"
        if cog.derniere_erreur:
            return f"❌ {cog.derniere_erreur[:150]}\nDernier succès : {depuis(cog.derniere_verif)}"
        return f"✅ Dernière vérification : {depuis(cog.derniere_verif)}"

    def etat_youtube(self) -> str:
        cog = self.bot.get_cog("YouTube")
        if cog is None:
            return "⚪ Module non chargé"
        if cog.api is None:
            return "⚪ Désactivé (clé absente du .env)"

        cfg = self.bot.config.get("youtube", default={}) or {}
        lignes = []
        for chaine in cfg.get("chaines", []) or []:
            nom = chaine.get("nom", "?")
            if cog.erreurs.get(nom):
                lignes.append(f"❌ **{nom}** : {cog.erreurs[nom][:100]}")
            else:
                lignes.append(f"✅ **{nom}** : {depuis(cog.verifs.get(nom))}")
        return "\n".join(lignes)[:1024] or "⚪ Aucune chaîne configurée"

    @app_commands.command(name="status", description="État du bot (version, latence, notifications)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def status(self, interaction: discord.Interaction):
        version = os.getenv("BOT_VERSION", "dev")
        commit = os.getenv("BOT_COMMIT", "")[:7]  # les 7 premiers caractères suffisent

        embed = discord.Embed(
            title="📊 État du bot",
            color=discord.Color.blurple(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(
            name="Version",
            value=f"`{version}`" + (f" (commit `{commit}`)" if commit else ""),
            inline=False,
        )
        embed.add_field(name="En ligne depuis", value=depuis(self.demarrage), inline=True)
        embed.add_field(name="Latence", value=f"{round(self.bot.latency * 1000)} ms", inline=True)
        embed.add_field(name="Modules", value=f"{len(self.bot.cogs)} chargés", inline=True)
        embed.add_field(name="Twitch", value=self.etat_twitch(), inline=False)
        embed.add_field(name="YouTube", value=self.etat_youtube(), inline=False)
        embed.set_footer(text=f"Python {platform.python_version()} • discord.py {discord.__version__}")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Status(bot))