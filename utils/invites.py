import discord


def instantane(invite: discord.Invite, vanity: bool = False) -> dict:
    """Garde l'essentiel d'une invitation (ce qu'on compare entre deux arrivées)."""
    return {
        "uses": invite.uses or 0,
        "max_uses": invite.max_uses or 0,  # 0 = illimité
        "inviter_id": invite.inviter.id if invite.inviter else None,
        "channel_id": invite.channel.id if invite.channel else None,
        "vanity": vanity,
    }


async def lire_invitations(guild: discord.Guild):
    """Renvoie {code: instantané} pour toutes les invitations du serveur,
    ou None si le bot n'a pas la permission « Gérer le serveur »."""
    try:
        invitations = await guild.invites()
    except discord.HTTPException:
        return None

    resultat = {i.code: instantane(i) for i in invitations}

    # Lien personnalisé (discord.gg/ton-nom) : il n'apparaît pas dans la liste ci-dessus
    if guild.vanity_url_code:
        try:
            vanity = await guild.vanity_invite()
            if vanity:
                resultat[vanity.code] = instantane(vanity, vanity=True)
        except discord.HTTPException:
            pass
    return resultat


def trouver_utilisees(avant: dict, apres: dict) -> list[str]:
    """Compare deux instantanés et renvoie les codes qui ont servi (normalement un seul)."""
    codes = [
        code for code, info in apres.items()
        if info["uses"] > avant.get(code, {}).get("uses", 0)
    ]
    # Une invitation à usage limité disparaît de la liste quand son dernier usage est consommé
    for code, info in avant.items():
        if code not in apres and info["max_uses"] and info["uses"] + 1 >= info["max_uses"]:
            codes.append(code)
    return codes