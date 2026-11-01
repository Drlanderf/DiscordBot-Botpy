"""Fonctions communes à l'éditeur d'embeds.
Ce fichier n'utilise pas discord.py : il manipule des dictionnaires au format JSON des embeds Discord."""
import json
import re
from datetime import datetime

COULEURS = {
    "rouge": 0xED4245, "vert": 0x57F287, "bleu": 0x3498DB, "jaune": 0xFEE75C,
    "orange": 0xE67E22, "violet": 0x9B59B6, "rose": 0xEB459E, "noir": 0x000000,
    "blanc": 0xFFFFFF, "gris": 0x95A5A6, "blurple": 0x5865F2,
    "twitch": 0x9146FF, "youtube": 0xFF0000,
}

# Un embed n'est affichable que s'il contient au moins l'un de ces éléments
CLES_VISIBLES = ("title", "description", "fields", "image", "thumbnail", "author", "footer")


def tronquer(texte: str, limite: int) -> str:
    return texte if len(texte) <= limite else texte[: limite - 1] + "…"


def url_valide(texte) -> bool:
    return (
        isinstance(texte, str)
        and texte.startswith(("http://", "https://"))
        and " " not in texte
        and len(texte) <= 2048
    )


def parse_couleur(texte: str):
    """Accepte #RRGGBB, RRGGBB, 0xRRGGBB ou un nom (rouge, vert, twitch...). Renvoie un entier ou None."""
    t = texte.strip().lower()
    if t in COULEURS:
        return COULEURS[t]
    t = t.removeprefix("#").removeprefix("0x")
    return int(t, 16) if re.fullmatch(r"[0-9a-f]{6}", t) else None


def a_du_contenu(embed: dict) -> bool:
    return any(embed.get(cle) for cle in CLES_VISIBLES)


def total_caracteres(embed: dict) -> int:
    """Discord limite un embed à 6000 caractères au total."""
    total = len(embed.get("title", "")) + len(embed.get("description", ""))
    total += len(embed.get("footer", {}).get("text", "")) + len(embed.get("author", {}).get("name", ""))
    for champ in embed.get("fields", []):
        total += len(champ["name"]) + len(champ["value"])
    return total


def _texte(valeur):
    return valeur.strip() if isinstance(valeur, str) and valeur.strip() else None


def nettoyer(brut) -> dict:
    """Ne garde que les éléments d'embed connus et bien formés (retire proxy_url, width, type, etc.)."""
    if not isinstance(brut, dict):
        return {}
    sortie = {}

    for cle in ("title", "description", "url"):
        texte = _texte(brut.get(cle))
        if texte:
            sortie[cle] = texte

    couleur = brut.get("color")
    if isinstance(couleur, str):
        couleur = parse_couleur(couleur)
    if isinstance(couleur, int) and not isinstance(couleur, bool) and 0 <= couleur <= 0xFFFFFF:
        sortie["color"] = couleur

    horodatage = brut.get("timestamp")
    if isinstance(horodatage, str):
        try:
            datetime.fromisoformat(horodatage.replace("Z", "+00:00"))
            sortie["timestamp"] = horodatage
        except ValueError:
            pass

    for cle in ("image", "thumbnail"):
        element = brut.get(cle)
        if isinstance(element, dict) and _texte(element.get("url")):
            sortie[cle] = {"url": element["url"].strip()}

    auteur = brut.get("author")
    if isinstance(auteur, dict) and _texte(auteur.get("name")):
        sortie["author"] = {k: auteur[k].strip() for k in ("name", "url", "icon_url") if _texte(auteur.get(k))}

    pied = brut.get("footer")
    if isinstance(pied, dict) and _texte(pied.get("text")):
        sortie["footer"] = {k: pied[k].strip() for k in ("text", "icon_url") if _texte(pied.get(k))}

    champs = []
    for champ in brut.get("fields") or []:
        if isinstance(champ, dict) and champ.get("name") not in (None, "") and champ.get("value") not in (None, ""):
            champs.append({
                "name": str(champ["name"]),
                "value": str(champ["value"]),
                "inline": bool(champ.get("inline", False)),
            })
    if champs:
        sortie["fields"] = champs[:25]

    return sortie


def verifier(embed: dict, content: str) -> list[str]:
    """Renvoie la liste des problèmes qui empêcheraient l'envoi (vide = tout est bon)."""
    problemes = []

    if not a_du_contenu(embed) and not content.strip():
        problemes.append(
            "Le message est vide : ajoute du texte au-dessus, ou du contenu dans l'embed (titre, description, champ, image…)."
        )
    if len(content) > 2000:
        problemes.append("Le texte au-dessus de l'embed dépasse 2000 caractères.")

    if len(embed.get("title", "")) > 256:
        problemes.append("Le titre dépasse 256 caractères.")
    if len(embed.get("description", "")) > 4096:
        problemes.append("La description dépasse 4096 caractères.")
    if len(embed.get("footer", {}).get("text", "")) > 2048:
        problemes.append("Le pied de page dépasse 2048 caractères.")
    if len(embed.get("author", {}).get("name", "")) > 256:
        problemes.append("Le nom de l'auteur dépasse 256 caractères.")

    champs = embed.get("fields", [])
    if len(champs) > 25:
        problemes.append("Un embed accepte 25 champs au maximum.")
    for i, champ in enumerate(champs, 1):
        if len(champ["name"]) > 256 or len(champ["value"]) > 1024:
            problemes.append(f"Le champ {i} est trop long (nom : 256, valeur : 1024 caractères maximum).")

    if total_caracteres(embed) > 6000:
        problemes.append("L'embed dépasse 6000 caractères au total.")

    urls = [
        ("lien du titre", embed.get("url")),
        ("image", embed.get("image", {}).get("url")),
        ("miniature", embed.get("thumbnail", {}).get("url")),
        ("lien de l'auteur", embed.get("author", {}).get("url")),
        ("icône de l'auteur", embed.get("author", {}).get("icon_url")),
        ("icône du pied de page", embed.get("footer", {}).get("icon_url")),
    ]
    for nom, url in urls:
        if url and not url_valide(url):
            problemes.append(f"URL invalide : {nom} (elle doit commencer par http:// ou https://).")

    return problemes


def charger_json(texte: str):
    """Lit un JSON d'embed. Accepte :
       - un embed seul : {"title": "...", ...}
       - un message complet : {"content": "...", "embeds": [{...}]}
       - une liste d'embeds : [{...}]
    Renvoie (embed, texte_au_dessus, note). Lève ValueError si le JSON est inutilisable."""
    try:
        brut = json.loads(texte)
    except json.JSONDecodeError as erreur:
        raise ValueError(f"JSON invalide (ligne {erreur.lineno}, colonne {erreur.colno}) : {erreur.msg}") from erreur

    note = None
    contenu = ""

    if isinstance(brut, list):
        brut = {"embeds": brut}
    if not isinstance(brut, dict):
        raise ValueError("Le JSON doit décrire un embed (un objet entre accolades).")

    if "embeds" in brut or "content" in brut:
        contenu = brut.get("content") or ""
        embeds = brut.get("embeds") or []
        if len(embeds) > 1:
            note = f"Le JSON contient {len(embeds)} embeds : seul le premier est chargé."
        brut_embed = embeds[0] if embeds else {}
    else:
        brut_embed = brut

    if not isinstance(brut_embed, dict):
        raise ValueError("L'embed du JSON est mal formé.")

    return nettoyer(brut_embed), str(contenu)[:2000], note


def exporter_json(embed: dict, content: str) -> str:
    charge = {}
    if content:
        charge["content"] = content
    charge["embeds"] = [embed] if a_du_contenu(embed) else []
    return json.dumps(charge, ensure_ascii=False, indent=2)
