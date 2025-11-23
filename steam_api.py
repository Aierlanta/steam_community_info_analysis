from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


STEAM_API_BASE = "https://api.steampowered.com"


@dataclass
class OwnedGame:
    appid: int
    name: Optional[str]
    playtime_forever: int


class SteamApiClient:
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client = httpx.Client(timeout=20.0)

    def resolve_vanity_url(self, vanity_url: str) -> Optional[str]:
        params = {
            "key": self._api_key,
            "vanityurl": vanity_url,
            "format": "json",
        }
        url = f"{STEAM_API_BASE}/ISteamUser/ResolveVanityURL/v1/"
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()
        response = data.get("response", {})
        if response.get("success") != 1:
            return None
        steamid = response.get("steamid")
        return str(steamid) if steamid is not None else None

    def get_owned_games(self, steamid: str) -> List[OwnedGame]:
        params = {
            "key": self._api_key,
            "steamid": steamid,
            "include_appinfo": 1,
            "include_played_free_games": 1,
            "format": "json",
        }
        url = f"{STEAM_API_BASE}/IPlayerService/GetOwnedGames/v1/"
        resp = self._client.get(url, params=params)
        resp.raise_for_status()
        data: Dict[str, Any] = resp.json()
        response = data.get("response", {})
        games_raw = response.get("games", []) or []
        games: List[OwnedGame] = []
        for g in games_raw:
            appid = g.get("appid")
            if appid is None:
                continue
            name = g.get("name")
            playtime_forever = int(g.get("playtime_forever", 0))
            games.append(
                OwnedGame(
                    appid=int(appid),
                    name=str(name) if isinstance(name, str) else None,
                    playtime_forever=playtime_forever,
                )
            )
        return games

    def close(self) -> None:
        self._client.close()

