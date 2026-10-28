import discord
from discord import app_commands
from discord.ext import commands


class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Vérifie que le bot répond")
    async def ping(self, interaction: discord.Interaction):
        latence = round(self.bot.latency * 1000)  # latency est en secondes, on convertit en ms
        await interaction.response.send_message(f"🏓 Pong ! ({latence} ms)", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Ping(bot))