"""Internationalisation (i18n) : textes du bot dans plusieurs langues.

Deux usages :
  - t("cle", variable=...)  -> message du bot, dans la langue réglée par `language:` dans config.yaml
  - i18n.command_text(...)  -> traduction des noms/descriptions de commandes (voir utils/translator.py)

Les textes vivent dans locales/<langue>.json. L'anglais (en.json) est la langue de base :
si une clé manque dans la langue choisie, le texte anglais est utilisé.
Ce fichier n'utilise pas discord.py : il se teste seul.
"""
import json
import re
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"
BASE_LANGUAGE = "en"

# Nom de commande ou de paramètre accepté par Discord : minuscules, chiffres, - et _ (1 à 32 caractères)
NAME_PATTERN = re.compile(r"^[-_\w]{1,32}$")


def is_valid_translation(text, location: str, context_menu: bool = False) -> bool:
    """Vérifie qu'une traduction de commande respecte les règles de Discord.
    location : 'command_name', 'command_description', 'parameter_name', 'choice_name'..."""
    if not isinstance(text, str) or not text.strip():
        return False
    if location == "choice_name" or location.endswith("description"):
        return len(text) <= 100
    if context_menu:  # menus « clic droit » : espaces et majuscules autorisés
        return len(text) <= 32
    return bool(NAME_PATTERN.match(text)) and text == text.lower()


class I18n:
    def __init__(self, directory=LOCALES_DIR):
        self.directory = Path(directory)
        self.catalogs = {}
        self.language = BASE_LANGUAGE
        self.load()

    def load(self):
        """Lit tous les fichiers locales/*.json (le nom du fichier est le code de la langue)."""
        self.catalogs = {}
        for path in sorted(self.directory.glob("*.json")):
            try:
                with path.open(encoding="utf-8") as fichier:
                    self.catalogs[path.stem.lower()] = json.load(fichier)
            except (OSError, json.JSONDecodeError) as erreur:
                print(f"[I18N] cannot read {path.name}: {erreur}")

    def available(self) -> list[str]:
        return sorted(self.catalogs)

    def set_language(self, code) -> bool:
        """Choisit la langue des messages. Renvoie False (et retombe sur l'anglais) si elle n'existe pas."""
        code = str(code or BASE_LANGUAGE).strip().lower()
        if code in self.catalogs:
            self.language = code
            return True
        print(f"[I18N] language '{code}' not found (available: {', '.join(self.available()) or 'none'}), "
              f"using '{BASE_LANGUAGE}'")
        self.language = BASE_LANGUAGE
        return False

    def t(self, key: str, **values) -> str:
        """Message traduit. Langue choisie, sinon anglais, sinon la clé elle-même (pour repérer un oubli)."""
        for code in (self.language, BASE_LANGUAGE):
            texte = self.catalogs.get(code, {}).get("messages", {}).get(key)
            if texte is not None:
                break
        else:
            return key
        try:
            return texte.format(**values)
        except (KeyError, IndexError, ValueError):
            return texte  # variable manquante : on affiche le texte brut plutôt que de planter

    def command_text(self, code: str, message: str):
        """Traduction d'un nom ou d'une description de commande (le texte anglais sert de clé)."""
        return self.catalogs.get(code, {}).get("commands", {}).get(message)


i18n = I18n()


def t(key: str, **values) -> str:
    return i18n.t(key, **values)
