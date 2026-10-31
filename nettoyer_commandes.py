"""Supprime TOUTES les slash commands enregistrées chez Discord pour ce bot
(globales + celles de chaque serveur).
À lancer bot arrêté, puis relancer le bot : il réenregistre uniquement les commandes actuelles."""
import asyncio
import os

import discord
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()


async def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise SystemExit("DISCORD_TOKEN manquant dans .env")

    client = discord.Client(intents=discord.Intents.none())
    arbre = app_commands.CommandTree(client)  # arbre vide : le synchroniser efface tout chez Discord

    async with client:
        await client.login(token)

        await arbre.sync()
        print("Commandes globales supprimées")

        async for guild in client.fetch_guilds():
            await arbre.sync(guild=guild)
            print(f"Commandes du serveur supprimées : {guild.name}")


asyncio.run(main())