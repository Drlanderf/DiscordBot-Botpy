import discord


async def envoyer_log(bot, embed: discord.Embed) -> bool:
    """Envoie un embed dans le salon de logs défini dans config.yaml."""
    salon_id = bot.config.get("salons", "logs", default=0)
    if not salon_id:
        return False  # pas de salon configuré : on ne fait rien

    salon = bot.get_channel(salon_id)
    if salon is None:
        print(f"[LOGS] salon {salon_id} introuvable")
        return False

    try:
        await salon.send(embed=embed)
    except discord.HTTPException as erreur:  # permission manquante, etc.
        print(f"[LOGS] envoi impossible : {erreur}")
        return False
    return True