import discord

async def editer_message_sauvegarde(bot, nom: str, **contenu) -> bool:
    """Réédite le message enregistré sous ce nom. Renvoie True si ça a marché."""
    reference = await bot.db.lire_message(nom)
    if reference is None:
        return False  # /roles n'a jamais été envoyé depuis qu'on mémorise les messages

    salon_id, message_id = reference
    try:
        salon = bot.get_channel(salon_id) or await bot.fetch_channel(salon_id)
        message = await salon.fetch_message(message_id)
        await message.edit(**contenu)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException) as erreur:
        print(f"[MESSAGES] impossible de mettre à jour '{nom}' : {erreur}")
        return False
    return True