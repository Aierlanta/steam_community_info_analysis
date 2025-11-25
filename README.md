# Steam 游戏时长追踪分析工具

> 🔄 **V2.0 (爬虫版本)** - 通过爬取 Steam 个人主页获取实时游戏数据

基于网页爬虫的游玩时间推断工具。通过定期爬取玩家 Steam 个人主页的"最新动态"，获取最近玩过的游戏及时长变化，推断玩家的实际游玩时间和习惯。

## 📋 目录

- [预览](#预览)
- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [部署指南](#部署指南)
- [数据格式](#数据格式)
- [常见问题](#常见问题)

## 🎨 预览

<img width="2560" height="1306" alt="image" src="https://github.com/user-attachments/assets/e9b63ef7-0811-47cb-958a-7644e203b4b6" />

<img width="2560" height="1300" alt="image" src="https://github.com/user-attachments/assets/81cb278f-101e-4b25-aeda-598c2761ce8a" />

<img width="2560" height="1440" alt="image" src="https://github.com/user-attachments/assets/24334be3-daaa-4be5-9cc9-8b1a6d2de105" />

## 🎯 功能特性

### V2.0 新特性 ⭐

- **🕷️ 网页爬虫**: 爬取 Steam 个人主页"最新动态"，获取实时数据
- **🔐 Cookie 支持**: 支持 Steam Cookie 登录，访问"仅好友可见"的资料
- **⏰ 时区自动转换**: 后端统一 UTC 存储，前端自动转换为本地时区
- **🎯 精准追踪**: 获取最近3个游戏的实时时长变化

### 核心功能

- **自动数据采集**: 后端定时爬取 Steam 个人主页，获取游戏时长变化
- **智能去重存储**: 只在数据发生变化时保存快照，节省存储空间
- **时间推断算法**: 基于相邻快照的时长差异，推断游玩时间区间
- **可视化分析**: 使用 Plotly 生成交互式图表，直观展示游玩数据
  - 📊 时间轴甘特图（游玩时段）
  - 🥧 游戏时长饼图
  - 📈 游戏排行柱状图
  - 🔥 活跃时段热力图
- **多玩家支持**: 可同时追踪多个 Steam 用户的游戏时长

## 🏗️ 系统架构

```
┌─────────────────┐
│   Steam 社区    │
│   个人主页      │
└────────┬────────┘
         │ 爬取
         ▼
┌─────────────────┐      ┌──────────────┐
│  后端采集器      │─────▶│  PostgreSQL  │
│  (Python)       │ 存储 │   数据库     │
│  - 爬虫         │      └──────┬───────┘
│  - 去重         │             │ 查询
│  - 定时任务     │             │
└─────────────────┘             ▼
                        ┌──────────────┐
                        │  前端可视化  │
                        │  (FastAPI)   │
                        │  - 数据分析  │
                        │  - Plotly图表│
                        └──────────────┘
```

## 📁 项目结构

```
steam_community_info_analysis/
├── backend/                      # 后端数据采集
│   ├── collector.py             # 主采集脚本
│   ├── steam_scraper.py         # Steam 爬虫模块
│   ├── requirements.txt         # Python 依赖
│   ├── pyproject.toml           # uv 项目配置
│   ├── .replit                  # Replit 配置
│   └── .env.example             # 环境变量示例
├── frontend/                     # 前端可视化
│   ├── app.py                   # FastAPI 应用
│   ├── templates/               # HTML 模板目录
│   │   └── dashboard.html
│   ├── requirements.txt         # Python 依赖
│   ├── pyproject.toml           # uv 项目配置
│   ├── .replit                  # Replit 配置
│   └── .env.example             # 环境变量示例
├── config.toml                  # 全局配置文件（玩家列表）
├── init_db.sql                  # 数据库初始化脚本
├── init_database.py             # 数据库初始化工具
├── README.md                    # 项目说明（本文件）
├── README_SCRAPER.md            # 爬虫版本详细说明
├── COOKIE_GUIDE.md              # Cookie 获取和配置指南
└── REPLIT_DEPLOYMENT_GUIDE.md   # Replit 部署完整指南
```

## 🚀 快速开始

### 1. 环境准备

#### 必需项

- **Python 3.10+**
- **uv** (Python 包管理器)
- **PostgreSQL 数据库**

#### 安装 uv

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 克隆项目

```bash
git clone https://github.com/yourusername/steam_community_info_analysis.git
cd steam_community_info_analysis
```

### 3. 配置数据库

#### 3.1 创建数据库

使用 [Neon](https://neon.tech) 或其他 PostgreSQL 服务：

1. 创建新数据库
2. 复制连接字符串（格式：`postgresql://user:pass@host:port/db`）

#### 3.2 初始化表结构

**方式 1：使用 psql 命令行**

```bash
psql "你的数据库连接字符串" -f init_db.sql
```

**方式 2：使用 Python 脚本**

```bash
# 先配置 .env 文件中的 DATABASE_URL
python init_database.py
```

### 4. 配置玩家列表

编辑 `config.toml`，添加要追踪的玩家：

```toml
[[steam.players]]
steamid = "1234567890"
vanity_url = "aaa"  # 可选，个性化URL

[[steam.players]]
steamid = "2345678901"
# 如果没有个性化URL，只填 steamid 即可
```

**如何获取 Steam ID？**

访问 [steamid.io](https://steamid.io)，输入个人主页链接，复制 **steamID64**。

### 5. 配置后端

```bash
cd backend
```

创建 `.env` 文件：

```env
# 数据库连接（必需）
DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require

# Steam Cookie（可选，用于访问好友资料）
# STEAM_COOKIES=sessionid=xxx; steamLoginSecure=xxx
```

**获取 Steam Cookie**: 参考 [`COOKIE_GUIDE.md`](COOKIE_GUIDE.md)

安装依赖：

```bash
uv sync
```

### 6. 配置前端

```bash
cd frontend
```

创建 `.env` 文件：

```env
# 数据库连接（与后端相同）
DATABASE_URL=postgresql://user:pass@host:port/db?sslmode=require
```

安装依赖：

```bash
uv sync
```

### 7. 运行测试

#### 测试后端采集

```bash
cd backend
uv run python collector.py
```

预期输出：

```
2025-11-24 15:00:00 - INFO - 数据库连接成功
2025-11-24 15:00:00 - INFO - 开始采集玩家数据: 1234567890
2025-11-24 15:00:03 - INFO - 成功爬取到 3 个最新游戏
2025-11-24 15:00:05 - INFO - 成功保存玩家快照（3 个游戏）
```

#### 启动前端服务

```bash
cd frontend
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

访问 <http://localhost:8000> 查看可视化界面。

## 📦 部署指南

### Replit 部署（推荐）

详细步骤请查看 [`REPLIT_DEPLOYMENT_GUIDE.md`](REPLIT_DEPLOYMENT_GUIDE.md)

#### 后端部署

1. 创建 Python Repl，命名为 `steam-collector`
2. 上传 `backend/` 文件夹内容
3. 配置 Secrets：`DATABASE_URL`、`STEAM_COOKIES`（可选）
4. 设置 Cron Job：`*/10 * * * *`（每10分钟执行）

#### 前端部署

1. 创建 Python Repl，命名为 `steam-dashboard`
2. 上传 `frontend/` 文件夹内容
3. 配置 Secret：`DATABASE_URL`
4. 部署为 Always On

### 其他云平台

- **Railway**: 支持 PostgreSQL 和定时任务
- **Fly.io**: 支持容器化部署
- **Render**: 支持 Cron Jobs
- **Vercel**: 前端可部署为 Serverless

## 📊 数据格式

### 数据库表结构

```sql
CREATE TABLE game_snapshots (
    id SERIAL PRIMARY KEY,
    player_id VARCHAR(20) NOT NULL,
    player_name VARCHAR(100),
    snapshot_time TIMESTAMPTZ NOT NULL,  -- UTC 时间
    games_data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 爬虫数据格式

```json
{
  "data_source": "web_scraper",
  "game_count": 3,
  "recent_games": [
    {
      "game_name": "Counter-Strike 2",
      "appid": 730,
      "playtime_total": 722.0,
      "last_played": "11月23日",
      "achievements": "1 / 1",
      "achievements_unlocked": 1,
      "achievements_total": 1
    }
  ]
}
```

### 时间处理

- **后端**: 使用 `datetime.now(timezone.utc)` 记录 UTC 时间
- **数据库**: 存储为 `TIMESTAMPTZ`（带时区时间戳）
- **API**: 返回 ISO 8601 格式（如 `2025-11-24T15:00:00+00:00`）
- **前端**: Plotly 自动转换为浏览器本地时区显示

## 🔧 使用说明

### 定时采集设置

#### 方式 1：使用 Cron（Linux/macOS）

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每10分钟）
*/10 * * * * cd /path/to/backend && uv run python collector.py
```

#### 方式 2：使用 Windows 任务计划程序

1. 打开"任务计划程序"
2. 创建基本任务
3. 触发器：每10分钟
4. 操作：启动程序 `python`，参数 `collector.py`，起始于 `backend/` 目录

#### 方式 3：使用 Python 循环脚本

创建 `backend/scheduler.py`：

```python
import time
import subprocess
from datetime import datetime

INTERVAL = 600  # 10 分钟

while True:
    print(f"[{datetime.now()}] 开始采集...")
    subprocess.run(['python', 'collector.py'])
    print(f"等待 {INTERVAL} 秒...")
    time.sleep(INTERVAL)
```

运行：

```bash
cd backend
python scheduler.py
```

### 查看分析结果

1. 访问前端 URL（如 <http://localhost:8000）>
2. 选择要查看的玩家
3. 查看以下图表：
   - **时间轴甘特图**: 推断的游玩时段
   - **游戏时长饼图**: 各游戏时长占比
   - **游戏排行榜**: 游玩时长排序
   - **活跃热力图**: 按小时统计活跃度

## ❓ 常见问题

### Q: 为什么时间轴上只有少数几个点？

**A**: 需要持续采集一段时间才能积累足够数据。建议：

- 设置每10分钟采集一次
- 至少运行几个小时
- 数据越多，推断越准确

### Q: 如何访问好友的私密资料？

**A**: 需要配置 Steam Cookie：

1. 参考 [`COOKIE_GUIDE.md`](COOKIE_GUIDE.md) 获取 Cookie
2. 在 `.env` 中配置 `STEAM_COOKIES`
3. 重启采集器

### Q: 数据存储多久？

**A**: 默认永久保存。建议定期清理：

```sql
-- 删除30天前的数据
DELETE FROM game_snapshots 
WHERE snapshot_time < NOW() - INTERVAL '30 days';
```

### Q: 能追踪所有游戏吗？

**A**: 爬虫版本只能获取"最新动态"中的3个游戏。如需追踪所有游戏，可以：

- 通过频繁采集（如每5分钟）捕获更多游戏
- 或使用旧版 Steam API（需要 API Key）

### Q: 为什么某个玩家无法采集？

**可能原因**：

1. 账号设为私密
2. 不是你的好友（且未配置 Cookie）
3. Steam ID 错误
4. 网络连接问题

**解决方案**：

1. 确认账号公开或配置 Cookie
2. 检查 Steam ID 是否正确（64位数字）
3. 查看采集器日志了解具体错误

### Q: 时区显示不正确？

**A**:

- 后端统一使用 UTC 时间存储
- 前端自动转换为浏览器本地时区
- 确认浏览器时区设置正确

### Q: 如何备份数据？

**备份数据库**：

```bash
# 导出数据
pg_dump "数据库连接字符串" > backup.sql

# 恢复数据
psql "数据库连接字符串" < backup.sql
```

## 📚 相关文档

- [爬虫版本详细说明](README_SCRAPER.md)
- [Cookie 获取指南](COOKIE_GUIDE.md)
- [Replit 部署指南](REPLIT_DEPLOYMENT_GUIDE.md)
- [Steam Web API 文档](https://steamcommunity.com/dev)

## 🛠️ 技术栈

### 后端

- **Python 3.10+**
- **requests** - HTTP 请求
- **BeautifulSoup4** - HTML 解析
- **psycopg2** - PostgreSQL 驱动
- **python-dotenv** - 环境变量管理

### 前端

- **FastAPI** - Web 框架
- **Uvicorn** - ASGI 服务器
- **Plotly** - 数据可视化
- **Pandas** - 数据处理
- **Jinja2** - 模板引擎

### 数据库

- **PostgreSQL 14+**
- **JSONB** - 灵活的 JSON 存储

## 🔄 版本历史

### V2.0 (2024-11-24) - 爬虫版本

- ✨ 使用网页爬虫替代 Steam Web API
- ✨ 支持 Steam Cookie 登录
- ✨ 统一 UTC 时区处理
- ✨ 前端自动时区转换
- 📝 完整的部署文档

### V1.0 (初始版本)

- 基于 Steam Web API
- 基础数据采集和可视化

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## ⚠️ 免责声明

本工具仅用于个人学习和数据分析。使用时请：

- 遵守 Steam 使用条款
- 尊重他人隐私
- 不要过于频繁请求（建议间隔 ≥5 分钟）

---

**作者**: Your Name  
**最后更新**: 2024-11-24
