from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from utils.youtube import reglage


class DebugYouTube(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="debug_youtube", description="Simule une annonce YouTube (test)")
    @app_commands.describe(
        chaine="La chaîne à tester",
        genre="Annonce de vidéo, de Short ou de live",
        ping="Mentionner le rôle (désactivé par défaut)",
        salon_annonce="Envoyer dans le salon d'annonces de la config plutôt que dans ce salon",
    )
    @app_commands.choices(
        genre=[
            app_commands.Choice(name="Vidéo", value="video"),
            app_commands.Choice(name="Short", value="short"),
            app_commands.Choice(name="Live", value="live"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def debug_youtube(
        self,
        interaction: discord.Interaction,
        chaine: str,
        genre: app_commands.Choice[str],
        ping: bool = False,
        salon_annonce: bool = False,
    ):
        cog = self.bot.get_cog("YouTube")
        if cog is None or cog.api is None:
            await interaction.response.send_message(
                "❌ Le module YouTube n'est pas actif (clé absente du .env ?).", ephemeral=True
            )
            return

        cfg = self.bot.config.get("youtube", default={}) or {}
        chaine_cfg = next((c for c in cfg.get("chaines", []) or [] if c.get("nom") == chaine), None)
        if chaine_cfg is None or not chaine_cfg.get("channel_id"):
            await interaction.response.send_message(
                f"❌ Chaîne `{chaine}` introuvable (ou sans `channel_id`) dans config.yaml.", ephemeral=True
            )
            return

        salon = interaction.channel
        if salon_annonce:
            salon = self.bot.get_channel(int(chaine_cfg.get("salon_id") or cfg.get("salon_id") or 0))
            if salon is None:
                await interaction.response.send_message("❌ Salon d'annonces introuvable.", ephemeral=True)
                return

        await interaction.response.defer(ephemeral=True)  # les requêtes YouTube peuvent prendre un instant

        try:
            ids = await cog.api.derniers_uploads(chaine_cfg["channel_id"], 10)
            par_id = {v["id"]: v for v in await cog.api.videos(ids)}
        except Exception as erreur:
            await interaction.followup.send(f"❌ {erreur}", ephemeral=True)
            return
        videos = [par_id[i] for i in ids if i in par_id]  # du plus récent au plus ancien

        seuil = reglage(chaine_cfg, cfg, "short_duree_max", 60)
        shorts = [v for v in videos if cog.est_un_short(v, seuil)]
        normales = [v for v in videos if not cog.est_un_short(v, seuil)]

        if genre.value == "short":
            candidats = shorts
        else:
            candidats = normales or videos
        if not candidats:
            message = (
                f"❌ Aucun Short (durée ≤ {seuil} s) parmi les 10 dernières vidéos."
                if genre.value == "short"
                else "❌ Aucune vidéo trouvée sur cette chaîne."
            )
            await interaction.followup.send(message, ephemeral=True)
            return

        # On transforme une vraie vidéo en annonce de test
        video = candidats[0]
        video["snippet"]["liveBroadcastContent"] = "live" if genre.value == "live" else "none"
        video["snippet"]["publishedAt"] = datetime.now(timezone.utc).isoformat()
        video.pop("liveStreamingDetails", None)

        try:
            await cog.envoyer_annonce(salon, chaine_cfg, video, ping=ping)
        except (ValueError, discord.HTTPException) as erreur:
            await interaction.followup.send(f"❌ {erreur}", ephemeral=True)
            return

        await interaction.followup.send(f"✅ Annonce de test envoyée dans {salon.mention}.", ephemeral=True)

    @debug_youtube.autocomplete("chaine")
    async def chaine_autocomplete(self, interaction: discord.Interaction, saisie: str):
        cfg = self.bot.config.get("youtube", default={}) or {}
        noms = [c["nom"] for c in cfg.get("chaines", []) or [] if c.get("nom")]
        return [app_commands.Choice(name=n, value=n) for n in noms if saisie.lower() in n.lower()][:25]


async def setup(bot):
    await bot.add_cog(DebugYouTube(bot))