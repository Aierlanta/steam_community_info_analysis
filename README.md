# steam_community_info_analysis

基于 Steam Web API 的“隐身模式”游玩时间推断工具：
后端定时轮询 `IPlayerService/GetOwnedGames`，记录总时长快照；前端按相邻快照的时长增量推断可能的游玩区间并可视化。

## 功能概览
- 仅使用官方 Web API（需要目标用户的“游戏详情”公开）
- 后端（Replit bot/定时任务）：每次运行拉一次 `GetOwnedGames`，写入 Postgres
- 前端（Replit autoscale）：提供 API `/api/users`、`/api/sessions?steamid=...`，并附带 React 可视化页面
- 推断逻辑：当某游戏 `playtime_forever` 在相邻快照间增加，就在两次快照时间窗内生成一个“可能的游玩 session”，时长为增量分钟数

## 目录结构
- `backend_run_once_pg.py`：后端一次性采集脚本（面向 Replit bot/定时任务）
- `steam_api.py`：封装 `ResolveVanityURL` / `GetOwnedGames`
- `pg_storage.py`：Postgres 存储，自动建表 `playtime_snapshots`，支持从环境变量或 `.env` 读取 `DATABASE_URL`
- `frontend_api.py`：FastAPI 服务，API：`/api/users`、`/api/sessions`，并挂载静态前端 `/web`
- `web/index.html`：React + Tailwind（CDN + Babel）可视化页面
- `config_loader.py`：从 `config.toml` 读取 Steam API Key、玩家列表等（本地或后端采集时用）
- `b_replit/.replit`、`f_replit/.replit`：后端/前端在 Replit 部署的模板 Run 配置

## 后端采集（本地或 Replit bot/定时任务）
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
4) 运行一次采集：
   ```bash
   uv run python backend_run_once_pg.py
   ```
   - 每跑一次会插入一批当前快照，建议按分钟级间隔定期运行（Replit bot/cron）

表结构（自动创建）：
```sql
CREATE TABLE IF NOT EXISTS playtime_snapshots (
  id               SERIAL PRIMARY KEY,
  captured_at_utc  TIMESTAMPTZ NOT NULL,
  steamid          TEXT        NOT NULL,
  appid            INTEGER     NOT NULL,
  game_name        TEXT,
  playtime_forever INTEGER     NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_steamid_appid_time
  ON playtime_snapshots (steamid, appid, captured_at_utc);
```

## 前端服务（本地或 Replit autoscale）
1) 启动：
   ```bash
   uv run uvicorn frontend_api:app --host 0.0.0.0 --port 8000
   ```
2) API：
   - `GET /api/users` -> 返回已采集到的 steamid 列表（去重）
   - `GET /api/sessions?steamid=...` -> 返回该玩家的推断 session 列表
3) 可视化页面：
   - 访问 `http://127.0.0.1:8000/web/index.html`
   - 顶部导航 + Hero + 玩家标签；每个玩家包含：按游戏聚合条形图、按日期柱状图、最近 session 列表、磁吸按钮等

## 推断逻辑说明
- 必须有至少两次快照，且某游戏的 `playtime_forever` 出现正向增量
- session 的时间窗口 = 上一次快照时间 ~ 本次快照时间
- session 的时长 = `playtime_forever` 增量（分钟）
- 精度取决于：采集间隔 + Steam 本身更新延迟；隐身场景下无法实时在线，只能用总时长跳变做“模糊区间”

## Replit 部署提示
- 后端（bot/定时任务）：用 `b_replit/.replit`，命令 `python backend_run_once_pg.py`；设置 Secrets：`STEAM_WEB_API_KEY`、`DATABASE_URL`
- 前端（autoscale）：用 `f_replit/.replit`，命令 `python -m uvicorn frontend_api:app --host 0.0.0.0 --port 8000`；Secrets：`DATABASE_URL`

## 常见问题
- 前端显示“暂无玩家”：检查 DB 连接是否正确，或后端是否已跑出快照。
- 前端显示玩家但 session 为 0：需要多跑几次后端，且目标用户在此期间时长有增长；没有增量就不会生成 session。
- 本地启动时 404 favicon / sw.js：可以忽略，不影响功能。*** End Patch*** Phony Patch Reformatted Plan to Markdown
