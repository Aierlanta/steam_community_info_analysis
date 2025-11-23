from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from pg_storage import PgPlaytimeSnapshot, PgPlaytimeStorage


app = FastAPI(title="Steam Playtime Sessions API")

# 提供静态前端页面，路径为 /web/index.html
app.mount("/web", StaticFiles(directory="web"), name="web")


def _infer_sessions_from_snapshots(
    snapshots: List[PgPlaytimeSnapshot],
) -> List[dict]:
    sessions: List[dict] = []
    if not snapshots:
        return sessions

    by_app: dict[int, List[PgPlaytimeSnapshot]] = {}
    for snap in snapshots:
        by_app.setdefault(snap.appid, []).append(snap)

    for appid, app_snaps in by_app.items():
        if len(app_snaps) < 2:
            continue
        prev = app_snaps[0]
        for current in app_snaps[1:]:
            if current.playtime_forever > prev.playtime_forever:
                delta = current.playtime_forever - prev.playtime_forever
                game_name = current.game_name or prev.game_name or f"appid {appid}"
                sessions.append(
                    {
                        "steamid": current.steamid,
                        "appid": appid,
                        "game_name": game_name,
                        "window_start_utc": prev.captured_at_utc.isoformat(),
                        "window_end_utc": current.captured_at_utc.isoformat(),
                        "minutes_delta": delta,
                    }
                )
            prev = current
    sessions.sort(key=lambda s: (s["steamid"], s["appid"], s["window_start_utc"]))
    return sessions


@app.get("/api/sessions")
def get_sessions(
    steamid: str = Query(..., description="要查询的 64 位 steamid"),
    limit: Optional[int] = Query(
        2000, description="最多返回的 session 数量（按时间排序后截断）"
    ),
) -> List[dict]:
    try:
        storage = PgPlaytimeStorage()
    except Exception as exc:  # pragma: no cover - 运行环境错误
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {exc}") from exc

    try:
        snapshots = storage.fetch_snapshots_ordered(steamid=steamid)
        sessions = _infer_sessions_from_snapshots(snapshots)
    finally:
        storage.close()

    if limit is not None and limit > 0 and len(sessions) > limit:
        sessions = sessions[-limit:]
    return sessions


@app.get("/api/users")
def get_users() -> List[dict]:
    try:
        storage = PgPlaytimeStorage()
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {exc}") from exc
    try:
        steamids = storage.list_distinct_steamids()
    finally:
        storage.close()
    return [{"steamid": s} for s in steamids]


@app.get("/")
def root_redirect():
    return RedirectResponse(url="/web/index.html", status_code=302)
