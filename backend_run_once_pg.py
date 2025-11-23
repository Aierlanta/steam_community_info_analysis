from __future__ import annotations

from pathlib import Path
from typing import Dict

from config_loader import AppConfig, load_config
from pg_storage import PgPlaytimeStorage
from steam_api import SteamApiClient


def _ensure_steamids(cfg: AppConfig, client: SteamApiClient) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for player in cfg.steam.players:
        if player.steamid:
            result[player.steamid] = player.steamid
            continue
        if player.vanity_url:
            steamid = client.resolve_vanity_url(player.vanity_url)
            if steamid is None:
                raise RuntimeError(f"无法通过 vanity_url={player.vanity_url} 解析 steamid")
            result[steamid] = steamid
    if not result:
        raise RuntimeError("未解析到任何 steamid。")
    return result


def main() -> None:
    cfg = load_config()
    storage = PgPlaytimeStorage()
    client = SteamApiClient(api_key=cfg.steam.api_key)
    try:
        steamids = _ensure_steamids(cfg, client)
        for steamid in steamids.values():
            games = client.get_owned_games(steamid)
            storage.insert_snapshot_batch(steamid=steamid, games=games)
    finally:
        client.close()
        storage.close()


if __name__ == "__main__":
    main()

