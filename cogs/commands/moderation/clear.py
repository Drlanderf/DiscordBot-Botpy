from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from utils.moderation import gerer_erreur, log_moderation, moderateur_requis


class Clear(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_app_command_error(self, interaction, error):
        await gerer_erreur(interaction, error)

    @app_commands.command(name="clear", description="Supprime des messages dans ce salon")
    @app_commands.describe(
        nombre="Nombre de messages récents à examiner (1 à 100)",
        raison="Pourquoi (facultatif)",
    )
    @app_commands.guild_only()
    @moderateur_requis()
    async def clear(
        self,
        interaction: discord.Interaction,
        nombre: app_commands.Range[int, 1, 100],
        raison: app_commands.Range[str, 3, 300] = "Non précisée",
    ):
        await interaction.response.defer(ephemeral=True)  # la suppression peut prendre un instant

        # Discord ne supprime en masse que les messages de moins de 14 jours : on ignore aussi les épinglés
        limite = discord.utils.utcnow() - timedelta(days=13)
        try:
            supprimes = await interaction.channel.purge(
                limit=nombre,
                check=lambda m: not m.pinned and m.created_at > limite,
                reason=f"/clear par {interaction.user} : {raison}"[:500],
            )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Il me manque la permission **Gérer les messages** dans ce salon.", ephemeral=True
            )
            return
        except discord.HTTPException as erreur:
            await interaction.followup.send(f"❌ Suppression impossible : {erreur}", ephemeral=True)
            return

        if not supprimes:
            await interaction.followup.send(
                "Aucun message à supprimer (épinglés et de plus de 13 jours ignorés).", ephemeral=True
            )
            return

        embed = discord.Embed(title="🧹 Messages supprimés", color=discord.Color.blurple(),
                              timestamp=discord.utils.utcnow())
        embed.add_field(name="Modérateur", value=f"{interaction.user.mention}\n`{interaction.user.id}`", inline=True)
        embed.add_field(name="Salon", value=interaction.channel.mention, inline=True)
        embed.add_field(name="Messages", value=f"{len(supprimes)} supprimé(s) sur {nombre} examinés", inline=True)
        embed.add_field(name="Raison", value=raison, inline=False)
        embed.set_footer(text="Modération")
        await log_moderation(self.bot, embed)

        await interaction.followup.send(f"✅ {len(supprimes)} message(s) supprimé(s).", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Clear(bot))