import discord
from discord import app_commands
from discord.ext import commands


class DebugTwitch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="debug_twitch", description="Simule une annonce de live Twitch (test)")
    @app_commands.describe(
        ping="Mentionner le rôle (désactivé par défaut)",
        salon_annonce="Envoyer dans le salon d'annonces de la config plutôt que dans ce salon",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def debug_twitch(
        self,
        interaction: discord.Interaction,
        ping: bool = False,
        salon_annonce: bool = False,
    ):
        cog = self.bot.get_cog("Twitch")
        if cog is None or cog.api is None:
            await interaction.response.send_message(
                "❌ Le module Twitch n'est pas actif (identifiants absents du .env ?).", ephemeral=True
            )
            return

        cfg = self.bot.config.get("twitch", default={}) or {}
        chaine = cfg.get("chaine")
        if not chaine:
            await interaction.response.send_message("❌ `twitch.chaine` manque dans config.yaml.", ephemeral=True)
            return

        salon = interaction.channel
        if salon_annonce:
            salon = self.bot.get_channel(int(cfg.get("salon_id") or 0))
            if salon is None:
                await interaction.response.send_message("❌ `twitch.salon_id` est introuvable.", ephemeral=True)
                return

        await interaction.response.defer(ephemeral=True)  # la requête Twitch peut prendre un instant

        try:
            profil = await cog.api.utilisateur(chaine)  # le vrai avatar, même hors ligne
        except Exception:
            profil = None

        # Faux live : mêmes champs que ceux renvoyés par Twitch
        stream = {
            "id": "debug",
            "user_login": chaine.lower(),
            "user_name": profil["display_name"] if profil else chaine,
            "title": "🧪 Ceci est un test de notification",
            "game_name": "Warframe",
            "viewer_count": 123,
            "thumbnail_url": f"https://static-cdn.jtvnw.net/previews-ttv/live_user_{chaine.lower()}-{{width}}x{{height}}.jpg",
        }

        try:
            await cog.envoyer_annonce(salon, stream, profil, ping=ping)
        except (ValueError, discord.HTTPException) as erreur:
            await interaction.followup.send(f"❌ {erreur}", ephemeral=True)
            return

        await interaction.followup.send(f"✅ Annonce de test envoyée dans {salon.mention}.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(DebugTwitch(bot))