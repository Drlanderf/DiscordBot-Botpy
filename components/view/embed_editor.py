import copy
import io

import discord

from components.modal.embed import (
    AuteurPiedModal,
    BoutonModal,
    ChampModal,
    ImagesModal,
    JsonModal,
    TexteModal,
)
from utils.embed_builder import a_du_contenu, exporter_json, nettoyer, total_caracteres, tronquer, verifier
from utils.logs import envoyer_log


def boutons_depuis_message(message: discord.Message):
    """Lit les boutons-liens d'un message existant.
    Renvoie (liste de boutons, gerables). gerables=False si le message contient autre chose que
    des boutons-liens (boutons de rôles, menus...) : on n'y touche alors pas."""
    boutons, gerables = [], True
    for rangee in message.components:
        for composant in getattr(rangee, "children", []):
            if isinstance(composant, discord.Button) and composant.url:
                boutons.append({
                    "label": composant.label or "",
                    "url": composant.url,
                    "emoji": str(composant.emoji) if composant.emoji else "",
                })
            else:
                gerables = False
    return boutons, gerables


class EmbedEditeur(discord.ui.View):
    """L'éditeur : un message privé (éphémère) qui montre l'embed en direct, avec des boutons pour le modifier."""

    def __init__(self, bot, utilisateur, canal, embed=None, content="", cible=None, boutons=None,
                 boutons_gerables=True):
        super().__init__(timeout=1800)
        self.bot = bot
        self.utilisateur = utilisateur
        self.canal = canal                      # salon de destination (création)
        self.cible = cible                      # message à modifier (modification), sinon None
        self.embed = nettoyer(embed or {})      # l'embed, au format JSON de Discord
        self.content = content or ""            # texte au-dessus de l'embed
        self.boutons = list(boutons or [])      # boutons-liens : {"label", "url", "emoji"}
        self.boutons_gerables = boutons_gerables
        self.maj_horodatage = False             # True = l'heure est mise à jour à l'envoi
        self.original = (copy.deepcopy(self.embed), self.content, copy.deepcopy(self.boutons))

        if cible is not None:
            self.remove_item(self.choisir_canal)  # pas de choix de salon en modification
            self.btn_envoyer.label = "Mettre à jour le message"
        if not boutons_gerables:
            self.btn_boutons.disabled = True
        self._maj_etats()

    # ------------------------------------------------------------------ affichage
    def apercu(self) -> discord.Embed:
        if a_du_contenu(self.embed):
            try:
                return discord.Embed.from_dict(self.embed)
            except Exception:
                pass
        return discord.Embed(
            description="*Embed vide : utilise les boutons ci-dessous pour le remplir.*",
            color=self.embed.get("color") or discord.Color.light_grey(),
        )

    def contenu(self, avertissement=None) -> str:
        if self.cible is not None:
            lieu = f"✏️ Modification de [ce message]({self.cible.jump_url})"
        else:
            lieu = f"📤 Envoi dans {self.canal.mention}"

        total = total_caracteres(self.embed)
        champs = len(self.embed.get("fields", []))
        stats = f"`{champs}/25` champs • `{total}/6000` caractères • `{len(self.boutons)}` bouton(s) lien"
        if total > 6000:
            stats += " ⚠️"

        lignes = [f"**Éditeur d'embed** — {lieu}", stats]
        if self.content:
            resume = tronquer(" ".join(self.content.split()), 120)
            lignes.append(f"💬 Texte au-dessus : {resume}")
        if avertissement:
            lignes.append(f"⚠️ {avertissement}")
        return "\n".join(lignes)

    def _maj_etats(self):
        actif = "timestamp" in self.embed
        self.btn_horodatage.style = discord.ButtonStyle.success if actif else discord.ButtonStyle.secondary

    async def rafraichir(self, interaction: discord.Interaction, avertissement=None):
        self._maj_etats()
        await interaction.response.edit_message(
            content=self.contenu(avertissement), embed=self.apercu(), view=self
        )

    # ------------------------------------------------------------------ préparation de l'envoi
    def embed_final(self) -> dict:
        embed = copy.deepcopy(self.embed)
        if self.maj_horodatage and "timestamp" in embed:
            embed["timestamp"] = discord.utils.utcnow().isoformat()
        return embed

    def vue_boutons(self) -> discord.ui.View:
        vue = discord.ui.View(timeout=None)
        for bouton in self.boutons:
            vue.add_item(discord.ui.Button(
                label=bouton["label"] or None, url=bouton["url"], emoji=bouton.get("emoji") or None
            ))
        return vue

    # ------------------------------------------------------------------ ligne 1 : contenu
    @discord.ui.button(label="Texte", emoji="📝", style=discord.ButtonStyle.primary, row=0)
    async def btn_texte(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TexteModal(self))

    @discord.ui.button(label="Auteur & pied", emoji="👤", style=discord.ButtonStyle.primary, row=0)
    async def btn_auteur(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AuteurPiedModal(self))

    @discord.ui.button(label="Images", emoji="🖼️", style=discord.ButtonStyle.primary, row=0)
    async def btn_images(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ImagesModal(self))

    @discord.ui.button(label="Horodatage", emoji="🕒", style=discord.ButtonStyle.secondary, row=0)
    async def btn_horodatage(self, interaction: discord.Interaction, button: discord.ui.Button):
        if "timestamp" in self.embed:
            self.embed.pop("timestamp")
            self.maj_horodatage = False
        else:
            self.embed["timestamp"] = discord.utils.utcnow().isoformat()
            self.maj_horodatage = True  # l'heure sera celle de l'envoi
        await self.rafraichir(interaction)

    @discord.ui.button(label="Champs", emoji="🧩", style=discord.ButtonStyle.primary, row=0)
    async def btn_champs(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=self.contenu(), embed=self.apercu(), view=ChampsView(self)
        )

    # ------------------------------------------------------------------ ligne 2 : outils
    @discord.ui.button(label="Boutons liens", emoji="🔗", style=discord.ButtonStyle.secondary, row=1)
    async def btn_boutons(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content=self.contenu(), embed=self.apercu(), view=BoutonsView(self)
        )

    @discord.ui.button(label="Importer JSON", emoji="📥", style=discord.ButtonStyle.secondary, row=1)
    async def btn_importer(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(JsonModal(self))

    @discord.ui.button(label="Exporter JSON", emoji="📤", style=discord.ButtonStyle.secondary, row=1)
    async def btn_exporter(self, interaction: discord.Interaction, button: discord.ui.Button):
        texte = exporter_json(self.embed_final(), self.content)
        fichier = discord.File(io.BytesIO(texte.encode("utf-8")), filename="embed.json")
        await interaction.response.send_message(
            "📤 Voici le JSON de cet embed. Tu pourras le recharger avec **Importer JSON** ou `/embed importer`.",
            file=fichier,
            ephemeral=True,
        )

    @discord.ui.button(label="Réinitialiser", emoji="↩️", style=discord.ButtonStyle.secondary, row=1)
    async def btn_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.embed = copy.deepcopy(self.original[0])
        self.content = self.original[1]
        self.boutons = copy.deepcopy(self.original[2])
        self.maj_horodatage = False
        await self.rafraichir(interaction, "éditeur remis dans son état de départ")

    # ------------------------------------------------------------------ ligne 3 : salon
    @discord.ui.select(
        cls=discord.ui.ChannelSelect,
        channel_types=[discord.ChannelType.text, discord.ChannelType.news],
        placeholder="Salon de destination (par défaut : ce salon)",
        row=2,
    )
    async def choisir_canal(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        canal = interaction.guild.get_channel_or_thread(select.values[0].id)
        if canal is None:
            await self.rafraichir(interaction, "salon introuvable")
            return
        self.canal = canal
        await self.rafraichir(interaction)

    # ------------------------------------------------------------------ ligne 4 : validation
    @discord.ui.button(label="Envoyer", emoji="✅", style=discord.ButtonStyle.success, row=3)
    async def btn_envoyer(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.embed_final()
        problemes = verifier(embed, self.content)
        if problemes:
            await interaction.response.send_message("❌ " + "\n❌ ".join(problemes), ephemeral=True)
            return

        kwargs = {
            "content": self.content or None,
            "embed": discord.Embed.from_dict(embed) if a_du_contenu(embed) else None,
            # Les mentions de rôles et de membres fonctionnent, mais jamais @everyone / @here
            "allowed_mentions": discord.AllowedMentions(everyone=False, roles=True, users=True),
        }

        try:
            if self.cible is not None:
                if self.boutons_gerables:  # si le message a des boutons de rôles, on n'y touche pas
                    kwargs["view"] = self.vue_boutons() if self.boutons else None
                message = await self.cible.edit(**kwargs)
                action = "modifié"
            else:
                if self.boutons:
                    kwargs["view"] = self.vue_boutons()
                message = await self.canal.send(**kwargs)
                action = "envoyé"
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Je n'ai pas la permission d'écrire (ou de modifier) dans ce salon.", ephemeral=True
            )
            return
        except discord.HTTPException as erreur:
            await interaction.response.send_message(f"❌ Discord a refusé le message : {erreur}", ephemeral=True)
            return

        self.stop()
        await interaction.response.edit_message(
            content=f"✅ Message {action} : {message.jump_url}", embed=None, view=None
        )
        await self.journaliser(interaction, message, action)

    @discord.ui.button(label="Annuler", emoji="❌", style=discord.ButtonStyle.danger, row=3)
    async def btn_annuler(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.edit_message(content="❌ Édition annulée.", embed=None, view=None)

    async def journaliser(self, interaction: discord.Interaction, message: discord.Message, action: str):
        """Trace l'envoi dans le salon de logs (comme /say)."""
        log = discord.Embed(
            title=f"🧩 Commande /embed : message {action}",
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow(),
        )
        log.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
        log.add_field(name="Auteur", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
        log.add_field(name="Salon", value=message.channel.mention, inline=True)
        log.add_field(name="Message", value=f"[Aller au message]({message.jump_url})", inline=True)
        if self.embed.get("title"):
            log.add_field(name="Titre de l'embed", value=tronquer(self.embed["title"], 200), inline=False)
        log.set_footer(text="Commande /embed")
        await envoyer_log(self.bot, log)


class SousVue(discord.ui.View):
    """Base des écrans « Champs » et « Boutons » : une liste déroulante + des boutons d'action.
    Ils s'affichent dans le même message que l'éditeur, qu'on retrouve avec « Retour »."""

    def __init__(self, editeur: EmbedEditeur):
        super().__init__(timeout=1800)
        self.editeur = editeur
        self.selection = None  # position de l'élément choisi dans la liste

    def liste(self) -> list:
        raise NotImplementedError

    def libelle(self, element: dict) -> tuple[str, str]:
        """(titre, description) affichés dans la liste déroulante."""
        raise NotImplementedError

    def construire(self):
        raise NotImplementedError

    def choisi(self) -> bool:
        if self.selection is not None and self.selection >= len(self.liste()):
            self.selection = None
        return self.selection is not None

    def ajouter_selecteur(self, placeholder: str):
        elements = self.liste()
        if not elements:
            return
        options = []
        for i, element in enumerate(elements):
            titre, description = self.libelle(element)
            options.append(discord.SelectOption(
                label=tronquer(f"{i + 1}. {titre}", 100),
                value=str(i),
                description=tronquer(description, 100) or None,
                default=(i == self.selection),
            ))
        selecteur = discord.ui.Select(placeholder=placeholder, options=options, row=0)
        selecteur.callback = self.choisir
        self.add_item(selecteur)

    def ajouter_bouton(self, label, emoji, style, callback, row, disabled=False):
        bouton = discord.ui.Button(label=label, emoji=emoji, style=style, row=row, disabled=disabled)
        bouton.callback = callback
        self.add_item(bouton)

    async def choisir(self, interaction: discord.Interaction):
        self.selection = int(interaction.data["values"][0])
        await self.rafraichir(interaction)

    async def rafraichir(self, interaction: discord.Interaction, avertissement=None):
        self.construire()
        await interaction.response.edit_message(
            content=self.editeur.contenu(avertissement), embed=self.editeur.apercu(), view=self
        )

    async def retour(self, interaction: discord.Interaction):
        self.stop()
        await self.editeur.rafraichir(interaction)


class ChampsView(SousVue):
    def __init__(self, editeur: EmbedEditeur):
        super().__init__(editeur)
        self.construire()

    def liste(self) -> list:
        return self.editeur.embed.get("fields", [])

    def libelle(self, champ: dict):
        return champ["name"], champ["value"].replace("\n", " ")

    def construire(self):
        self.clear_items()
        champs, choisi = self.liste(), self.choisi()
        self.ajouter_selecteur("Choisis un champ à modifier, déplacer ou supprimer…")

        secondaire, danger = discord.ButtonStyle.secondary, discord.ButtonStyle.danger
        self.ajouter_bouton("Ajouter", "➕", discord.ButtonStyle.success, self.ajouter, 1, disabled=len(champs) >= 25)
        self.ajouter_bouton("Modifier", "✏️", secondaire, self.modifier, 1, disabled=not choisi)
        self.ajouter_bouton("Monter", "⬆️", secondaire, self.monter, 1, disabled=not choisi or self.selection == 0)
        self.ajouter_bouton(
            "Descendre", "⬇️", secondaire, self.descendre, 1,
            disabled=not choisi or self.selection == len(champs) - 1,
        )
        self.ajouter_bouton("Supprimer", "🗑️", danger, self.supprimer, 1, disabled=not choisi)
        self.ajouter_bouton("Retour", "⬅️", discord.ButtonStyle.primary, self.retour, 2)

    async def ajouter(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ChampModal(self.editeur, self.rafraichir))

    async def modifier(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ChampModal(self.editeur, self.rafraichir, self.selection))

    async def monter(self, interaction: discord.Interaction):
        champs, i = self.liste(), self.selection
        champs[i - 1], champs[i] = champs[i], champs[i - 1]
        self.selection = i - 1
        await self.rafraichir(interaction)

    async def descendre(self, interaction: discord.Interaction):
        champs, i = self.liste(), self.selection
        champs[i + 1], champs[i] = champs[i], champs[i + 1]
        self.selection = i + 1
        await self.rafraichir(interaction)

    async def supprimer(self, interaction: discord.Interaction):
        champs = self.liste()
        champs.pop(self.selection)
        if not champs:
            self.editeur.embed.pop("fields", None)  # pas de liste vide dans l'embed
        self.selection = None
        await self.rafraichir(interaction)


class BoutonsView(SousVue):
    def __init__(self, editeur: EmbedEditeur):
        super().__init__(editeur)
        self.construire()

    def liste(self) -> list:
        return self.editeur.boutons

    def libelle(self, bouton: dict):
        return bouton["label"], bouton["url"]

    def construire(self):
        self.clear_items()
        self.choisi()
        self.ajouter_selecteur("Choisis un bouton à supprimer…")

        self.ajouter_bouton(
            "Ajouter", "➕", discord.ButtonStyle.success, self.ajouter, 1, disabled=len(self.liste()) >= 25
        )
        self.ajouter_bouton(
            "Supprimer", "🗑️", discord.ButtonStyle.danger, self.supprimer, 1, disabled=self.selection is None
        )
        self.ajouter_bouton("Retour", "⬅️", discord.ButtonStyle.primary, self.retour, 2)

    async def ajouter(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BoutonModal(self.editeur, self.rafraichir))

    async def supprimer(self, interaction: discord.Interaction):
        self.liste().pop(self.selection)
        self.selection = None
        await self.rafraichir(interaction)
