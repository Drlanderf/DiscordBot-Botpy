import discord
from discord.ext import commands

from utils.botban import construire_embed_log
from utils.logs import envoyer_log


class Botban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.en_cours = set()  # membres en cours de traitement (évite les doublons si le bot spamme)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        cfg = self.bot.config.get("botban", default={}) or {}
        salon_id = int(cfg.get("salon_id") or 0)

        # On ne s'intéresse qu'aux messages du salon piège, écrits par de vrais membres
        if not salon_id or message.channel.id != salon_id:
            return
        if message.guild is None or message.author.bot or not isinstance(message.author, discord.Member):
            return

        membre = message.author
        perms = membre.guild_permissions
        if perms.administrator or perms.manage_messages:
            return  # le staff n'est jamais banni par ce salon

        if membre.id in self.en_cours:  # déjà en train de le bannir : on supprime juste ce message
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            return

        self.en_cours.add(membre.id)
        try:
            await self.bannir(message, membre, cfg)
        finally:
            self.en_cours.discard(membre.id)

    async def bannir(self, message: discord.Message, membre: discord.Member, cfg: dict):
        try:
            heures = min(max(int(cfg.get("purge_heures", 24)), 0), 168)  # Discord accepte 0 à 7 jours
        except (TypeError, ValueError):
            heures = 24

        # On garde les infos AVANT le ban, car le message va être supprimé
        texte = message.content
        nb_pieces = len(message.attachments)
        salon = message.channel

        try:
            await membre.ban(
                reason=f"Botban : message posté dans #{salon.name}",
                delete_message_seconds=heures * 3600,
            )
            titre, couleur = "🔨 Botban : membre banni", discord.Color.red()
            resultat = f"✅ Banni, ses messages des dernières {heures} h sont supprimés" if heures else "✅ Banni"
        except discord.HTTPException as erreur:
            # Forbidden : rôle du bot trop bas ou permission manquante. On supprime au moins le message.
            try:
                await message.delete()
            except discord.HTTPException:
                pass
            titre, couleur = "⚠️ Botban : ban impossible", discord.Color.orange()
            resultat = f"❌ Ban impossible ({erreur}). Message supprimé."

        print(f"[BOTBAN] {membre} ({membre.id}) : {resultat}")
        embed = construire_embed_log(titre, couleur, membre, salon, texte, nb_pieces, resultat)
        await envoyer_log(self.bot, embed, cfg.get("salon_logs"))


async def setup(bot):
    await bot.add_cog(Botban(bot))