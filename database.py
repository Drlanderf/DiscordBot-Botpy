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