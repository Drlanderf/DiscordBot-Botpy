import discord
from discord import app_commands
from discord.ext import commands

from utils.journal import construire_embed_arrivee, construire_embed_depart
from utils.logs import envoyer_log


class DebugJournal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="debug_journal", description="Envoie un faux log d'arrivée ou de départ (test)")
    @app_commands.describe(genre="Arrivée ou départ")
    @app_commands.choices(
        genre=[
            app_commands.Choice(name="Arrivée", value="arrivee"),
            app_commands.Choice(name="Départ", value="depart"),
        ]
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def debug_journal(self, interaction: discord.Interaction, genre: app_commands.Choice[str]):
        cfg = self.bot.config.get("journal", default={}) or {}
        membre = interaction.user

        if genre.value == "arrivee":
            invitation = {
                "type": "invitation",
                "code": "test1234",
                "uses": 3,
                "max_uses": 10,
                "inviter_id": membre.id,
                "channel_id": interaction.channel.id,
                "vanity": False,
            }
            embed = construire_embed_arrivee(membre, invitation, int(cfg.get("compte_recent_jours", 7) or 0))
        else:
            embed = construire_embed_depart(membre, ("test1234", membre.id), None)

        embed.title = f"🧪 {embed.title} (test)"

        if await envoyer_log(self.bot, embed, cfg.get("salon_id")):
            await interaction.response.send_message("✅ Faux log envoyé.", ephemeral=True)
        else:
            await interaction.response.send_message(
                "❌ Envoi impossible : vérifie `journal.salon_id` (ou `salons.logs`) et les permissions du bot.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(DebugJournal(bot))