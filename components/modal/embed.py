import re

import discord

from utils.embed_builder import charger_json, parse_couleur, url_valide


def _definir(embed: dict, cle: str, valeur):
    """Écrit la valeur dans l'embed, ou retire la clé si le champ a été vidé."""
    valeur = (valeur or "").strip()
    if valeur:
        embed[cle] = valeur
    else:
        embed.pop(cle, None)


def _url(champ: discord.ui.TextInput, nom: str, avertissements: list):
    """Renvoie l'URL saisie si elle est valide, None si le champ est vide ou invalide (avec avertissement)."""
    valeur = champ.value.strip()
    if not valeur:
        return None
    if url_valide(valeur):
        return valeur
    avertissements.append(f"{nom} ignoré (URL invalide : elle doit commencer par http:// ou https://)")
    return None


class TexteModal(discord.ui.Modal, title="Texte de l'embed"):
    def __init__(self, editeur):
        super().__init__()
        self.editeur = editeur
        e = editeur.embed

        self.titre = discord.ui.TextInput(
            label="Titre", required=False, max_length=256, default=e.get("title"),
        )
        self.description = discord.ui.TextInput(
            label="Description", style=discord.TextStyle.paragraph, required=False,
            max_length=4000, default=(e.get("description") or "")[:4000] or None,
        )
        self.couleur = discord.ui.TextInput(
            label="Couleur (#RRGGBB ou nom)", required=False, max_length=20,
            default=f"#{e['color']:06X}" if "color" in e else None,
            placeholder="#5865F2, rouge, vert, twitch…",
        )
        self.lien = discord.ui.TextInput(
            label="Lien du titre (URL)", required=False, max_length=500,
            default=e.get("url"), placeholder="https://…",
        )
        self.contenu = discord.ui.TextInput(
            label="Texte au-dessus de l'embed", style=discord.TextStyle.paragraph, required=False,
            max_length=2000, default=editeur.content or None,
            placeholder="Optionnel. Les mentions @rôle et #salon fonctionnent.",
        )
        for champ in (self.titre, self.description, self.couleur, self.lien, self.contenu):
            self.add_item(champ)

    async def on_submit(self, interaction: discord.Interaction):
        e, avertissements = self.editeur.embed, []

        _definir(e, "title", self.titre.value)
        _definir(e, "description", self.description.value)

        texte_couleur = self.couleur.value.strip()
        if not texte_couleur:
            e.pop("color", None)
        else:
            couleur = parse_couleur(texte_couleur)
            if couleur is None:
                avertissements.append("couleur ignorée (utilise #RRGGBB ou un nom comme rouge, vert, twitch)")
            else:
                e["color"] = couleur

        if not self.lien.value.strip():
            e.pop("url", None)
        else:
            lien = _url(self.lien, "lien du titre", avertissements)
            if lien:
                e["url"] = lien

        self.editeur.content = self.contenu.value.strip()
        await self.editeur.rafraichir(interaction, "; ".join(avertissements) or None)


class AuteurPiedModal(discord.ui.Modal, title="Auteur et pied de page"):
    def __init__(self, editeur):
        super().__init__()
        self.editeur = editeur
        auteur = editeur.embed.get("author", {})
        pied = editeur.embed.get("footer", {})

        self.auteur = discord.ui.TextInput(
            label="Nom de l'auteur (en haut)", required=False, max_length=256, default=auteur.get("name"),
        )
        self.auteur_icone = discord.ui.TextInput(
            label="Icône de l'auteur (URL image)", required=False, max_length=500, default=auteur.get("icon_url"),
        )
        self.auteur_lien = discord.ui.TextInput(
            label="Lien de l'auteur (URL)", required=False, max_length=500, default=auteur.get("url"),
        )
        self.pied = discord.ui.TextInput(
            label="Texte du pied de page", required=False, max_length=2048, default=pied.get("text"),
        )
        self.pied_icone = discord.ui.TextInput(
            label="Icône du pied de page (URL image)", required=False, max_length=500, default=pied.get("icon_url"),
        )
        for champ in (self.auteur, self.auteur_icone, self.auteur_lien, self.pied, self.pied_icone):
            self.add_item(champ)

    async def on_submit(self, interaction: discord.Interaction):
        e, avertissements = self.editeur.embed, []

        nom = self.auteur.value.strip()
        if nom:
            auteur = {"name": nom}
            icone = _url(self.auteur_icone, "icône de l'auteur", avertissements)
            lien = _url(self.auteur_lien, "lien de l'auteur", avertissements)
            if icone:
                auteur["icon_url"] = icone
            if lien:
                auteur["url"] = lien
            e["author"] = auteur
        else:
            e.pop("author", None)
            if self.auteur_icone.value.strip() or self.auteur_lien.value.strip():
                avertissements.append("auteur ignoré : il faut un nom")

        texte = self.pied.value.strip()
        if texte:
            pied = {"text": texte}
            icone = _url(self.pied_icone, "icône du pied de page", avertissements)
            if icone:
                pied["icon_url"] = icone
            e["footer"] = pied
        else:
            e.pop("footer", None)
            if self.pied_icone.value.strip():
                avertissements.append("pied de page ignoré : il faut un texte")

        await self.editeur.rafraichir(interaction, "; ".join(avertissements) or None)


class ImagesModal(discord.ui.Modal, title="Images de l'embed"):
    def __init__(self, editeur):
        super().__init__()
        self.editeur = editeur
        e = editeur.embed

        self.miniature = discord.ui.TextInput(
            label="Miniature (petite image à droite)", required=False, max_length=500,
            default=e.get("thumbnail", {}).get("url"), placeholder="https://… (lien direct vers une image)",
        )
        self.image = discord.ui.TextInput(
            label="Grande image (en bas)", required=False, max_length=500,
            default=e.get("image", {}).get("url"), placeholder="https://… (lien direct vers une image)",
        )
        self.add_item(self.miniature)
        self.add_item(self.image)

    async def on_submit(self, interaction: discord.Interaction):
        e, avertissements = self.editeur.embed, []

        for cle, champ, nom in (("thumbnail", self.miniature, "miniature"), ("image", self.image, "image")):
            if not champ.value.strip():
                e.pop(cle, None)
                continue
            url = _url(champ, nom, avertissements)
            if url:
                e[cle] = {"url": url}

        await self.editeur.rafraichir(interaction, "; ".join(avertissements) or None)


class ChampModal(discord.ui.Modal, title="Champ de l'embed"):
    def __init__(self, editeur, retour, index=None):
        super().__init__()
        self.editeur = editeur
        self.retour = retour  # fonction qui réaffiche la bonne vue après validation
        self.index = index
        champ = editeur.embed["fields"][index] if index is not None else {}

        self.nom = discord.ui.TextInput(label="Nom du champ", max_length=256, default=champ.get("name"))
        self.valeur = discord.ui.TextInput(
            label="Valeur", style=discord.TextStyle.paragraph, max_length=1024, default=champ.get("value"),
            placeholder="Le texte du champ. Le markdown et les liens [texte](url) fonctionnent.",
        )
        self.inline = discord.ui.TextInput(
            label="Côte à côte avec les autres ? (oui/non)", max_length=3,
            default="oui" if champ.get("inline", True) else "non",
        )
        for element in (self.nom, self.valeur, self.inline):
            self.add_item(element)

    async def on_submit(self, interaction: discord.Interaction):
        nom, valeur = self.nom.value.strip(), self.valeur.value.strip()
        if not nom or not valeur:
            await self.retour(interaction, "champ ignoré : le nom et la valeur sont obligatoires")
            return

        champ = {
            "name": nom,
            "value": valeur,
            "inline": self.inline.value.strip().lower() not in ("non", "n", "no", "false", "0"),
        }
        champs = self.editeur.embed.setdefault("fields", [])
        if self.index is None:
            if len(champs) >= 25:
                await self.retour(interaction, "25 champs au maximum")
                return
            champs.append(champ)
        else:
            champs[self.index] = champ
        await self.retour(interaction, None)


class BoutonModal(discord.ui.Modal, title="Bouton lien"):
    def __init__(self, editeur, retour):
        super().__init__()
        self.editeur = editeur
        self.retour = retour

        self.texte = discord.ui.TextInput(label="Texte du bouton", max_length=80)
        self.url = discord.ui.TextInput(label="Lien (URL)", max_length=500, placeholder="https://…")
        self.emoji = discord.ui.TextInput(
            label="Emoji (facultatif)", required=False, max_length=60, placeholder="🎮 ou <:nom:123456789>",
        )
        for champ in (self.texte, self.url, self.emoji):
            self.add_item(champ)

    async def on_submit(self, interaction: discord.Interaction):
        avertissements = []
        url = _url(self.url, "bouton", avertissements)
        texte = self.texte.value.strip()

        if url is None or not texte:
            await self.retour(interaction, "bouton ignoré : texte et lien valides obligatoires")
            return
        if len(self.editeur.boutons) >= 25:
            await self.retour(interaction, "25 boutons au maximum")
            return

        emoji = self.emoji.value.strip()
        avertissement = None
        # Un emoji valide est soit un emoji Unicode (non ASCII), soit un emoji de serveur <:nom:id>
        if emoji and not (re.fullmatch(r"<a?:\w+:\d+>", emoji) or not emoji.isascii()):
            emoji = ""
            avertissement = "emoji ignoré (utilise un emoji comme 🎮, ou le format <:nom:id>)"

        self.editeur.boutons.append({"label": texte, "url": url, "emoji": emoji})
        await self.retour(interaction, avertissement)


class JsonModal(discord.ui.Modal, title="Importer du JSON"):
    def __init__(self, editeur):
        super().__init__()
        self.editeur = editeur
        self.json = discord.ui.TextInput(
            label="JSON de l'embed", style=discord.TextStyle.paragraph, max_length=4000,
            placeholder='{"title": "Salut", "description": "…"}  (ou un JSON exporté)',
        )
        self.add_item(self.json)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            embed, contenu, note = charger_json(self.json.value)
        except ValueError as erreur:
            await self.editeur.rafraichir(interaction, f"import refusé : {erreur}")
            return

        self.editeur.embed = embed
        self.editeur.content = contenu
        self.editeur.maj_horodatage = False
        await self.editeur.rafraichir(interaction, note)
