from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

from steam_api import OwnedGame


@dataclass
class PlaytimeSnapshot:
    captured_at_utc: datetime
    steamid: str
    appid: int
    game_name: Optional[str]
    playtime_forever: int


class PlaytimeStorage:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS playtime_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                captured_at_utc TEXT NOT NULL,
                steamid TEXT NOT NULL,
                appid INTEGER NOT NULL,
                game_name TEXT,
                playtime_forever INTEGER NOT NULL
            );
            """
        )
        self._conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_snapshots_steamid_appid_time
            ON playtime_snapshots (steamid, appid, captured_at_utc);
            """
        )
        self._conn.commit()

    def insert_snapshot_batch(
        self,
        steamid: str,
        games: Iterable[OwnedGame],
        captured_at: Optional[datetime] = None,
    ) -> None:
        if captured_at is None:
            captured_at = datetime.now(timezone.utc)
        captured_at_str = captured_at.isoformat()
        rows = [
            (
                captured_at_str,
                steamid,
                game.appid,
                game.name,
                game.playtime_forever,
            )
            for game in games
        ]
        if not rows:
            return
        self._conn.executemany(
            """
            INSERT INTO playtime_snapshots (
                captured_at_utc, steamid, appid, game_name, playtime_forever
            )
            VALUES (?, ?, ?, ?, ?);
            """,
            rows,
        )
        self._conn.commit()

    def fetch_snapshots_ordered(
        self,
        steamid: str,
        appid: Optional[int] = None,
    ) -> List[PlaytimeSnapshot]:
        if appid is None:
            cursor = self._conn.execute(
                """
                SELECT captured_at_utc, steamid, appid, game_name, playtime_forever
                FROM playtime_snapshots
                WHERE steamid = ?
                ORDER BY captured_at_utc ASC;
                """,
                (steamid,),
            )
        else:
            cursor = self._conn.execute(
                """
                SELECT captured_at_utc, steamid, appid, game_name, playtime_forever
                FROM playtime_snapshots
                WHERE steamid = ? AND appid = ?
                ORDER BY captured_at_utc ASC;
                """,
                (steamid, appid),
            )
        rows = cursor.fetchall()
        snapshots: List[PlaytimeSnapshot] = []
        for captured_at_utc, s_id, app_id, game_name, playtime in rows:
            dt = datetime.fromisoformat(captured_at_utc)
            snapshots.append(
                PlaytimeSnapshot(
                    captured_at_utc=dt,
                    steamid=str(s_id),
                    appid=int(app_id),
                    game_name=str(game_name) if game_name is not None else None,
                    playtime_forever=int(playtime),
                )
            )
        return snapshots

    def close(self) -> None:
        self._conn.close()

