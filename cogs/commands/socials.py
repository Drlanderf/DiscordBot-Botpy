import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import construire_embed
from utils.i18n import t


class Socials(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # English base name: "socials". French users see "/reseaux" (see locales/fr.json).
    @app_commands.command(name="socials", description="Send the social networks embed")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.guild_only()
    async def socials(self, interaction: discord.Interaction):
        # The config key is still called "reseaux" for now (renaming config keys comes later).
        section = self.bot.config.get("reseaux")
        if not section:
            await interaction.response.send_message(t("socials.missing_section"), ephemeral=True)
            return

        try:
            await interaction.channel.send(embed=construire_embed(section))
        except discord.HTTPException as error:  # missing permission, embed too large...
            await interaction.response.send_message(t("common.send_failed", error=error), ephemeral=True)
            return

        await interaction.response.send_message(t("socials.sent"), ephemeral=True)


async def setup(bot):
    await bot.add_cog(Socials(bot))
