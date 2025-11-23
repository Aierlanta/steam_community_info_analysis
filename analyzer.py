from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

from storage import PlaytimeSnapshot, PlaytimeStorage


@dataclass
class PlaySession:
    steamid: str
    appid: int
    game_name: str
    window_start_utc: datetime
    window_end_utc: datetime
    minutes_delta: int


def infer_sessions_for_steamid(
    storage: PlaytimeStorage,
    steamid: str,
) -> List[PlaySession]:
    snapshots = storage.fetch_snapshots_ordered(steamid=steamid)
    by_app: Dict[int, List[PlaytimeSnapshot]] = {}
    for snap in snapshots:
        by_app.setdefault(snap.appid, []).append(snap)

    sessions: List[PlaySession] = []
    for appid, app_snaps in by_app.items():
        if len(app_snaps) < 2:
            continue
        prev = app_snaps[0]
        for current in app_snaps[1:]:
            if current.playtime_forever > prev.playtime_forever:
                delta = current.playtime_forever - prev.playtime_forever
                game_name = current.game_name or prev.game_name or ""
                if not game_name:
                    game_name = f"appid {appid}"
                sessions.append(
                    PlaySession(
                        steamid=steamid,
                        appid=appid,
                        game_name=game_name,
                        window_start_utc=prev.captured_at_utc,
                        window_end_utc=current.captured_at_utc,
                        minutes_delta=delta,
                    )
                )
            prev = current
    return sessions


def infer_sessions_for_all(
    storage: PlaytimeStorage,
    steamids: List[str],
) -> List[PlaySession]:
    all_sessions: List[PlaySession] = []
    for steamid in steamids:
        sessions = infer_sessions_for_steamid(storage, steamid)
        all_sessions.extend(sessions)
    return all_sessions

