import discord
from discord import app_commands
from discord.ext import commands

from utils.moderation import (
    embed_sanction,
    executer_ban,
    gerer_erreur,
    log_moderation,
    moderateur_requis,
    texte_court,
    verifier_cible,
)


class Avertissements(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_app_command_error(self, interaction, error):
        await gerer_erreur(interaction, error)

    def seuil(self) -> int:
        try:
            return max(int(self.bot.config.get("moderation", "seuil_avertissements", default=3)), 1)
        except (TypeError, ValueError):
            return 3

    # ---------------------------------------------------------------- /warn
    @app_commands.command(name="warn", description="Donne un avertissement à un membre")
    @app_commands.describe(membre="Le membre à avertir", raison="Pourquoi (obligatoire)")
    @app_commands.guild_only()
    @moderateur_requis()
    async def warn(self, interaction: discord.Interaction, membre: discord.Member,
                   raison: app_commands.Range[str, 3, 300]):
        refus = verifier_cible(interaction, membre)
        if refus:
            await interaction.response.send_message(refus, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        await self.bot.db.ajouter_avertissement(membre.id, interaction.user.id, raison)
        total = len(await self.bot.db.lister_avertissements(membre.id))
        seuil = self.seuil()

        if total < seuil:
            embed = embed_sanction(
                "⚠️ Avertissement", discord.Color.gold(), membre, interaction.user, raison,
                [("Avertissements", f"{total} / {seuil}")],
            )
            await log_moderation(self.bot, embed)

            message = f"✅ Avertissement enregistré pour {membre} ({total}/{seuil})."
            if total == seuil - 1:
                message += "\n⚠️ Le prochain avertissement entraînera un bannissement automatique."
            await interaction.followup.send(message, ephemeral=True)
            return

        # Seuil atteint : bannissement automatique
        try:
            avertissements = await executer_ban(self.bot, membre, interaction.user, raison, "auto")
        except discord.HTTPException as erreur:
            await interaction.followup.send(
                f"⚠️ Avertissement enregistré ({total}/{seuil}), mais le bannissement automatique "
                f"a échoué : {erreur}",
                ephemeral=True,
            )
            return

        detail = "\n".join(
            f"**{i}.** {a['raison']} (<t:{a['date']}:d>, <@{a['moderateur_id']}>)"
            for i, a in enumerate(avertissements, 1)
        )
        embed = embed_sanction(
            "🔨 Bannissement automatique", discord.Color.red(), membre, interaction.user,
            f"{len(avertissements)} avertissements atteints (dernier : {raison})",
            [("Avertissements", detail)],
        )
        await log_moderation(self.bot, embed)
        await interaction.followup.send(
            f"🔨 {membre} a atteint {seuil} avertissements et a été banni automatiquement.", ephemeral=True
        )

    # --------------------------------------------------------------- /warns
    @app_commands.command(name="warns", description="Liste les avertissements d'un membre")
    @app_commands.describe(utilisateur="La personne dont tu veux voir les avertissements")
    @app_commands.guild_only()
    @moderateur_requis()
    async def warns(self, interaction: discord.Interaction, utilisateur: discord.User):
        liste = await self.bot.db.lister_avertissements(utilisateur.id)
        seuil = self.seuil()

        embed = discord.Embed(title=f"⚠️ Avertissements de {utilisateur}", color=discord.Color.gold())
        embed.set_thumbnail(url=utilisateur.display_avatar.url)

        if not liste:
            embed.description = "✅ Aucun avertissement."
        else:
            lignes = [
                f"**#{a['id']}** • <t:{a['date']}:R> • <@{a['moderateur_id']}>\n{a['raison']}"
                for a in liste[-10:]  # les 10 plus récents
            ]
            embed.description = texte_court("\n\n".join(lignes), 4000)
            embed.set_footer(text=f"{len(liste)} / {seuil} avant bannissement automatique")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Avertissements(bot))