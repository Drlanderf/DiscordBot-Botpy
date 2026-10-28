import discord
from discord import app_commands
from discord.ext import commands

from components.modal.say import SayModal


class Say(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="say", description="Envoyer un message en tant que bot")
    @app_commands.default_permissions(administrator=True)       # masquée pour les non-admins
    @app_commands.checks.has_permissions(administrator=True)    # et vraiment refusée à leur place
    @app_commands.guild_only()
    async def say(self, interaction: discord.Interaction):
        # send_modal doit être la PREMIÈRE réponse à la commande : il ouvre le formulaire.
        await interaction.response.send_modal(SayModal())


async def setup(bot):
    await bot.add_cog(Say(bot))