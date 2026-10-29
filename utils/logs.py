import discord


async def envoyer_log(bot, embed: discord.Embed, salon_id: int | None = None) -> bool:
    """Envoie un embed dans un salon de logs.
    Sans salon_id, utilise salons.logs de config.yaml."""
    salon_id = salon_id or bot.config.get("salons", "logs", default=0)
    if not salon_id:
        return False  # pas de salon configuré : on ne fait rien

    salon = bot.get_channel(int(salon_id))
    if salon is None:
        print(f"[LOGS] salon {salon_id} introuvable")
        return False

    try:
        await salon.send(embed=embed)
    except discord.HTTPException as erreur:  # permission manquante, etc.
        print(f"[LOGS] envoi impossible : {erreur}")
        return False
    return True