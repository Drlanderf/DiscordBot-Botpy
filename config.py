import os
import shutil
from pathlib import Path

import yaml

# Le modèle de config qui est copié au premier lancement
EXEMPLE = Path(__file__).parent / "config.example.yaml"


class Config:
    def __init__(self):
        # Dossier où vit le vrai config.yaml (./data par défaut, modifiable avec DATA_DIR dans le .env)
        self.dossier = Path(os.getenv("DATA_DIR", "./data")).resolve()
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.chemin = self.dossier / "config.yaml"
        self.donnees = {}
        self.recharger()

    def recharger(self):
        # Si config.yaml n'existe pas encore, on le crée à partir du modèle
        if not self.chemin.exists():
            shutil.copy(EXEMPLE, self.chemin)
        with self.chemin.open(encoding="utf-8") as f:
            self.donnees = yaml.safe_load(f) or {}

    def get(self, *cles, default=None):
        # config.get("salons", "compteur_vocal") va chercher salons -> compteur_vocal
        valeur = self.donnees
        for cle in cles:
            if not isinstance(valeur, dict) or cle not in valeur:
                return default
            valeur = valeur[cle]
        return valeur