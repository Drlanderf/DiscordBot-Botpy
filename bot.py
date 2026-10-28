import os
from pathlib import Path
import discord
from discord.ext import commands
from dotenv import load_dotenv
from config import Config
from database import Database

load_dotenv() # Chargement du .env

class Bot(commands.Bot):
    def __init__(self): # Constructeur du bot avec héritage
        super().__init__(command_prefix=commands.when_mentioned,intents=discord.Intents.all(),)
        self.config = Config()
        self.db = Database(self.config.dossier / "bot.db")

    async def close(self):
        await self.db.fermer()   # ferme proprement la base à l'arrêt du bot
        await super().close()
        
    async def setup_hook(self): # On charge les événements
        racine = Path(__file__).parent
        dossier_cogs = racine / "cogs"
        await self.db.connecter()
        for fichier in sorted(dossier_cogs.rglob("*.py")):
            if fichier.name.startswith("_"):
                continue
            module = ".".join(fichier.relative_to(racine).with_suffix("").parts)
            try:
                await self.load_extension(module)
                print(f"[OK]     {module}")
            except Exception as erreur:
                print(f"[ERREUR] {module} : {erreur}")

        guild_id = os.getenv("GUILD_ID")
        if guild_id:  # synchro instantanée sur ton serveur
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"[SYNC]   commandes synchronisées sur le serveur {guild_id}")
        else:  # synchro globale, peut mettre un moment à apparaître
            await self.tree.sync()
            print("[SYNC]   commandes synchronisées globalement")


token = os.getenv("DISCORD_TOKEN")
if token is None:
    raise SystemExit("DISCORD_TOKEN introuvable : vérifie ton fichier .env")

bot = Bot()
bot.run(token)