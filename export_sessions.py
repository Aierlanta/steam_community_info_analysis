from __future__ import annotations

from pathlib import Path

from analyzer import infer_sessions_for_all
from config_loader import load_config
from storage import PlaytimeStorage
from web_export import export_sessions_to_json


def main() -> None:
    cfg = load_config()
    storage = PlaytimeStorage(cfg.storage.database_path)
    try:
        steamids = [p.steamid for p in cfg.steam.players if p.steamid]  # type: ignore[assignment]
        if not steamids:
            # 如果只有 vanity_url，也可以直接从数据库中拿到所有 steamid。
            from typing import List

            cursor = storage._conn.execute(  # type: ignore[attr-defined]
                "SELECT DISTINCT steamid FROM playtime_snapshots;"
            )
            rows = cursor.fetchall()
            steamids = [str(row[0]) for row in rows]

        sessions = infer_sessions_for_all(storage, steamids)
        output_path = Path(__file__).resolve().parent / "web" / "sessions.json"
        export_sessions_to_json(sessions, output_path)
    finally:
        storage.close()


if __name__ == "__main__":
    main()

