from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from utils.moderation import (
    embed_sanction,
    est_moderateur,
    executer_ban,
    gerer_erreur,
    log_moderation,
    moderateur_requis,
    texte_court,
    verifier_cible,
)

DUREES_TIMEOUT = [
    app_commands.Choice(name="5 minutes", value=5),
    app_commands.Choice(name="10 minutes", value=10),
    app_commands.Choice(name="30 minutes", value=30),
    app_commands.Choice(name="1 heure", value=60),
    app_commands.Choice(name="6 heures", value=360),
    app_commands.Choice(name="12 heures", value=720),
    app_commands.Choice(name="1 jour", value=1440),
    app_commands.Choice(name="3 jours", value=4320),
    app_commands.Choice(name="7 jours", value=10080),
]


class Sanctions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_app_command_error(self, interaction, error):
        await gerer_erreur(interaction, error)

    # ---------------------------------------------------------------- /kick
    @app_commands.command(name="kick", description="Expulse un membre (il pourra revenir)")
    @app_commands.describe(membre="Le membre à expulser", raison="Pourquoi (obligatoire)")
    @app_commands.guild_only()
    @moderateur_requis()
    async def kick(self, interaction: discord.Interaction, membre: discord.Member,
                   raison: app_commands.Range[str, 3, 300]):
        refus = verifier_cible(interaction, membre)
        if refus:
            await interaction.response.send_message(refus, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            await membre.kick(reason=texte_court(f"Kick par {interaction.user} : {raison}", 500))
        except discord.HTTPException as erreur:
            await interaction.followup.send(f"❌ Expulsion impossible : {erreur}", ephemeral=True)
            return

        await log_moderation(
            self.bot, embed_sanction("👢 Expulsion", discord.Color.orange(), membre, interaction.user, raison)
        )
        await interaction.followup.send(f"✅ {membre} a été expulsé.", ephemeral=True)

    # ------------------------------------------------------------- /timeout
    @app_commands.command(name="timeout", description="Réduit un membre au silence pour qu'il se calme")
    @app_commands.describe(membre="Le membre concerné", duree="Pendant combien de temps",
                           raison="Pourquoi (obligatoire)")
    @app_commands.choices(duree=DUREES_TIMEOUT)
    @app_commands.guild_only()
    @moderateur_requis()
    async def timeout(self, interaction: discord.Interaction, membre: discord.Member,
                      duree: app_commands.Choice[int], raison: app_commands.Range[str, 3, 300]):
        refus = verifier_cible(interaction, membre)
        if refus:
            await interaction.response.send_message(refus, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        fin = discord.utils.utcnow() + timedelta(minutes=duree.value)
        try:
            await membre.timeout(fin, reason=texte_court(f"Timeout par {interaction.user} : {raison}", 500))
        except discord.HTTPException as erreur:
            await interaction.followup.send(
                f"❌ Timeout impossible : {erreur} (les administrateurs ne peuvent pas être mis en timeout)",
                ephemeral=True,
            )
            return

        embed = embed_sanction(
            "🔇 Timeout", discord.Color.gold(), membre, interaction.user, raison,
            [("Durée", duree.name), ("Fin", discord.utils.format_dt(fin, "R"))],
        )
        await log_moderation(self.bot, embed)
        await interaction.followup.send(f"✅ {membre} est en timeout pour {duree.name}.", ephemeral=True)

    # ----------------------------------------------------------------- /ban
    @app_commands.command(name="ban", description="Bannit un membre (ignore le système d'avertissements)")
    @app_commands.describe(
        membre="Le membre à bannir",
        raison="Pourquoi (obligatoire)",
        purge_heures="Supprimer ses messages des X dernières heures (0 à 168)",
    )
    @app_commands.guild_only()
    @moderateur_requis()
    async def ban(self, interaction: discord.Interaction, membre: discord.Member,
                  raison: app_commands.Range[str, 3, 300],
                  purge_heures: app_commands.Range[int, 0, 168] = 0):
        refus = verifier_cible(interaction, membre)
        if refus:
            await interaction.response.send_message(refus, ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            avertissements = await executer_ban(self.bot, membre, interaction.user, raison, "manuel", purge_heures)
        except discord.HTTPException as erreur:
            await interaction.followup.send(f"❌ Bannissement impossible : {erreur}", ephemeral=True)
            return

        champs = []
        if purge_heures:
            champs.append(("Messages supprimés", f"{purge_heures} h"))
        if avertissements:
            detail = "\n".join(f"{i}. {a['raison']}" for i, a in enumerate(avertissements, 1))
            champs.append(("Avertissements précédents", detail))

        await log_moderation(
            self.bot, embed_sanction("🔨 Bannissement", discord.Color.red(), membre, interaction.user, raison, champs)
        )
        await interaction.followup.send(f"✅ {membre} a été banni.", ephemeral=True)

    # ------------------------------------------------------------- /baninfo
    @app_commands.command(name="baninfo", description="Pourquoi cette personne a-t-elle été bannie ?")
    @app_commands.describe(utilisateur="Pseudo (historique du bot) ou identifiant de la personne")
    @app_commands.guild_only()
    @moderateur_requis()
    async def baninfo(self, interaction: discord.Interaction, utilisateur: str):
        await interaction.response.defer(ephemeral=True)

        try:
            user_id = int(utilisateur.strip())
        except ValueError:
            await interaction.followup.send(
                "❌ Choisis une personne dans la liste proposée, ou colle son identifiant.", ephemeral=True
            )
            return

        ligne = await self.bot.db.lire_ban(user_id)

        # On interroge aussi la vraie liste des bans de Discord (statut actuel + bans faits hors du bot)
        statut, raison_discord, nom_discord = None, None, None
        try:
            entree = await interaction.guild.fetch_ban(discord.Object(id=user_id))
            statut, raison_discord, nom_discord = True, entree.reason, str(entree.user)
        except discord.NotFound:
            statut = False
        except discord.HTTPException:
            pass  # statut inconnu

        if ligne is None and statut is not True:
            await interaction.followup.send("Aucun bannissement trouvé pour cet identifiant.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"🔨 Bannissement de {ligne['nom'] if ligne else nom_discord}",
            color=discord.Color.red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Identifiant", value=f"`{user_id}`", inline=True)
        statut_texte = {True: "⛔ Toujours banni", False: "✅ N'est plus banni", None: "❓ Inconnu"}[statut]
        embed.add_field(name="Statut", value=statut_texte, inline=True)

        if ligne:
            auto = ligne["type"] == "auto"
            embed.add_field(name="Type", value="Automatique (avertissements)" if auto else "Manuel (/ban)", inline=True)
            embed.add_field(name="Date", value=f"<t:{ligne['date']}:f>", inline=True)
            par = f"<@{ligne['moderateur_id']}>" if ligne["moderateur_id"] else "—"
            embed.add_field(name="Déclenché par" if auto else "Par", value=par, inline=True)
            embed.add_field(name="Raison", value=texte_court(ligne["raison"], 1024), inline=False)
            if ligne["avertissements"]:
                lignes = [
                    f"**{i}.** {a['raison']} (<t:{a['date']}:d>, <@{a['moderateur_id']}>)"
                    for i, a in enumerate(ligne["avertissements"], 1)
                ]
                embed.add_field(name="Avertissements", value=texte_court("\n".join(lignes), 1024), inline=False)
        else:
            embed.add_field(
                name="Raison (liste des bans Discord)",
                value=texte_court(raison_discord or "Aucune raison", 1024),
                inline=False,
            )
            embed.set_footer(text="Banni en dehors des commandes du bot")

        await interaction.followup.send(embed=embed, ephemeral=True)

    @baninfo.autocomplete("utilisateur")
    async def utilisateur_autocomplete(self, interaction: discord.Interaction, saisie: str):
        # Les noms des bannis ne sont proposés qu'à l'équipe de modération
        if not isinstance(interaction.user, discord.Member) or not est_moderateur(self.bot, interaction.user):
            return []
        lignes = await self.bot.db.chercher_bans(saisie)
        return [
            app_commands.Choice(name=texte_court(f"{nom} ({uid})", 100), value=str(uid))
            for uid, nom in lignes
        ]


async def setup(bot):
    await bot.add_cog(Sanctions(bot))