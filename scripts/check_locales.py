"""Vérifie les fichiers de langue (locales/*.json).

Usage : python scripts/check_locales.py [dossier]
Contrôle, pour chaque langue par rapport à en.json :
  - aucune clé manquante ni en trop dans "messages"
  - les mêmes variables {comme_ceci} dans chaque texte
  - des traductions de commandes conformes aux règles de Discord
Quitte avec le code 1 s'il y a une erreur (utilisable en CI)."""
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from utils.i18n import BASE_LANGUAGE, is_valid_translation  # noqa: E402

VARIABLE = re.compile(r"\{(\w*)\}")
ressemble_a_un_nom = re.compile(r"^[a-z0-9_-]{1,32}$")


def main(dossier: Path) -> int:
    erreurs, catalogues = [], {}

    for chemin in sorted(dossier.glob("*.json")):
        try:
            catalogues[chemin.stem.lower()] = json.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as erreur:
            erreurs.append(f"{chemin.name}: unreadable JSON ({erreur})")

    if BASE_LANGUAGE not in catalogues:
        erreurs.append(f"{BASE_LANGUAGE}.json is missing (it is the base language)")
    else:
        base = catalogues[BASE_LANGUAGE].get("messages", {})

        for code, catalogue in catalogues.items():
            messages = catalogue.get("messages", {})

            for cle in base:
                if cle not in messages:
                    erreurs.append(f"{code}: missing key '{cle}'")
            for cle, texte in messages.items():
                if cle not in base:
                    erreurs.append(f"{code}: unknown key '{cle}' (not in {BASE_LANGUAGE}.json)")
                elif set(VARIABLE.findall(texte)) != set(VARIABLE.findall(base[cle])):
                    erreurs.append(f"{code}: variables differ in '{cle}' (expected {sorted(set(VARIABLE.findall(base[cle])))})")

            for source, texte in catalogue.get("commands", {}).items():
                # Une source du type "socials" est un nom ; une phrase est une description
                lieu = "command_name" if ressemble_a_un_nom.match(source) else "command_description"
                if not is_valid_translation(texte, lieu):
                    erreurs.append(f"{code}: invalid command translation for '{source}' -> {texte!r} ({lieu})")

    for erreur in erreurs:
        print(f"ERROR  {erreur}")
    if erreurs:
        print(f"\n{len(erreurs)} problem(s) found.")
        return 1

    print(f"OK  {len(catalogues)} language(s) checked: {', '.join(sorted(catalogues))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "locales"))
