from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from analyzer import PlaySession


def _session_to_serializable(session: PlaySession) -> dict:
    base = asdict(session)
    base["window_start_utc"] = session.window_start_utc.astimezone(timezone.utc).isoformat()
    base["window_end_utc"] = session.window_end_utc.astimezone(timezone.utc).isoformat()
    return base


def export_sessions_to_json(
    sessions: List[PlaySession],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    data = [_session_to_serializable(s) for s in sessions]
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

