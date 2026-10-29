import re

import aiohttp

BASE = "https://www.googleapis.com/youtube/v3"


def duree_en_secondes(iso: str) -> int:
    """Convertit une durée YouTube au format ISO 8601 ("PT1M30S") en secondes (90)."""
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", iso or "")
    if not m:
        return 0
    jours, heures, minutes, secondes = (int(x or 0) for x in m.groups())
    return jours * 86400 + heures * 3600 + minutes * 60 + secondes


def reglage(chaine: dict, cfg: dict, cle: str, defaut):
    """Un réglage de la chaîne l'emporte sur le réglage commun, qui l'emporte sur la valeur par défaut."""
    return chaine.get(cle, cfg.get(cle, defaut))


class YouTubeAPI:
    """Petit client pour l'API YouTube Data v3 (clé d'API, lecture seule)."""

    def __init__(self, cle_api: str):
        self.cle_api = cle_api
        self.session = None

    async def ouvrir(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))

    async def fermer(self):
        if self.session:
            await self.session.close()

    async def _get(self, chemin: str, params: dict) -> dict:
        async with self.session.get(
            f"{BASE}/{chemin}", params={**params, "key": self.cle_api}
        ) as reponse:
            donnees = await reponse.json()
            if reponse.status != 200:
                message = donnees.get("error", {}).get("message", "erreur inconnue")
                raise RuntimeError(f"YouTube {reponse.status} : {message}")
            return donnees

    async def derniers_uploads(self, channel_id: str, nombre: int = 5) -> list[str]:
        """Identifiants des dernières vidéos, de la plus récente à la plus ancienne."""
        playlist = "UU" + channel_id[2:]  # playlist des mises en ligne : UC... devient UU...
        donnees = await self._get(
            "playlistItems",
            {"part": "contentDetails", "playlistId": playlist, "maxResults": nombre},
        )
        return [item["contentDetails"]["videoId"] for item in donnees.get("items", [])]

    async def videos(self, ids: list[str]) -> list[dict]:
        """Détails des vidéos (titre, miniatures, durée, statut live...). 1 seul appel pour la liste."""
        if not ids:
            return []
        donnees = await self._get(
            "videos",
            {"part": "snippet,liveStreamingDetails,contentDetails", "id": ",".join(ids)},
        )
        return donnees.get("items", [])

    async def avatar_chaine(self, channel_id: str):
        donnees = await self._get("channels", {"part": "snippet", "id": channel_id})
        items = donnees.get("items", [])
        if not items:
            return None
        miniatures = items[0]["snippet"]["thumbnails"]
        return (miniatures.get("high") or miniatures.get("default"))["url"]

    async def miniature_verticale(self, video_id: str):
        """Vignette verticale 9:16 d'un Short, ou None si elle n'existe pas (adresse non documentée)."""
        url = f"https://i.ytimg.com/vi/{video_id}/oardefault.jpg"
        try:
            async with self.session.head(url) as reponse:
                return url if reponse.status == 200 else None
        except Exception:
            return None