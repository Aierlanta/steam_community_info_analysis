# Steam 游戏时长采集器（后端）

## 功能说明

定时采集指定 Steam 玩家的游戏拥有列表和游玩时间，存储快照到 PostgreSQL 数据库。

## 配置步骤

1. 复制 `.env.example` 为 `.env` 并填写实际配置：
   ```bash
   cp .env.example .env
   ```

2. 编辑 `.env` 文件：
   - `STEAM_API_KEY`: 在 [Steam 开发者页面](https://steamcommunity.com/dev/apikey) 申请
   - `DATABASE_URL`: PostgreSQL 连接字符串

3. 确保根目录的 `config.toml` 已配置玩家信息

## 安装依赖

```bash
uv pip install -r requirements.txt
```

## 运行采集器

```bash
uv run python collector.py
```

## Replit 部署

1. 在 Replit 创建 Python 项目
2. 上传代码到项目
3. 在 Secrets 中配置环境变量
4. 在 Replit Scheduler 中设置定时任务：
   - 命令: `python backend/collector.py`
   - 间隔: 每 10 分钟

## 数据存储

每次采集成功后，会在 `game_snapshots` 表中插入一条记录，包含：
- 玩家 ID
- 快照时间
- 完整的游戏列表和时长数据（JSON 格式）

