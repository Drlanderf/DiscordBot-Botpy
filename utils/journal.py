from datetime import timedelta

import discord


def duree_texte(duree: timedelta) -> str:
    """timedelta -> "3 j 4 h", "5 h 12 min" ou "8 min"."""
    secondes = int(duree.total_seconds())
    jours, reste = divmod(secondes, 86400)
    heures, reste = divmod(reste, 3600)
    minutes = reste // 60
    if jours:
        return f"{jours} j {heures} h"
    if heures:
        return f"{heures} h {minutes} min"
    return f"{minutes} min"


def construire_embed_arrivee(membre: discord.Member, invitation: dict, jours_recent: int = 7) -> discord.Embed:
    embed = discord.Embed(
        title="🤖 Nouveau bot" if membre.bot else "📥 Nouvel arrivant",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow(),
    )
    embed.set_author(name=str(membre), icon_url=membre.display_avatar.url)
    embed.set_thumbnail(url=membre.display_avatar.url)

    creation = (
        discord.utils.format_dt(membre.created_at, "D")
        + " ("
        + discord.utils.format_dt(membre.created_at, "R")
        + ")"
    )
    if jours_recent and not membre.bot and discord.utils.utcnow() - membre.created_at < timedelta(days=jours_recent):
        creation += "\n⚠️ Compte récent"

    embed.add_field(name="Membre", value=f"{membre.mention}\n`{membre.id}`", inline=True)
    embed.add_field(name="Compte créé", value=creation, inline=True)
    embed.add_field(name="Membres", value=str(membre.guild.member_count), inline=True)

    genre = invitation.get("type")
    if genre == "invitation":
        nom = f"`{invitation['code']}`" + (" (lien personnalisé)" if invitation.get("vanity") else "")
        if invitation.get("channel_id"):
            nom += f"\n<#{invitation['channel_id']}>"
        if invitation.get("inviter_id"):
            createur = f"<@{invitation['inviter_id']}>\n`{invitation['inviter_id']}`"
        else:
            createur = "—"
        maximum = invitation.get("max_uses")
        usages = f"{invitation['uses']} / {maximum}" if maximum else str(invitation["uses"])
        embed.add_field(name="Invitation", value=nom, inline=True)
        embed.add_field(name="Créée par", value=createur, inline=True)
        embed.add_field(name="Utilisations", value=usages, inline=True)
    elif genre == "plusieurs":
        lignes = [
            f"`{o['code']}`" + (f" par <@{o['inviter_id']}>" if o.get("inviter_id") else "")
            for o in invitation["options"]
        ]
        embed.add_field(
            name="Invitation",
            value="⚠️ Plusieurs possibilités (arrivées simultanées) :\n" + "\n".join(lignes),
            inline=False,
        )
    elif genre == "bot":
        embed.add_field(name="Invitation", value="🤖 Bot ajouté via OAuth2 (pas d'invitation)", inline=False)
    elif genre == "permission":
        embed.add_field(
            name="Invitation",
            value="⚠️ Impossible de lire les invitations : donne la permission **Gérer le serveur** au bot.",
            inline=False,
        )
    else:
        embed.add_field(
            name="Invitation",
            value="❓ Inconnue (lien expiré, découverte du serveur ou suivi pas encore prêt)",
            inline=False,
        )

    embed.set_footer(text="Journal des membres")
    return embed


def construire_embed_depart(membre: discord.Member, arrivee, cause) -> discord.Embed:
    """arrivee = (code, inviter_id) ou None. cause = entrée du journal d'audit (kick/ban) ou None."""
    if cause is None:
        titre, couleur = "📤 Départ", discord.Color.light_grey()
    elif cause.action == discord.AuditLogAction.ban:
        titre, couleur = "🔨 Banni", discord.Color.red()
    else:
        titre, couleur = "👢 Expulsé", discord.Color.orange()

    embed = discord.Embed(title=titre, color=couleur, timestamp=discord.utils.utcnow())
    embed.set_author(name=str(membre), icon_url=membre.display_avatar.url)
    embed.set_thumbnail(url=membre.display_avatar.url)

    embed.add_field(name="Membre", value=f"{membre.mention}\n`{membre.id}`", inline=True)
    if membre.joined_at:
        sejour = duree_texte(discord.utils.utcnow() - membre.joined_at)
        embed.add_field(
            name="Avait rejoint",
            value=f"{discord.utils.format_dt(membre.joined_at, 'D')}\nResté : {sejour}",
            inline=True,
        )
    embed.add_field(name="Membres restants", value=str(membre.guild.member_count), inline=True)

    if arrivee:
        code, inviter_id = arrivee
        origine = f"`{code}`" + (f" par <@{inviter_id}>" if inviter_id else "")
    else:
        origine = "—"
    embed.add_field(name="Invitation d'origine", value=origine, inline=True)

    if cause is not None:
        moderateur = cause.user.mention if cause.user else "inconnu"
        embed.add_field(name="Par", value=moderateur, inline=True)
        embed.add_field(name="Raison", value=cause.reason or "Aucune raison", inline=False)

    roles = [r.mention for r in reversed(membre.roles) if not r.is_default()]
    texte_roles = ", ".join(roles[:15]) + (" …" if len(roles) > 15 else "") if roles else "Aucun"
    embed.add_field(name="Rôles", value=texte_roles, inline=False)

    embed.set_footer(text="Journal des membres")
    return embed