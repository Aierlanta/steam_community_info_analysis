# Steam 游戏时长追踪系统

基于 Steam Web API 的"隐身模式"游玩时间推断工具。通过定期轮询玩家游戏数据并对比快照差异，推断玩家的实际游玩时间和习惯。

## 🎯 功能特性

- **自动数据采集**：后端定时调用 Steam API，获取玩家游戏列表和时长
- **智能去重存储**：只在数据发生变化时保存快照，节省存储空间
- **时间推断算法**：基于相邻快照的时长差异，推断游玩时间区间
- **可视化分析**：使用 Plotly 生成交互式图表，直观展示游玩数据
- **多玩家支持**：可同时追踪多个 Steam 用户的游戏时长

## 📁 项目结构

```
steam_community_info_analysis/
├── backend/                    # 后端数据采集
│   ├── collector.py           # 主采集脚本
│   ├── requirements.txt       # Python 依赖
│   ├── pyproject.toml         # uv 项目配置
│   ├── .env.example           # 环境变量示例
│   ├── .replit                # Replit 配置
│   └── README.md              # 后端说明文档
├── frontend/                   # 前端可视化
│   ├── app.py                 # FastAPI 应用
│   ├── requirements.txt       # Python 依赖
│   ├── pyproject.toml         # uv 项目配置
│   ├── .env.example           # 环境变量示例
│   ├── .replit                # Replit 配置
│   └── templates/             # HTML 模板目录
├── config.toml                # 全局配置文件
└── init_db.sql                # 数据库初始化脚本
```

## 🚀 快速开始

### 1. 环境准备

#### 必需项

- Python 3.10+
- PostgreSQL 数据库
- Steam Web API Key（[申请地址](https://steamcommunity.com/dev/apikey)）

#### 推荐工具

- [uv](https://github.com/astral-sh/uv) - 快速的 Python 包管理器

### 2. 数据库初始化

```bash
# 连接到 PostgreSQL 数据库
psql -U your_username -d your_database

# 执行初始化脚本
\i init_db.sql
```

或使用命令行：

```bash
psql -U your_username -d your_database -f init_db.sql
```

### 3. 配置文件设置

#### 修改 `config.toml`

```toml
[steam]
api_key = "your_steam_api_key_here"

[[steam.players]]
steamid = "xxxxxxxx"
vanity_url = "your_steam_username"

[polling]
interval_seconds = 600  # 轮询间隔（秒）
```

#### 配置后端环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env 文件，填写实际配置
```

`.env` 内容：

```env
STEAM_API_KEY=your_steam_api_key_here
DATABASE_URL=postgresql://user:password@host:port/database
```

#### 配置前端环境变量

```bash
cd frontend
cp .env.example .env
# 编辑 .env 文件，填写数据库连接
```

### 4. 本地运行

#### 后端（数据采集器）

```bash
cd backend

# 使用 uv 安装依赖
uv sync

# 运行采集器（单次）
uv run python collector.py
```

#### 前端（可视化服务）

```bash
cd frontend

# 使用 uv 安装依赖
uv pip install -r requirements.txt

# 启动 Web 服务
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

访问 <http://localhost:8000> 查看可视化界面。

## ☁️ Replit 部署

### 部署后端（数据采集器）

1. 在 Replit 创建新 Python 项目 `steam-collector`
2. 上传 `backend/` 目录下的所有文件
3. 上传根目录的 `config.toml` 文件
4. 在 Replit **Secrets** 中配置环境变量：
   - `STEAM_API_KEY`: 你的 Steam API 密钥
   - `DATABASE_URL`: PostgreSQL 连接字符串
5. 在 **Replit Scheduler** 中添加定时任务：
   - 命令: `python collector.py`
   - Cron 表达式: `*/10 * * * *` （每 10 分钟运行）

### 部署前端（可视化服务）

1. 在 Replit 创建新 Python 项目 `steam-dashboard`
2. 上传 `frontend/` 目录下的所有文件
3. 在 Replit **Secrets** 中配置：
   - `DATABASE_URL`: PostgreSQL 连接字符串（与后端相同）
4. 点击 **Run** 按钮启动服务
5. 启用 **Always On** 保持服务运行

部署完成后，Replit 会提供一个公开访问的 URL。

## 📊 功能说明

### 后端采集器

- **Steam API 调用**：使用 `IPlayerService/GetOwnedGames` 接口获取玩家游戏数据
- **数据去重**：比较游戏 ID 列表和 `playtime_forever` 字段，只有变化时才保存
- **多玩家支持**：从 `config.toml` 读取玩家列表，依次采集数据
- **错误处理**：网络异常、API 限流等情况的容错处理

### 前端可视化

#### 主要路由

- `/` - 玩家列表首页
- `/player/{player_id}` - 玩家详细分析页面（默认显示最近 7 天）
- `/player/{player_id}?days=14` - 自定义天数（1-30 天）

#### API 端点

- `GET /api/players` - 获取所有玩家列表
- `GET /api/snapshots/{player_id}?days=7` - 获取原始快照数据
- `GET /api/analysis/{player_id}?days=7` - 获取分析后的数据（JSON）

#### 可视化图表

1. **游戏时长推断时间轴（甘特图）**
   - 横轴：日期时间
   - 纵轴：游戏名称
   - 色块：推断的游玩时间区间

2. **游戏时长分布（饼图）**
   - 显示各游戏时长占比
   - Top 10 游戏 + 其他

3. **游戏时长排名（柱状图）**
   - 按时长降序排列
   - 显示 Top 15 游戏

4. **游玩活跃度分析（柱状图）**
   - 按 24 小时统计游玩活跃度
   - 帮助了解游玩习惯

## 🔧 技术栈

### 后端

- **Python 3.10+**
- **requests** - HTTP 请求
- **psycopg2** - PostgreSQL 驱动
- **python-dotenv** - 环境变量管理
- **toml** - 配置文件解析

### 前端

- **FastAPI** - 现代 Web 框架
- **Uvicorn** - ASGI 服务器
- **Plotly** - 交互式可视化
- **Pandas** - 数据处理

### 数据库

- **PostgreSQL** - 关系型数据库
- **JSONB** - 存储游戏数据快照

## 📝 数据库结构

```sql
CREATE TABLE game_snapshots (
    id SERIAL PRIMARY KEY,
    player_id VARCHAR(20) NOT NULL,      -- Steam ID
    player_name VARCHAR(100),             -- 玩家名称
    snapshot_time TIMESTAMP NOT NULL,     -- 快照时间
    games_data JSONB NOT NULL,            -- 游戏数据（JSON）
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 快照数据格式

```json
{
  "game_count": 150,
  "games": [
    {
      "appid": 730,
      "name": "Counter-Strike 2",
      "playtime_forever": 12345,
      "playtime_2weeks": 240
    }
  ]
}
```

## 🎮 使用场景

1. **追踪游戏时长**：即使在 Steam 隐身模式下，也能推断实际游玩时间
2. **游玩习惯分析**：了解自己或朋友的游戏偏好和活跃时段
3. **游戏统计**：查看各游戏的总游玩时长和排名
4. **数据可视化**：直观的图表展示，便于分析和分享

## ⚠️ 注意事项

1. **API 限流**：Steam API 有调用频率限制，建议轮询间隔不少于 5 分钟
2. **隐私设置**：只能获取公开个人资料的玩家数据
3. **时间推断**：推断的游玩时间是基于快照差异的估算，可能与实际有偏差
4. **数据存储**：长期运行会积累大量快照数据，注意数据库容量

## 🔒 隐私声明

本工具仅使用 Steam 公开 API 获取公开数据，不涉及任何隐私信息的非法获取。请遵守 Steam 使用条款和相关法律法规。

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📮 联系方式

如有问题或建议，请通过 GitHub Issues 联系。

---

**Happy Gaming! 🎮**
