from __future__ import annotations

import signal
import time
from contextlib import contextmanager
from typing import Dict, Optional

from config_loader import AppConfig, load_config
from steam_api import SteamApiClient
from storage import PlaytimeStorage


@contextmanager
def _steam_client(api_key: str) -> SteamApiClient:
    client = SteamApiClient(api_key=api_key)
    try:
        yield client
    finally:
        client.close()


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


def run_collector(config_path: Optional[str] = None) -> None:
    if config_path is None:
        cfg = load_config()
    else:
        from pathlib import Path

        cfg = load_config(Path(config_path))

    storage = PlaytimeStorage(cfg.storage.database_path)

    stop_flag = {"stop": False}

    def _handle_signal(signum, frame):  # type: ignore[no-untyped-def]
        stop_flag["stop"] = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    with _steam_client(cfg.steam.api_key) as client:
        steamids = _ensure_steamids(cfg, client)
        interval = cfg.polling.interval_seconds

        while not stop_flag["stop"]:
            for steamid in steamids.values():
                games = client.get_owned_games(steamid)
                storage.insert_snapshot_batch(steamid=steamid, games=games)
            time.sleep(interval)

    storage.close()

