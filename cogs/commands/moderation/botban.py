import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import construire_embed
from utils.messages import editer_message_sauvegarde


class BotbanCommande(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="botban", description="Envoie l'avertissement dans le salon piège")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def botban(self, interaction: discord.Interaction):
        cfg = self.bot.config.get("botban", default={}) or {}
        salon = self.bot.get_channel(int(cfg.get("salon_id") or 0))
        if salon is None:
            await interaction.response.send_message(
                "❌ `botban.salon_id` est absent ou introuvable dans config.yaml.", ephemeral=True
            )
            return

        try:
            message = await salon.send(embed=construire_embed(cfg))
        except discord.HTTPException as erreur:
            await interaction.response.send_message(f"❌ Envoi impossible : {erreur}", ephemeral=True)
            return

        await self.bot.db.sauvegarder_message("botban", salon.id, message.id)
        await interaction.response.send_message(f"✅ Avertissement envoyé dans {salon.mention}.", ephemeral=True)

    # Déclenché par /reload : met à jour l'avertissement déjà envoyé
    @commands.Cog.listener()
    async def on_config_reloaded(self):
        cfg = self.bot.config.get("botban", default={}) or {}
        if cfg:
            await editer_message_sauvegarde(self.bot, "botban", embed=construire_embed(cfg))


async def setup(bot):
    await bot.add_cog(BotbanCommande(bot))