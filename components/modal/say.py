import discord

from utils.i18n import t
from utils.logs import envoyer_log


class SayModal(discord.ui.Modal):
    def __init__(self):
        # Le titre et les libellés sont construits ici (et non dans la classe)
        # pour suivre la langue réglée dans config.yaml au moment de l'ouverture du formulaire.
        super().__init__(title=t("say.modal.title"))
        self.message = discord.ui.TextInput(
            label=t("say.modal.label"),
            style=discord.TextStyle.paragraph,  # multi-line text area
            placeholder=t("say.modal.placeholder"),
            max_length=2000,                    # Discord message limit
            required=True,
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.channel.send(self.message.value)
        except discord.Forbidden:
            await interaction.response.send_message(t("say.forbidden"), ephemeral=True)
            return

        # Discord requires an answer within 3 seconds
        await interaction.response.send_message(t("say.sent"), ephemeral=True)

        # Then we build and send the log
        embed = discord.Embed(
            title=t("say.log.title"),
            description=self.message.value,
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),  # shown in the footer, in each reader's timezone
        )
        embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        embed.add_field(
            name=t("say.log.author"),
            value=f"{interaction.user.mention} (`{interaction.user.id}`)",
            inline=True,
        )
        embed.add_field(name=t("say.log.channel"), value=interaction.channel.mention, inline=True)
        embed.set_footer(text=t("say.log.footer"))

        await envoyer_log(interaction.client, embed)
