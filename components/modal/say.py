import discord

from utils.logs import envoyer_log


class SayModal(discord.ui.Modal, title="Parler en tant que bot"):
    message = discord.ui.TextInput(
        label="Message à envoyer",
        style=discord.TextStyle.paragraph,
        placeholder="Écris ton message ici...",
        max_length=2000,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.channel.send(self.message.value)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Je n'ai pas la permission d'écrire dans ce salon.", ephemeral=True
            )
            return

        # On répond d'abord : Discord exige une réponse en moins de 3 secondes
        await interaction.response.send_message("✅ Message envoyé.", ephemeral=True)

        # Puis on construit et on envoie le log
        embed = discord.Embed(
            title="📢 Commande /say utilisée",
            description=self.message.value,              # le contenu du message
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),            # date et heure, affichées dans le footer
        )
        embed.set_author(
            name=str(interaction.user),
            icon_url=interaction.user.display_avatar.url,
        )
        embed.add_field(
            name="Auteur",
            value=f"{interaction.user.mention} (`{interaction.user.id}`)",
            inline=True,
        )
        embed.add_field(name="Salon", value=interaction.channel.mention, inline=True)
        embed.set_footer(text="Commande /say")

        await envoyer_log(interaction.client, embed)