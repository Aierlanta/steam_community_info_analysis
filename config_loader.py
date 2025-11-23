from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import tomllib


@dataclass
class SteamPlayerConfig:
    steamid: Optional[str]
    vanity_url: Optional[str]


@dataclass
class SteamConfig:
    api_key: str
    players: List[SteamPlayerConfig]


@dataclass
class PollingConfig:
    interval_seconds: int


@dataclass
class StorageConfig:
    database_path: Path


@dataclass
class AppConfig:
    steam: SteamConfig
    polling: PollingConfig
    storage: StorageConfig


def load_config(config_path: Path | None = None) -> AppConfig:
    base_dir = Path(__file__).resolve().parent
    if config_path is None:
        config_path = base_dir / "config.toml"

    if not config_path.is_file():
        raise FileNotFoundError(f"未找到配置文件: {config_path}")

    with config_path.open("rb") as f:
        raw = tomllib.load(f)

    steam_section = raw.get("steam", {})
    polling_section = raw.get("polling", {})
    storage_section = raw.get("storage", {})

    api_key_env_var = steam_section.get("api_key_env_var", "STEAM_WEB_API_KEY")
    api_key_from_env = os.getenv(api_key_env_var, "").strip()
    api_key_from_file = str(steam_section.get("api_key", "")).strip()

    api_key = api_key_from_env or api_key_from_file
    if not api_key:
        raise ValueError(
            f"未配置 Steam Web API Key，请在环境变量 {api_key_env_var} 或 config.toml 中填写。"
        )

    players_raw = steam_section.get("players", [])
    players: List[SteamPlayerConfig] = []
    for item in players_raw:
        steamid = str(item.get("steamid", "")).strip() or None
        vanity_url = str(item.get("vanity_url", "")).strip() or None
        if not steamid and not vanity_url:
            continue
        players.append(SteamPlayerConfig(steamid=steamid, vanity_url=vanity_url))

    if not players:
        raise ValueError("steam.players 列表为空，至少配置一个目标用户。")

    interval_seconds = int(polling_section.get("interval_seconds", 60))
    if interval_seconds <= 0:
        raise ValueError("polling.interval_seconds 必须为正整数。")

    database_path_raw = str(storage_section.get("database_path", "data/playtime_log.sqlite"))
    database_path = (base_dir / database_path_raw).resolve()

    return AppConfig(
        steam=SteamConfig(api_key=api_key, players=players),
        polling=PollingConfig(interval_seconds=interval_seconds),
        storage=StorageConfig(database_path=database_path),
    )

