from discord.ext import commands
class Ready(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Connecté en tant que {self.bot.user}")
        print(f"Présent sur {len(self.bot.guilds)} serveur(s)")

async def setup(bot):
    await bot.add_cog(Ready(bot))