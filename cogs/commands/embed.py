import re

import discord
from discord import app_commands
from discord.ext import commands

from components.view.embed_editor import EmbedEditeur, boutons_depuis_message
from utils.embed_builder import charger_json

LIEN_MESSAGE = re.compile(r"discord(?:app)?\.com/channels/(\d+)/(\d+)/(\d+)")


async def repondre(interaction: discord.Interaction, **kwargs):
    """Répond en privé, que la commande ait déjà été « différée » (defer) ou non."""
    kwargs.setdefault("ephemeral", True)
    if interaction.response.is_done():
        await interaction.followup.send(**kwargs)
    else:
        await interaction.response.send_message(**kwargs)


@app_commands.default_permissions(administrator=True)
@app_commands.guild_only()
class Embeds(commands.GroupCog, group_name="embed", group_description="Créer et modifier des embeds personnalisés"):
    def __init__(self, bot):
        self.bot = bot
        # Clic droit sur un message du bot > Applications > « Modifier embed »
        self.menu = app_commands.ContextMenu(name="Modifier embed", callback=self.menu_modifier)
        super().__init__()  # obligatoire pour un GroupCog

    async def cog_load(self):
        self.bot.tree.add_command(self.menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.menu.name, type=self.menu.type)

    # Vérification réelle des droits (le masquage de Discord ne suffit pas)
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.administrator:
            return True
        raise app_commands.CheckFailure("Réservé aux administrateurs.")

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CheckFailure):
            texte = "⛔ Cette commande est réservée aux administrateurs."
        else:
            print(f"[EMBED] erreur : {error!r}")
            texte = "❌ Une erreur est survenue (voir la console du bot)."
        await repondre(interaction, content=texte)

    # ---------------------------------------------------------------- /embed creer
    @app_commands.command(name="creer", description="Ouvre l'éditeur pour créer un nouvel embed")
    async def creer(self, interaction: discord.Interaction):
        editeur = EmbedEditeur(self.bot, interaction.user, interaction.channel)
        await interaction.response.send_message(
            content=editeur.contenu(), embed=editeur.apercu(), view=editeur, ephemeral=True
        )

    # ---------------------------------------------------------------- /embed modifier
    @app_commands.command(name="modifier", description="Modifie un message envoyé par le bot")
    @app_commands.describe(message="Lien du message (clic droit > Copier le lien) ou identifiant s'il est dans ce salon")
    async def modifier(self, interaction: discord.Interaction, message: str):
        await interaction.response.defer(ephemeral=True)  # récupérer le message peut prendre un instant
        cible = await self.trouver_message(interaction, message)
        if isinstance(cible, str):  # c'est un message d'erreur
            await repondre(interaction, content=cible)
            return
        await self.ouvrir_editeur(interaction, cible)

    # ---------------------------------------------------------------- /embed importer
    @app_commands.command(name="importer", description="Crée un embed à partir d'un fichier JSON")
    @app_commands.describe(fichier="Fichier .json (export de l'éditeur, ou JSON d'embed au format Discord)")
    async def importer(self, interaction: discord.Interaction, fichier: discord.Attachment):
        if fichier.size > 200_000:
            await repondre(interaction, content="❌ Fichier trop volumineux (200 Ko maximum).")
            return

        await interaction.response.defer(ephemeral=True)
        try:
            texte = (await fichier.read()).decode("utf-8-sig")
            embed, contenu, note = charger_json(texte)
        except UnicodeDecodeError:
            await repondre(interaction, content="❌ Le fichier n'est pas un texte UTF-8 valide.")
            return
        except ValueError as erreur:
            await repondre(interaction, content=f"❌ {erreur}")
            return

        editeur = EmbedEditeur(self.bot, interaction.user, interaction.channel, embed=embed, content=contenu)
        await repondre(interaction, content=editeur.contenu(note), embed=editeur.apercu(), view=editeur)

    # ---------------------------------------------------------------- clic droit > Modifier embed
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def menu_modifier(self, interaction: discord.Interaction, message: discord.Message):
        if not isinstance(interaction.user, discord.Member) or not interaction.user.guild_permissions.administrator:
            await repondre(interaction, content="⛔ Cette commande est réservée aux administrateurs.")
            return
        await self.ouvrir_editeur(interaction, message)

    # ---------------------------------------------------------------- outils
    async def ouvrir_editeur(self, interaction: discord.Interaction, message: discord.Message):
        if message.author.id != self.bot.user.id:
            await repondre(interaction, content="❌ Je ne peux modifier que les messages envoyés par le bot.")
            return

        riches = [e for e in message.embeds if e.type == "rich"]  # on ignore les aperçus de liens
        if len(riches) > 1:
            await repondre(
                interaction,
                content="❌ Ce message contient plusieurs embeds : l'éditeur n'en gère qu'un seul par message.",
            )
            return

        boutons, gerables = boutons_depuis_message(message)
        editeur = EmbedEditeur(
            self.bot, interaction.user, message.channel,
            embed=riches[0].to_dict() if riches else {},
            content=message.content,
            cible=message,
            boutons=boutons,
            boutons_gerables=gerables,
        )
        await repondre(interaction, content=editeur.contenu(), embed=editeur.apercu(), view=editeur)

    async def trouver_message(self, interaction: discord.Interaction, texte: str):
        """Renvoie le message demandé, ou une chaîne de caractères décrivant l'erreur."""
        texte = texte.strip()
        trouve = LIEN_MESSAGE.search(texte)

        if trouve:
            serveur_id, canal_id, message_id = map(int, trouve.groups())
            if serveur_id != interaction.guild.id:
                return "❌ Ce lien pointe vers un autre serveur."
        elif texte.isdigit():
            canal_id, message_id = interaction.channel.id, int(texte)
        else:
            return "❌ Donne un lien de message (clic droit > Copier le lien) ou un identifiant de message."

        canal = interaction.guild.get_channel_or_thread(canal_id)
        if canal is None:
            try:
                canal = await interaction.guild.fetch_channel(canal_id)
            except discord.HTTPException:
                return "❌ Salon introuvable."

        try:
            return await canal.fetch_message(message_id)
        except discord.NotFound:
            return "❌ Message introuvable."
        except discord.Forbidden:
            return "❌ Je n'ai pas accès à ce salon."
        except (discord.HTTPException, AttributeError):
            return "❌ Impossible de lire ce message."


async def setup(bot):
    await bot.add_cog(Embeds(bot))
