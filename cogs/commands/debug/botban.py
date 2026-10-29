import discord
from discord import app_commands
from discord.ext import commands

from utils.botban import construire_embed_log
from utils.logs import envoyer_log


class DebugBotban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="debug_botban", description="Envoie un faux log de botban (aucun ban)")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def debug_botban(self, interaction: discord.Interaction):
        cfg = self.bot.config.get("botban", default={}) or {}
        salon = self.bot.get_channel(int(cfg.get("salon_id") or 0)) or interaction.channel

        embed = construire_embed_log(
            titre="🧪 Botban : test (aucun ban)",
            couleur=discord.Color.orange(),
            membre=interaction.user,
            salon=salon,
            texte="Ceci est un message de test. https://exemple.com/lien-de-spam",
            nb_pieces_jointes=0,
            resultat="🧪 Simulation : personne n'a été banni",
        )

        if await envoyer_log(self.bot, embed, cfg.get("salon_logs")):
            await interaction.response.send_message("✅ Faux log envoyé.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Envoi impossible : vérifie `botban.salon_logs` (ou `salons.logs`) et les permissions du bot.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(DebugBotban(bot))