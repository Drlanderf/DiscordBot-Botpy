import time

import aiohttp


class TwitchAPI:
    """Petit client pour l'API Twitch (Helix) avec un jeton d'application."""

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = None
        self._token = None
        self._expire = 0.0

    async def ouvrir(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15))

    async def fermer(self):
        if self.session:
            await self.session.close()

    async def _jeton(self) -> str:
        # On réutilise le jeton tant qu'il est valide, sinon on en demande un nouveau
        if self._token and time.time() < self._expire - 60:
            return self._token

        async with self.session.post(
            "https://id.twitch.tv/oauth2/token",
            data={
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials",
            },
        ) as reponse:
            reponse.raise_for_status()
            donnees = await reponse.json()

        self._token = donnees["access_token"]
        self._expire = time.time() + donnees["expires_in"]
        return self._token

    async def _get(self, chemin: str, params: dict) -> dict:
        for essai in range(2):
            headers = {"Client-Id": self.client_id, "Authorization": f"Bearer {await self._jeton()}"}
            async with self.session.get(
                f"https://api.twitch.tv/helix/{chemin}", params=params, headers=headers
            ) as reponse:
                if reponse.status == 401 and essai == 0:  # jeton refusé : on en redemande un
                    self._token = None
                    continue
                reponse.raise_for_status()
                return await reponse.json()

    async def stream(self, login: str):
        """Renvoie les infos du live en cours, ou None si la chaîne est hors ligne."""
        donnees = await self._get("streams", {"user_login": login})
        return donnees["data"][0] if donnees["data"] else None

    async def utilisateur(self, login: str):
        """Renvoie le profil (avatar, nom affiché...) ou None."""
        donnees = await self._get("users", {"login": login})
        return donnees["data"][0] if donnees["data"] else None