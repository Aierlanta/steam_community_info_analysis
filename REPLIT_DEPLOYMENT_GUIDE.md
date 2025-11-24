# Replit 部署指南

## 📦 项目结构

本项目分为两个独立的 Repl：

1. **后端 (Backend)** - 数据采集器（定时任务）
2. **前端 (Frontend)** - Web 可视化界面（Always On）

---

## 🔧 后端部署（数据采集器）

### 1. 创建 Repl

1. 登录 [Replit](https://replit.com)
2. 点击 **Create Repl**
3. 选择 **Python** 模板
4. 命名: `steam-collector`（或你喜欢的名字）
5. 点击 **Create Repl**

### 2. 上传代码

将 `backend/` 文件夹中的所有文件上传到 Repl：

```
steam-collector/
├── collector.py          # 主采集脚本
├── steam_scraper.py      # 爬虫模块
├── requirements.txt      # 依赖包
├── pyproject.toml        # 项目配置
└── .replit              # Replit 配置
```

### 3. 配置环境变量（Secrets）

点击左侧的 **🔒 Secrets**（锁图标），添加以下变量：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `DATABASE_URL` | `postgresql://user:pass@host:port/db` | PostgreSQL 数据库连接字符串 |
| `STEAM_COOKIES` | `sessionid=...; steamLoginSecure=...` | Steam Cookie（可选，访问好友资料） |

**DATABASE_URL 格式**：
```
postgresql://用户名:密码@主机:端口/数据库名?sslmode=require
```

**STEAM_COOKIES 获取方法**：
参考 `COOKIE_GUIDE.md`

### 4. 安装依赖

在 Shell 中运行：

```bash
pip install -r requirements.txt
```

### 5. 测试运行

点击绿色的 **▶ Run** 按钮，应该看到：

```
2025-11-24 15:00:00 - INFO - 数据库连接成功
2025-11-24 15:00:00 - INFO - 开始采集玩家数据: 76561198958724637
...
2025-11-24 15:00:05 - INFO - 数据采集完成
```

### 6. 配置定时任务（Scheduler）

#### 方式A：使用 Replit Cron Jobs（推荐）

1. 点击侧边栏的 **⏰ Cron Jobs**
2. 点击 **Create cron job**
3. 配置：
   - **Schedule**: `*/10 * * * *`（每 10 分钟）
   - **Command**: `python collector.py`
   - **Timezone**: 选择你的时区
4. 点击 **Create**

#### 方式B：使用 Python 脚本循环

创建 `scheduler.py`：

```python
#!/usr/bin/env python3
"""定时调度器"""
import time
import subprocess
from datetime import datetime

INTERVAL = 600  # 10 分钟（秒）

print(f"🚀 调度器启动，间隔 {INTERVAL} 秒")

while True:
    try:
        print(f"\n{'='*50}")
        print(f"⏰ 执行时间: {datetime.now()}")
        print(f"{'='*50}")
        
        result = subprocess.run(['python', 'collector.py'], 
                              capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("错误:", result.stderr)
            
    except Exception as e:
        print(f"❌ 执行失败: {e}")
    
    print(f"\n😴 等待 {INTERVAL} 秒...")
    time.sleep(INTERVAL)
```

然后修改 `.replit`：

```toml
run = "python scheduler.py"
```

---

## 🌐 前端部署（可视化界面）

### 1. 创建 Repl

1. 登录 [Replit](https://replit.com)
2. 点击 **Create Repl**
3. 选择 **Python** 模板
4. 命名: `steam-dashboard`（或你喜欢的名字）
5. 点击 **Create Repl**

### 2. 上传代码

将 `frontend/` 文件夹中的所有文件上传到 Repl：

```
steam-dashboard/
├── app.py               # FastAPI 应用
├── requirements.txt     # 依赖包
├── pyproject.toml       # 项目配置
├── .replit             # Replit 配置
├── templates/           # HTML 模板
│   └── dashboard.html
└── static/              # 静态文件（如果有）
```

### 3. 配置环境变量（Secrets）

点击左侧的 **🔒 Secrets**，添加：

| 变量名 | 值 | 说明 |
|--------|-----|------|
| `DATABASE_URL` | `postgresql://user:pass@host:port/db` | 数据库连接字符串（与后端相同） |

### 4. 安装依赖

在 Shell 中运行：

```bash
pip install -r requirements.txt
```

### 5. 测试运行

点击绿色的 **▶ Run** 按钮，应该看到：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

在 Replit 的 **Webview** 中应该能看到玩家列表页面。

### 6. 配置 Always On

为了让前端 24/7 运行：

#### 方式A：Replit 自动部署（推荐）

1. 点击顶部的 **Deploy** 按钮
2. 选择 **Autoscale deployment** 或 **Reserved VM**
3. 按照提示完成部署

#### 方式B：手动保持运行

如果没有付费计划，可以使用 UptimeRobot 等服务定期 ping 你的 Repl：

1. 获取 Repl 的公开 URL（如 `https://steam-dashboard.yourusername.repl.co`）
2. 在 [UptimeRobot](https://uptimerobot.com) 创建 HTTP 监控
3. 设置每 5 分钟 ping 一次

---

## 📊 数据库准备

### Neon PostgreSQL（推荐）

1. 访问 [Neon](https://neon.tech)
2. 创建免费账号
3. 创建新项目
4. 复制连接字符串（格式：`postgresql://...`）
5. 在本地或 Replit Shell 中运行初始化脚本：

```bash
# 方式1：使用 psql
psql "postgresql://user:pass@host/db" -f init_db.sql

# 方式2：使用 Python
python init_database.py
```

初始化脚本会创建：
- `game_snapshots` 表
- 必要的索引

---

## ⚙️ 配置清单

### 后端（steam-collector）

- [x] 上传代码文件
- [x] 配置 `DATABASE_URL` Secret
- [x] 配置 `STEAM_COOKIES` Secret（可选）
- [x] 安装依赖
- [x] 测试运行
- [x] 配置 Cron Job（每 10 分钟）

### 前端（steam-dashboard）

- [x] 上传代码文件
- [x] 配置 `DATABASE_URL` Secret
- [x] 安装依赖
- [x] 测试运行
- [x] 部署 Always On

### 数据库

- [x] 创建 PostgreSQL 数据库
- [x] 运行 `init_db.sql`
- [x] 测试连接

---

## 🧪 测试流程

### 1. 测试后端

在后端 Repl 的 Shell 中运行：

```bash
python collector.py
```

应该看到：
```
✅ 数据库连接成功
✅ 成功采集玩家数据
✅ 数据已保存
```

### 2. 测试前端

1. 运行前端 Repl
2. 访问 Webview 中的 URL
3. 应该看到玩家列表
4. 点击玩家，查看游戏时长分析

### 3. 测试定时任务

1. 等待 10 分钟
2. 查看后端 Repl 的日志
3. 确认自动采集成功

---

## 🐛 常见问题

### 后端 Repl 自动停止？

**原因**: Replit 免费计划会在一段时间无活动后休眠

**解决方案**:
- 升级到付费计划
- 使用 Scheduler 定时运行
- 或使用其他云平台（如 Railway、Fly.io）

### 前端无法连接数据库？

**检查项**:
1. `DATABASE_URL` 是否正确配置
2. 数据库是否允许外部连接
3. 防火墙规则是否正确
4. SSL 模式是否设置为 `require`

### Cron Job 没有执行？

**检查项**:
1. Cron 表达式是否正确
2. 命令路径是否正确（`python collector.py`）
3. 查看 Cron 日志（Replit 提供）

### Cookie 失效？

**症状**: 无法获取好友的游戏数据

**解决方案**:
1. 重新获取 Steam Cookie
2. 更新 `STEAM_COOKIES` Secret
3. 重启后端 Repl

---

## 🔐 安全建议

### 1. 保护 Secrets

- ✅ 使用 Replit Secrets 存储敏感信息
- ✅ 不要在代码中硬编码密码
- ✅ 不要分享包含 Secrets 的代码

### 2. 数据库安全

- ✅ 使用强密码
- ✅ 启用 SSL 连接
- ✅ 定期备份数据

### 3. Cookie 管理

- ✅ 定期更换 Cookie
- ✅ 监控异常登录
- ✅ 考虑使用专门账号

---

## 📚 相关文档

- [Replit 官方文档](https://docs.replit.com)
- [Neon PostgreSQL 文档](https://neon.tech/docs)
- [FastAPI 文档](https://fastapi.tiangolo.com)
- [项目 README](../README.md)
- [Cookie 获取指南](../COOKIE_GUIDE.md)

---

## 💡 优化建议

### 性能优化

1. **增加采集频率**
   - 调整 Cron 为每 5 分钟: `*/5 * * * *`
   - 更密集的数据点，更准确的时间推断

2. **数据库索引**
   - 已自动创建必要索引
   - 定期运行 `VACUUM ANALYZE`

3. **缓存策略**
   - 前端可添加 Redis 缓存
   - 减少数据库查询压力

### 功能扩展

1. **多玩家支持**
   - 在 `config.toml` 添加更多玩家
   - 前端显示玩家选择器

2. **通知功能**
   - 检测到玩家上线时发送通知
   - 使用 Discord Webhook 或邮件

3. **统计分析**
   - 每周/每月游戏时长报告
   - 游戏习惯热力图

---

**更新日期**: 2025-11-24  
**版本**: 1.0

