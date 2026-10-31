import json
import time
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages_envoyes (
    nom        TEXT PRIMARY KEY,
    salon_id   INTEGER NOT NULL,
    message_id INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS etat (
    cle    TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS arrivees (
    user_id    INTEGER PRIMARY KEY,
    code       TEXT NOT NULL,
    inviter_id INTEGER
);
CREATE TABLE IF NOT EXISTS avertissements (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    moderateur_id INTEGER NOT NULL,
    raison        TEXT NOT NULL,
    date          INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_avertissements_user ON avertissements (user_id);
CREATE TABLE IF NOT EXISTS bannissements (
    user_id        INTEGER PRIMARY KEY,
    nom            TEXT NOT NULL,
    type           TEXT NOT NULL,      -- 'manuel' ou 'auto'
    moderateur_id  INTEGER,
    raison         TEXT NOT NULL,
    avertissements TEXT,               -- JSON : [[raison, date, moderateur_id], ...]
    date           INTEGER NOT NULL
);
"""


class Database:
    def __init__(self, chemin: Path):
        self.chemin = chemin
        self.conn = None

    async def connecter(self):
        self.conn = await aiosqlite.connect(self.chemin)
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def fermer(self):
        if self.conn:
            await self.conn.close()

    # --- messages envoyés par le bot (pour pouvoir les modifier plus tard) ---
    async def sauvegarder_message(self, nom: str, salon_id: int, message_id: int):
        await self.conn.execute(
            "INSERT INTO messages_envoyes (nom, salon_id, message_id) VALUES (?, ?, ?) "
            "ON CONFLICT(nom) DO UPDATE SET salon_id = excluded.salon_id, "
            "message_id = excluded.message_id",
            (nom, salon_id, message_id),
        )
        await self.conn.commit()

    async def lire_message(self, nom: str):
        async with self.conn.execute(
            "SELECT salon_id, message_id FROM messages_envoyes WHERE nom = ?", (nom,)
        ) as curseur:
            ligne = await curseur.fetchone()
        return (ligne[0], ligne[1]) if ligne else None

    # --- petite mémoire clé/valeur (ex: dernier live annoncé) ---
    async def lire_etat(self, cle: str):
        async with self.conn.execute("SELECT valeur FROM etat WHERE cle = ?", (cle,)) as curseur:
            ligne = await curseur.fetchone()
        return ligne[0] if ligne else None

    async def ecrire_etat(self, cle: str, valeur: str):
        await self.conn.execute(
            "INSERT INTO etat (cle, valeur) VALUES (?, ?) "
            "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
            (cle, valeur),
        )
        await self.conn.commit()

    # --- invitation utilisée par chaque membre (pour le log de départ) ---
    async def sauvegarder_arrivee(self, user_id: int, code: str, inviter_id):
        await self.conn.execute(
            "INSERT INTO arrivees (user_id, code, inviter_id) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET code = excluded.code, inviter_id = excluded.inviter_id",
            (user_id, code, inviter_id),
        )
        await self.conn.commit()

    async def lire_arrivee(self, user_id: int):
        async with self.conn.execute(
            "SELECT code, inviter_id FROM arrivees WHERE user_id = ?", (user_id,)
        ) as curseur:
            ligne = await curseur.fetchone()
        return (ligne[0], ligne[1]) if ligne else None

    async def supprimer_arrivee(self, user_id: int):
        await self.conn.execute("DELETE FROM arrivees WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    # --- avertissements ---
    async def ajouter_avertissement(self, user_id: int, moderateur_id: int, raison: str) -> int:
        curseur = await self.conn.execute(
            "INSERT INTO avertissements (user_id, moderateur_id, raison, date) VALUES (?, ?, ?, ?)",
            (user_id, moderateur_id, raison, int(time.time())),
        )
        await self.conn.commit()
        return curseur.lastrowid

    async def lister_avertissements(self, user_id: int) -> list[dict]:
        async with self.conn.execute(
            "SELECT id, moderateur_id, raison, date FROM avertissements WHERE user_id = ? ORDER BY id",
            (user_id,),
        ) as curseur:
            lignes = await curseur.fetchall()
        return [{"id": l[0], "moderateur_id": l[1], "raison": l[2], "date": l[3]} for l in lignes]

    async def supprimer_avertissements(self, user_id: int):
        await self.conn.execute("DELETE FROM avertissements WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    # --- bannissements (une ligne par personne, la plus récente remplace l'ancienne) ---
    async def sauvegarder_ban(self, user_id, nom, type_, moderateur_id, raison, avertissements: list[dict]):
        resume = json.dumps(
            [[a["raison"], a["date"], a["moderateur_id"]] for a in avertissements], ensure_ascii=False
        )
        await self.conn.execute(
            "INSERT INTO bannissements (user_id, nom, type, moderateur_id, raison, avertissements, date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET nom = excluded.nom, type = excluded.type, "
            "moderateur_id = excluded.moderateur_id, raison = excluded.raison, "
            "avertissements = excluded.avertissements, date = excluded.date",
            (user_id, nom, type_, moderateur_id, raison, resume, int(time.time())),
        )
        await self.conn.commit()

    async def lire_ban(self, user_id: int):
        async with self.conn.execute(
            "SELECT nom, type, moderateur_id, raison, avertissements, date "
            "FROM bannissements WHERE user_id = ?",
            (user_id,),
        ) as curseur:
            ligne = await curseur.fetchone()
        if ligne is None:
            return None
        return {
            "nom": ligne[0],
            "type": ligne[1],
            "moderateur_id": ligne[2],
            "raison": ligne[3],
            "avertissements": [
                {"raison": r, "date": d, "moderateur_id": m} for r, d, m in json.loads(ligne[4] or "[]")
            ],
            "date": ligne[5],
        }

    async def chercher_bans(self, texte: str) -> list[tuple]:
        """Pour l'autocomplétion de /baninfo : (user_id, nom) des bans les plus récents."""
        motif = f"%{texte}%"
        async with self.conn.execute(
            "SELECT user_id, nom FROM bannissements "
            "WHERE nom LIKE ? OR CAST(user_id AS TEXT) LIKE ? ORDER BY date DESC LIMIT 25",
            (motif, motif),
        ) as curseur:
            return await curseur.fetchall()