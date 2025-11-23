# steam_community_info_analysis

基于 Steam Web API 的“隐身模式”游玩时间推断工具：
后端定时轮询 `IPlayerService/GetOwnedGames`，每次将完整快照（含全部游戏）作为一条 JSON 记录写入 Postgres；前端/分析按相邻快照的时长增量推断可能的游玩区间并可视化。

## 功能概览
- 仅使用官方 Web API（需要目标用户的“游戏详情”公开）
- 后端：每次运行拉一次 `GetOwnedGames`，将快照 JSON 写入 Postgres（表 `playtime_snapshots_json`），若内容未变则跳过写入
- 前端（FastAPI）：从数据库读取最近一周的快照 JSON，提供 API `/api/users`、`/api/sessions?steamid=...`，并附带 React 可视化页面
- 本地文件快照方案（`storage.py`）保留为备选，但默认使用 Postgres JSON
- 推断逻辑：当某游戏 `playtime_forever` 在相邻快照间增加，就在两次快照时间窗内生成一个“可能的游玩 session”，时长为增量分钟数

## 目录结构
- `backend_run_once_pg.py`：后端一次性采集脚本（面向 Replit bot/定时任务）
- `steam_api.py`：封装 `ResolveVanityURL` / `GetOwnedGames`
- `storage.py`：基于文件的 JSON 快照存储（可选备用）
- `pg_storage.py`：Postgres JSON 存储，每次一条 JSONB 快照记录，支持从环境变量或 `.env` 读取 `DATABASE_URL`
- `frontend_api.py`：FastAPI 服务，API：`/api/users`、`/api/sessions`，并挂载静态前端 `/web`
- `web/index.html`：React + Tailwind（CDN + Babel）可视化页面
- `config_loader.py`：从 `config.toml` 读取 Steam API Key、玩家列表等（本地或后端采集时用）
- `b_replit/.replit`、`f_replit/.replit`：后端/前端在 Replit 部署的模板 Run 配置

## 后端采集（Postgres JSON 快照，默认）
1) 配置 Steam Web API Key：
   - 推荐用环境变量 `STEAM_WEB_API_KEY`；或在 `config.toml` 的 `api_key` 字段填写（公开仓库勿提交）
2) 配置目标用户：
   - `config.toml` -> `[[steam.players]]`
   - 若有 64 位 steamid：`steamid = "..."`，`vanity_url` 为空
   - 若只有自定义 ID（例：morbisol）：`steamid = ""`，`vanity_url = "morbisol"`
3) 配置 Postgres 连接：
   - 环境变量 `DATABASE_URL` 或 `PG_CONN_STR`，或在项目根 `.env` 写：
     ```
     DATABASE_URL="postgresql://user:pass@host:port/db?sslmode=require"
     ```
4) 运行采集（循环模式，按 `polling.interval_seconds` 周期拉取并写入表 `playtime_snapshots_json`，若内容未变则跳过写入）：
   ```bash
   uv run python main.py
   ```
   - 可以用 Ctrl+C 退出；如需只跑一次，可调用 `collector.run_collector(config_path)` 自行控制。

表结构（自动创建）：
```json
{
  "captured_at_utc": "TIMESTAMPTZ",
  "steamid": "TEXT",
  "payload": {
    "captured_at_utc": "2024-01-01T12:00:00+00:00",
    "steamid": "7656...",
    "games": [
      {"appid": 570, "game_name": "Dota 2", "playtime_forever": 1234},
      {"appid": 730, "game_name": "Counter-Strike 2", "playtime_forever": 5678}
    ]
  }
}
```


## 前端服务（本地或 Replit autoscale）
1) 启动：
   ```bash
   uv run uvicorn frontend_api:app --host 0.0.0.0 --port 8000
   ```
2) API：
   - `GET /api/users` -> 返回数据库中已采集到的 steamid 列表（去重）
   - `GET /api/sessions?steamid=...` -> 返回该玩家最近一周的推断 session 列表（基于快照 JSON 增量）
3) 可视化页面：
   - 访问 `http://127.0.0.1:8000/web/index.html`
   - 顶部导航 + Hero + 玩家标签；每个玩家包含：按游戏聚合条形图、按日期柱状图、最近 session 列表、磁吸按钮等

## 推断逻辑说明
- 必须有至少两次快照，且某游戏的 `playtime_forever` 出现正向增量
- session 的时间窗口 = 上一次快照时间 ~ 本次快照时间
- session 的时长 = `playtime_forever` 增量（分钟）
- 精度取决于：采集间隔 + Steam 本身更新延迟；隐身场景下无法实时在线，只能用总时长跳变做“模糊区间”

## 文件快照方案（可选）
- 如果不想依赖数据库，可改用 `storage.py`（本地 JSON 目录），并将采集/前端切换回文件存储。当前默认未启用。

## Replit 部署提示
- 后端（bot/定时任务，Postgres JSON）：用 `b_replit/.replit`，命令 `python main.py`；Secrets：`STEAM_WEB_API_KEY`、`DATABASE_URL`
- 前端（autoscale）：用 `f_replit/.replit`，命令 `python -m uvicorn frontend_api:app --host 0.0.0.0 --port 8000`；Secrets：`DATABASE_URL`（以及 `STEAM_WEB_API_KEY` 供读取配置）

## 常见问题
- 前端显示“暂无玩家”：检查数据库连接和 `playtime_snapshots_json` 是否已有采集数据。
- 前端显示玩家但 session 为 0：需要多跑几次后端，且目标用户在此期间时长有增长；没有增量就不会生成 session。
- 本地启动时 404 favicon / sw.js：可以忽略，不影响功能。
