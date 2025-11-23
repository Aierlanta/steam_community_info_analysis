from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

import psycopg
from pathlib import Path

from steam_api import OwnedGame


def _get_pg_dsn() -> str:
    dsn = os.getenv("DATABASE_URL") or os.getenv("PG_CONN_STR") or ""
    if not dsn:
        # 尝试从项目根目录的 .env 读取（简单解析，不依赖额外包）
        env_path = Path(__file__).resolve().parent / ".env"
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                if line.startswith("DATABASE_URL="):
                    dsn = line[len("DATABASE_URL=") :].strip().strip('"')
                    break
    if not dsn:
        raise ValueError("未找到数据库连接字符串，请设置环境变量 DATABASE_URL 或 PG_CONN_STR，或在项目根目录提供 .env。")
    return dsn


@dataclass
class PgPlaytimeSnapshot:
    captured_at_utc: datetime
    steamid: str
    appid: int
    game_name: Optional[str]
    playtime_forever: int


class PgPlaytimeStorage:
    def __init__(self, dsn: Optional[str] = None) -> None:
        self._dsn = dsn or _get_pg_dsn()
        self._conn = psycopg.connect(self._dsn, autocommit=True)
        self.ensure_schema()

    def ensure_schema(self) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS playtime_snapshots (
                    id               SERIAL PRIMARY KEY,
                    captured_at_utc  TIMESTAMPTZ NOT NULL,
                    steamid          TEXT        NOT NULL,
                    appid            INTEGER     NOT NULL,
                    game_name        TEXT,
                    playtime_forever INTEGER     NOT NULL
                );
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_snapshots_steamid_appid_time
                ON playtime_snapshots (steamid, appid, captured_at_utc);
                """
            )

    def insert_snapshot_batch(
        self,
        steamid: str,
        games: Iterable[OwnedGame],
        captured_at: Optional[datetime] = None,
    ) -> None:
        if captured_at is None:
            captured_at = datetime.now(timezone.utc)
        rows = [
            (
                captured_at,
                steamid,
                game.appid,
                game.name,
                game.playtime_forever,
            )
            for game in games
        ]
        if not rows:
            return
        with self._conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO playtime_snapshots (
                    captured_at_utc, steamid, appid, game_name, playtime_forever
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                rows,
            )

    def fetch_snapshots_ordered(
        self,
        steamid: str,
    ) -> List[PgPlaytimeSnapshot]:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT captured_at_utc, steamid, appid, game_name, playtime_forever
                FROM playtime_snapshots
                WHERE steamid = %s
                ORDER BY appid, captured_at_utc;
                """,
                (steamid,),
            )
            rows = cur.fetchall()
        snapshots: List[PgPlaytimeSnapshot] = []
        for captured_at_utc, s_id, app_id, game_name, playtime in rows:
            snapshots.append(
                PgPlaytimeSnapshot(
                    captured_at_utc=captured_at_utc,
                    steamid=str(s_id),
                    appid=int(app_id),
                    game_name=str(game_name) if game_name is not None else None,
                    playtime_forever=int(playtime),
                )
            )
        return snapshots

    def list_distinct_steamids(self) -> List[str]:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT steamid
                FROM playtime_snapshots
                ORDER BY steamid;
                """
            )
            rows = cur.fetchall()
        return [str(row[0]) for row in rows]

    def close(self) -> None:
        self._conn.close()
