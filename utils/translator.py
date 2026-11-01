"""Traduit les noms et descriptions des commandes selon la langue du client Discord de chacun.

Les commandes sont déclarées en anglais dans le code (c'est la langue de base). Pour chaque langue,
Discord demande au bot la traduction : on la cherche dans locales/<langue>.json, section "commands".
Sans traduction, Discord affiche le texte anglais."""
from typing import Optional

import discord
from discord import app_commands

from utils.i18n import i18n, is_valid_translation


class CommandTranslator(app_commands.Translator):
    async def translate(self, string: app_commands.locale_str, locale: discord.Locale, context) -> Optional[str]:
        location = context.location.name  # command_name, command_description, parameter_name...
        est_menu = isinstance(context.data, app_commands.ContextMenu)

        # "fr" pour le français, "pt-br" puis "pt" pour le portugais brésilien...
        for code in (locale.value.lower(), locale.value.split("-")[0].lower()):
            texte = i18n.command_text(code, string.message)
            if texte is None:
                continue
            if is_valid_translation(texte, location, est_menu):
                return texte
            # Une traduction invalide ferait échouer toute la synchronisation : on l'ignore.
            print(f"[I18N] invalid translation ignored for '{string.message}' ({code}, {location}): {texte!r}")
            return None
        return None
