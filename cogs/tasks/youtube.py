import json
import os
from datetime import datetime

import discord
from discord.ext import commands, tasks

from utils.youtube import YouTubeAPI, duree_en_secondes, reglage

MESSAGE_VIDEO = "{role}, **{nom}** vient de publier une nouvelle vidéo !"
MESSAGE_LIVE = "{role}, **{nom}** est en live sur YouTube !"
MEMOIRE_MAX = 50  # nombre de vidéos mémorisées par chaîne


class YouTube(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = None
        self.avatars = {}  # cache : channel_id -> url de l'avatar
        self.verifs = {}   # nom de la chaîne -> date du dernier passage réussi
        self.erreurs = {}  # nom de la chaîne -> dernière erreur (absente si tout va bien)

    async def cog_load(self):
        cle = os.getenv("YOUTUBE_API_KEY")
        if not cle:
            print("[YOUTUBE] YOUTUBE_API_KEY absente du .env : notifications désactivées")
            return
        self.api = YouTubeAPI(cle)
        await self.api.ouvrir()
        self.verifier.start()

    async def cog_unload(self):
        self.verifier.cancel()
        if self.api:
            await self.api.fermer()

    async def avatar(self, channel_id: str):
        if channel_id not in self.avatars:
            try:
                self.avatars[channel_id] = await self.api.avatar_chaine(channel_id)
            except Exception:
                return None  # sans avatar, l'annonce part quand même
        return self.avatars[channel_id]

    @staticmethod
    def est_un_short(video: dict, seuil: int) -> bool:
        """Un Short = une vidéo (pas un live) dont la durée est inférieure ou égale au seuil."""
        if seuil <= 0 or video["snippet"].get("liveBroadcastContent") != "none":
            return False
        duree = duree_en_secondes(video.get("contentDetails", {}).get("duration", ""))
        return 0 < duree <= seuil

    def construire_embed(self, video: dict, avatar, image: str | None = None) -> discord.Embed:
        snippet = video["snippet"]
        en_direct = snippet.get("liveBroadcastContent") == "live"

        # Pour un live, la vraie date est celle du démarrage, pas celle de la création de l'événement
        debut = (video.get("liveStreamingDetails") or {}).get("actualStartTime")
        date_texte = debut if (en_direct and debut) else snippet["publishedAt"]

        embed = discord.Embed(
            title=snippet["title"],
            url=f"https://www.youtube.com/watch?v={video['id']}",
            description="🔴 **En direct maintenant !**" if en_direct else None,
            color=discord.Color.from_str("#FF0000"),
            timestamp=datetime.fromisoformat(date_texte.replace("Z", "+00:00")),
        )
        embed.set_author(
            name=snippet["channelTitle"],
            url=f"https://www.youtube.com/channel/{snippet['channelId']}",
            icon_url=avatar,
        )

        if image:  # vignette verticale d'un Short
            embed.set_image(url=image)
        else:
            miniatures = snippet.get("thumbnails", {})
            for taille in ("maxres", "standard", "high", "medium", "default"):  # la meilleure disponible
                if taille in miniatures:
                    embed.set_image(url=miniatures[taille]["url"])
                    break

        # Discord ajoute " • date heure" après ce texte grâce au timestamp ci-dessus
        embed.set_footer(text="YouTube")
        return embed

    async def envoyer_annonce(self, salon, chaine: dict, video: dict, ping: bool = True):
        """Construit et envoie l'annonce. Utilisée par la vérification ET par /debug_youtube.
        Lève ValueError (message mal écrit) ou discord.HTTPException (envoi impossible)."""
        cfg = self.bot.config.get("youtube", default={}) or {}
        snippet = video["snippet"]
        en_direct = snippet.get("liveBroadcastContent") == "live"

        role = salon.guild.get_role(int(chaine.get("role_id") or 0)) if ping else None
        cle_message, defaut = ("message_live", MESSAGE_LIVE) if en_direct else ("message_video", MESSAGE_VIDEO)
        modele = chaine.get(cle_message) or cfg.get(cle_message) or defaut

        try:
            texte = modele.format(
                role=role.mention if role else "",
                nom=snippet["channelTitle"],
                titre=snippet["title"],
                lien=f"https://www.youtube.com/watch?v={video['id']}",
            )
        except (KeyError, IndexError, ValueError) as erreur:
            raise ValueError(
                f"'{cle_message}' invalide dans config.yaml "
                f"(variables autorisées : {{role}} {{nom}} {{titre}} {{lien}})"
            ) from erreur

        avatar = await self.avatar(snippet["channelId"])

        # Short : on essaie la vignette verticale 9:16 (sinon, la vignette normale est utilisée)
        image = None
        if self.est_un_short(video, reglage(chaine, cfg, "short_duree_max", 60)):
            image = await self.api.miniature_verticale(video["id"])

        await salon.send(
            texte.lstrip(", "),
            embed=self.construire_embed(video, avatar, image),
            allowed_mentions=discord.AllowedMentions(
                roles=[role] if role else False, everyone=False, users=False
            ),
        )

    async def verifier_chaine(self, cfg: dict, chaine: dict):
        channel_id = chaine.get("channel_id")
        salon_id = chaine.get("salon_id") or cfg.get("salon_id")
        if not channel_id or not salon_id:
            return

        cle = f"youtube_annonces_{channel_id}"
        brut = await self.bot.db.lire_etat(cle)
        recents = await self.api.derniers_uploads(channel_id)  # du plus récent au plus ancien

        if brut is None:
            # Première fois pour cette chaîne : on mémorise l'existant SANS rien annoncer,
            # sauf un live en cours ou programmé, qui sera traité quand il démarrera.
            videos = await self.api.videos(recents)
            deja_la = [v["id"] for v in videos if v["snippet"].get("liveBroadcastContent") == "none"]
            await self.bot.db.ecrire_etat(cle, json.dumps(deja_la))
            print(f"[YOUTUBE] {chaine.get('nom', channel_id)} : {len(deja_la)} vidéo(s) existante(s) ignorée(s)")
            return

        annonces = json.loads(brut)
        nouveaux = [i for i in recents if i not in annonces]
        if not nouveaux:
            return

        salon = self.bot.get_channel(int(salon_id))
        if salon is None:
            print(f"[YOUTUBE] salon {salon_id} introuvable")
            return

        par_id = {v["id"]: v for v in await self.api.videos(nouveaux)}
        ping_video = bool(reglage(chaine, cfg, "ping", True))
        ping_live = bool(reglage(chaine, cfg, "ping_live", False))
        annonces_live = bool(reglage(chaine, cfg, "annonces_live", True))

        for video_id in reversed(nouveaux):  # la plus ancienne d'abord, pour garder l'ordre
            video = par_id.get(video_id)
            if video is None:
                continue  # privée, supprimée ou pas encore disponible : on réessaiera

            statut = video["snippet"].get("liveBroadcastContent")
            if statut == "upcoming":
                continue  # live programmé : on attend qu'il démarre
            if statut == "none" and "liveStreamingDetails" in video:
                annonces.append(video_id)  # rediffusion d'un live déjà terminé : pas d'annonce
                continue
            if statut == "live" and not annonces_live:
                annonces.append(video_id)  # annonces de live désactivées : on le mémorise sans l'annoncer
                continue

            try:
                await self.envoyer_annonce(
                    salon, chaine, video, ping=ping_live if statut == "live" else ping_video
                )
            except (ValueError, discord.HTTPException) as erreur:
                print(f"[YOUTUBE] annonce impossible : {erreur}")
                break  # on réessaiera au prochain passage
            annonces.append(video_id)

        await self.bot.db.ecrire_etat(cle, json.dumps(annonces[-MEMOIRE_MAX:]))

    @tasks.loop(minutes=3)
    async def verifier(self):
        cfg = self.bot.config.get("youtube", default={}) or {}
        for chaine in cfg.get("chaines", []) or []:
            nom = chaine.get("nom", "?")
            try:
                await self.verifier_chaine(cfg, chaine)
            except Exception as erreur:  # une chaîne en erreur ne bloque pas l'autre
                self.erreurs[nom] = str(erreur)
                print(f"[YOUTUBE] {nom} : {erreur}")
            else:
                self.verifs[nom] = discord.utils.utcnow()
                self.erreurs.pop(nom, None)

    @verifier.before_loop
    async def avant_demarrage(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(YouTube(bot))