import asyncio

import discord
from discord.ext import commands

from utils.invites import instantane, lire_invitations, trouver_utilisees
from utils.journal import construire_embed_arrivee
from utils.logs import envoyer_log


class Arrivees(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}               # guild_id -> {code: instantané}
        self.verrou = asyncio.Lock()  # une arrivée à la fois, pour comparer proprement

    @commands.Cog.listener()
    async def on_ready(self):
        # (Re)construit la mémoire des invitations de chaque serveur
        for guild in self.bot.guilds:
            invitations = await lire_invitations(guild)
            if invitations is None:
                print(f"[INVITES] {guild.name} : permission « Gérer le serveur » manquante, suivi impossible")
            else:
                self.cache[guild.id] = invitations

    @commands.Cog.listener()
    async def on_invite_create(self, invite: discord.Invite):
        # Une nouvelle invitation entre dans la mémoire avec son compteur à jour
        if invite.guild and invite.guild.id in self.cache:
            self.cache[invite.guild.id][invite.code] = instantane(invite)

    async def identifier_invitation(self, guild: discord.Guild) -> dict:
        async with self.verrou:
            apres = await lire_invitations(guild)
            if apres is None:
                return {"type": "permission"}

            avant = self.cache.get(guild.id)
            self.cache[guild.id] = apres
            if avant is None:
                return {"type": "inconnue"}

            infos = []
            for code in trouver_utilisees(avant, apres):
                if code in apres:
                    info = dict(apres[code])
                else:  # invitation à usage limité, épuisée donc disparue de la liste
                    info = {**avant[code], "uses": avant[code]["uses"] + 1}
                infos.append({"code": code, **info})

            if len(infos) == 1:
                return {"type": "invitation", **infos[0]}
            if len(infos) > 1:
                return {"type": "plusieurs", "options": infos}
            return {"type": "inconnue"}

    @commands.Cog.listener()
    async def on_member_join(self, membre: discord.Member):
        cfg = self.bot.config.get("journal", default={}) or {}

        invitation = {"type": "bot"} if membre.bot else await self.identifier_invitation(membre.guild)

        # On retient l'invitation pour pouvoir l'afficher dans le log de départ
        if invitation["type"] == "invitation":
            await self.bot.db.sauvegarder_arrivee(membre.id, invitation["code"], invitation.get("inviter_id"))

        try:
            jours = int(cfg.get("compte_recent_jours", 7) or 0)
        except (TypeError, ValueError):
            jours = 7

        embed = construire_embed_arrivee(membre, invitation, jours)
        await envoyer_log(self.bot, embed, cfg.get("salon_id"))


async def setup(bot):
    await bot.add_cog(Arrivees(bot))