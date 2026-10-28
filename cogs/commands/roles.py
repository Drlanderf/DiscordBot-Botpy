import re

import discord
from discord import app_commands
from discord.ext import commands

from components.button.role import RoleButton, construire_vue
from utils.embeds import construire_embed
from utils.messages import editer_message_sauvegarde


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="roles", description="Envoie un message de choix de rôles")
    @app_commands.describe(groupe="Le groupe de rôles à envoyer")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def roles(self, interaction: discord.Interaction, groupe: str):
        section = self.bot.config.get("groupes_roles", groupe)
        if not section or not section.get("roles"):
            await interaction.response.send_message(
                f"❌ Le groupe `{groupe}` est absent ou vide dans config.yaml.", ephemeral=True
            )
            return

        if not re.fullmatch(r"[a-z0-9_]+", groupe):
            await interaction.response.send_message(
                "❌ Le nom du groupe doit contenir uniquement des minuscules, chiffres et `_`.",
                ephemeral=True,
            )
            return

        if len(section["roles"]) > 25:
            await interaction.response.send_message("❌ Maximum 25 boutons par message.", ephemeral=True)
            return

        view = construire_vue(interaction.guild, groupe, section)
        try:
            message = await interaction.channel.send(embed=construire_embed(section), view=view)
        except discord.HTTPException as erreur:
            await interaction.response.send_message(f"❌ Envoi impossible : {erreur}", ephemeral=True)
            return

        # Un nom de mémoire par groupe : "roles_jeux", "roles_notifications"...
        await self.bot.db.sauvegarder_message(f"roles_{groupe}", message.channel.id, message.id)
        await interaction.response.send_message("✅ Message envoyé.", ephemeral=True)

    @roles.autocomplete("groupe")
    async def groupe_autocomplete(self, interaction: discord.Interaction, saisie: str):
        groupes = self.bot.config.get("groupes_roles", default={}) or {}
        return [
            app_commands.Choice(name=nom, value=nom)
            for nom in groupes
            if saisie.lower() in nom.lower()
        ][:25]

    # Déclenché par /reload : met à jour tous les groupes déjà envoyés
    @commands.Cog.listener()
    async def on_config_reloaded(self):
        groupes = self.bot.config.get("groupes_roles", default={}) or {}
        for nom, section in groupes.items():
            if not section or not section.get("roles"):
                continue

            reference = await self.bot.db.lire_message(f"roles_{nom}")
            if reference is None:  # ce groupe n'a jamais été envoyé
                continue
            salon = self.bot.get_channel(reference[0])
            if salon is None:
                continue

            await editer_message_sauvegarde(
                self.bot,
                f"roles_{nom}",
                embed=construire_embed(section),
                view=construire_vue(salon.guild, nom, section),
            )


async def setup(bot):
    bot.add_dynamic_items(RoleButton)
    await bot.add_cog(Roles(bot))