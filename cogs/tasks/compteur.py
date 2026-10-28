import discord
from discord.ext import commands, tasks
from utils.formatage import formater_membres

SALON_COMPTEUR_ID = 123456789012345678  # à remplacer par l'ID de ton salon vocal


class Compteur(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        self.mise_a_jour.start()      # lance la tâche quand le cog est chargé

    async def cog_unload(self):
        self.mise_a_jour.cancel()     # l'arrête si le cog est déchargé

    @tasks.loop(minutes=10)
    async def mise_a_jour(self):
        salon_id = self.bot.config.get("salons", "compteur_vocal", default=0)
        if not salon_id:
            print("[COMPTEUR] salons.compteur_vocal n'est pas renseigné dans config.yaml")
            return

        salon = self.bot.get_channel(salon_id)
        if salon is None:
            print(f"[COMPTEUR] salon {salon_id} introuvable")
            return

        nouveau_nom = f"👥・{formater_membres(salon.guild.member_count)} membres"
        if salon.name == nouveau_nom:  # rien n'a changé : on ne touche pas au salon
            return

        try:
            await salon.edit(name=nouveau_nom)
        except discord.HTTPException as erreur:  # permission manquante, limite atteinte...
            print(f"[COMPTEUR] {erreur}")

    @mise_a_jour.before_loop
    async def avant_demarrage(self):
        await self.bot.wait_until_ready()  # attend que le bot soit connecté


async def setup(bot):
    await bot.add_cog(Compteur(bot))