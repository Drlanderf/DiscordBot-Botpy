import asyncio
from datetime import timedelta

import discord
from discord.ext import commands

from utils.journal import construire_embed_depart
from utils.logs import envoyer_log


class Departs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def trouver_cause(self, guild: discord.Guild, membre: discord.Member):
        """Cherche un kick ou un ban récent dans le journal d'audit. None = départ volontaire."""
        await asyncio.sleep(2)  # laisse au journal d'audit le temps d'enregistrer l'action
        limite = discord.utils.utcnow() - timedelta(seconds=30)
        try:
            async for entree in guild.audit_logs(limit=10):
                if entree.created_at < limite:
                    break
                if (
                    entree.target
                    and entree.target.id == membre.id
                    and entree.action in (discord.AuditLogAction.kick, discord.AuditLogAction.ban)
                ):
                    return entree
        except discord.HTTPException:  # permission « Voir les logs du serveur » manquante
            return None
        return None

    @commands.Cog.listener()
    async def on_member_remove(self, membre: discord.Member):
        cfg = self.bot.config.get("journal", default={}) or {}

        arrivee = await self.bot.db.lire_arrivee(membre.id)
        await self.bot.db.supprimer_arrivee(membre.id)

        cause = await self.trouver_cause(membre.guild, membre)

        # Les bans du salon piège ont déjà leur propre log : on évite le doublon
        if cause and cause.action == discord.AuditLogAction.ban and (cause.reason or "").startswith("Botban"):
            return

        embed = construire_embed_depart(membre, arrivee, cause)
        await envoyer_log(self.bot, embed, cfg.get("salon_id"))


async def setup(bot):
    await bot.add_cog(Departs(bot))