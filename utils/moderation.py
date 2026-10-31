import discord
from discord import app_commands

from utils.logs import envoyer_log


def texte_court(texte: str, limite: int) -> str:
    return texte if len(texte) <= limite else texte[: limite - 1] + "…"


def est_moderateur(bot, membre: discord.Member) -> bool:
    """Administrateur, ou titulaire d'un des rôles listés dans moderation.roles."""
    if membre.guild_permissions.administrator:
        return True
    autorises = {int(r) for r in (bot.config.get("moderation", "roles", default=[]) or [])}
    return any(role.id in autorises for role in membre.roles)


def moderateur_requis():
    """Décorateur : réserve une commande à l'équipe de modération."""

    async def predicat(interaction: discord.Interaction) -> bool:
        if isinstance(interaction.user, discord.Member) and est_moderateur(interaction.client, interaction.user):
            return True
        raise app_commands.CheckFailure("Réservé à la modération.")

    return app_commands.check(predicat)


async def gerer_erreur(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Réponse commune quand une commande de modération échoue."""
    if isinstance(error, app_commands.CheckFailure):
        message = "⛔ Cette commande est réservée à l'équipe de modération."
    else:
        print(f"[MODÉRATION] erreur : {error!r}")
        message = "❌ Une erreur est survenue (voir la console du bot)."

    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


def verifier_cible(interaction: discord.Interaction, cible: discord.Member):
    """Renvoie un message d'erreur si la sanction est interdite, sinon None."""
    auteur, guild = interaction.user, interaction.guild

    if cible.id == auteur.id:
        return "❌ Tu ne peux pas te sanctionner toi-même."
    if cible.id == interaction.client.user.id:
        return "❌ Je ne peux pas me sanctionner moi-même."
    if cible.id == guild.owner_id:
        return "❌ Le propriétaire du serveur ne peut pas être sanctionné."
    if auteur.id != guild.owner_id and cible.top_role >= auteur.top_role:
        return "❌ Cette personne a un rôle supérieur ou égal au tien."
    if cible.top_role >= guild.me.top_role:
        return "❌ Mon rôle est trop bas pour sanctionner cette personne (place le rôle du bot plus haut)."
    return None


def embed_sanction(titre, couleur, cible, moderateur, raison, champs=()) -> discord.Embed:
    embed = discord.Embed(title=titre, color=couleur, timestamp=discord.utils.utcnow())
    embed.set_thumbnail(url=cible.display_avatar.url)
    embed.add_field(name="Membre", value=f"{cible.mention}\n`{cible.id}`", inline=True)
    embed.add_field(name="Modérateur", value=f"{moderateur.mention}\n`{moderateur.id}`", inline=True)
    for nom, valeur in champs:
        valeur = str(valeur)
        embed.add_field(name=nom, value=texte_court(valeur, 1024), inline=len(valeur) <= 40)
    embed.add_field(name="Raison", value=texte_court(raison, 1024), inline=False)
    embed.set_footer(text="Modération")
    return embed


async def log_moderation(bot, embed: discord.Embed) -> bool:
    """Envoie dans le salon moderation.salon_logs (sinon salons.logs)."""
    cfg = bot.config.get("moderation", default={}) or {}
    return await envoyer_log(bot, embed, cfg.get("salon_logs"))


async def executer_ban(bot, membre: discord.Member, moderateur, raison: str, type_: str, purge_heures: int = 0):
    """Bannit un membre et enregistre pourquoi, dans la liste des bans de Discord ET dans la base.
    Les avertissements du membre sont rattachés au ban puis supprimés de la table des avertissements.
    Renvoie la liste de ces avertissements. Lève discord.HTTPException si le ban échoue."""
    avertissements = await bot.db.lister_avertissements(membre.id)

    if type_ == "auto":
        detail = " | ".join(f"{i}) {a['raison']}" for i, a in enumerate(avertissements, 1))
        raison_discord = f"Auto, {len(avertissements)} avertissements : {detail}"
        raison_base = f"{len(avertissements)} avertissements"
    else:
        raison_discord = f"Ban par {moderateur} : {raison}"
        raison_base = raison

    # Cette raison est visible dans Paramètres du serveur > Bannissements, sans limite de durée
    await membre.ban(reason=texte_court(raison_discord, 500), delete_message_seconds=purge_heures * 3600)

    await bot.db.sauvegarder_ban(membre.id, str(membre), type_, moderateur.id, raison_base, avertissements)
    await bot.db.supprimer_avertissements(membre.id)
    return avertissements