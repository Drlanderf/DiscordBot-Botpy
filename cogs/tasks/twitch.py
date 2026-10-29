import os
import time
from datetime import datetime

import discord
from discord.ext import commands, tasks

from utils.twitch import TwitchAPI

MESSAGE_PAR_DEFAUT = "{role}, **{nom}** est en live sur : **{jeu}** !"


class Twitch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = None

    async def cog_load(self):
        client_id = os.getenv("TWITCH_CLIENT_ID")
        client_secret = os.getenv("TWITCH_CLIENT_SECRET")
        if not client_id or not client_secret:
            print("[TWITCH] TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET absents du .env : notifications désactivées")
            return
        self.api = TwitchAPI(client_id, client_secret)
        await self.api.ouvrir()
        self.verifier.start()

    async def cog_unload(self):
        self.verifier.cancel()
        if self.api:
            await self.api.fermer()

    def construire_embed(self, stream: dict, profil: dict | None) -> discord.Embed:
        lien = f"https://www.twitch.tv/{stream['user_login']}"
        avatar = profil["profile_image_url"] if profil else None

        # Date de début du live (fournie par Twitch). Sans elle (commande de test), on prend l'heure actuelle.
        debut = stream.get("started_at")
        date = datetime.fromisoformat(debut.replace("Z", "+00:00")) if debut else discord.utils.utcnow()

        embed = discord.Embed(
            title=stream["title"] or "En direct !",
            url=lien,
            color=discord.Color.from_str("#9146FF"),  # violet Twitch
            timestamp=date,
        )
        embed.set_author(name=stream["user_name"], url=lien, icon_url=avatar)
        if avatar:
            embed.set_thumbnail(url=avatar)
        embed.add_field(name="Jeu", value=stream["game_name"] or "Non renseigné", inline=True)
        embed.add_field(name="Viewers", value=str(stream["viewer_count"]), inline=True)

        # Aperçu du stream. Le "?t=" force Discord à ne pas réutiliser une ancienne image en cache.
        apercu = stream["thumbnail_url"].replace("{width}", "620").replace("{height}", "378")
        embed.set_image(url=f"{apercu}?t={int(time.time())}")

        # Discord ajoute " • date heure" après ce texte grâce au timestamp ci-dessus
        embed.set_footer(text="Twitch")
        return embed

    async def envoyer_annonce(self, salon, stream: dict, profil: dict | None, ping: bool = True):
        """Construit et envoie l'annonce. Utilisée par le live réel ET par /debug_twitch.
        Lève ValueError (message mal écrit) ou discord.HTTPException (envoi impossible)."""
        cfg = self.bot.config.get("twitch", default={}) or {}
        role = salon.guild.get_role(int(cfg.get("role_id") or 0)) if ping else None
        modele = cfg.get("message") or MESSAGE_PAR_DEFAUT

        try:
            texte = modele.format(
                role=role.mention if role else "",
                nom=stream["user_name"],
                jeu=stream["game_name"] or "un jeu inconnu",
                lien=f"https://www.twitch.tv/{stream['user_login']}",  # nouvelle variable
            )
        except (KeyError, IndexError, ValueError) as erreur:
            raise ValueError(
                "'message' invalide dans config.yaml "
                "(variables autorisées : {role} {nom} {jeu} {lien})"
            ) from erreur

        await salon.send(
            texte.lstrip(", "),
            embed=self.construire_embed(stream, profil),
            # Seul le rôle prévu peut être notifié, et seulement si ping est activé
            allowed_mentions=discord.AllowedMentions(
                roles=[role] if role else False, everyone=False, users=False
            ),
        )

    @tasks.loop(minutes=1)
    async def verifier(self):
        cfg = self.bot.config.get("twitch", default={}) or {}
        chaine, salon_id = cfg.get("chaine"), cfg.get("salon_id")
        if not chaine or not salon_id:
            return  # section absente ou incomplète : rien à faire

        try:
            stream = await self.api.stream(chaine)
        except Exception as erreur:  # réseau coupé, identifiants faux...
            print(f"[TWITCH] requête impossible : {erreur}")
            return

        if stream is None:
            return  # hors ligne

        # Chaque diffusion a un identifiant unique : on n'annonce qu'une fois par live
        if await self.bot.db.lire_etat("twitch_dernier_stream") == stream["id"]:
            return

        salon = self.bot.get_channel(int(salon_id))
        if salon is None:
            print(f"[TWITCH] salon {salon_id} introuvable")
            return

        try:
            profil = await self.api.utilisateur(chaine)
        except Exception:
            profil = None  # sans avatar, l'annonce part quand même

        try:
            await self.envoyer_annonce(salon, stream, profil, ping=bool(cfg.get("ping", True)))
        except (ValueError, discord.HTTPException) as erreur:
            print(f"[TWITCH] annonce impossible : {erreur}")
            return  # on réessaiera à la prochaine minute

        await self.bot.db.ecrire_etat("twitch_dernier_stream", stream["id"])

    @verifier.before_loop
    async def avant_demarrage(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Twitch(bot))