# Replit 部署指南

完整的 Replit 部署教程，用于部署 Steam 游戏时长追踪系统的后端采集器和前端可视化服务。

## 📋 准备工作

### 1. 所需资源

- **Replit 账号**：[https://replit.com](https://replit.com)（免费账号即可）
- **PostgreSQL 数据库**：推荐使用以下服务之一
  - [Neon](https://neon.tech)（免费）
  - [Supabase](https://supabase.com)（免费）
  - [ElephantSQL](https://www.elephantsql.com)（免费）
  - Replit PostgreSQL（付费）
- **Steam Web API Key**：在 [https://steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey) 申请

### 2. 获取 PostgreSQL 数据库

#### 使用 Neon（推荐）

1. 访问 [https://neon.tech](https://neon.tech) 注册账号
2. 创建新项目
3. 复制连接字符串，格式类似：
   ```
   postgresql://username:password@ep-xxx-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

#### 使用 Supabase

1. 访问 [https://supabase.com](https://supabase.com) 注册账号
2. 创建新项目
3. 在项目设置中找到 Database 连接信息
4. 使用 Connection String（URI 格式）

---

## 🔧 部署后端（数据采集器）

### 步骤 1：创建 Replit 项目

1. 登录 Replit，点击 **Create Repl**
2. 选择 **Python** 模板
3. 命名为 `steam-collector`
4. 点击 **Create Repl**

### 步骤 2：上传代码

在 Replit 编辑器中创建以下文件结构：

```
steam-collector/
├── collector.py          # 从 backend/collector.py 复制内容
├── pyproject.toml        # 从 backend/pyproject.toml 复制内容
├── requirements.txt      # 从 backend/requirements.txt 复制内容
├── .replit              # 从 backend/.replit 复制内容
└── config.toml          # 从根目录 config.toml 复制内容（修改玩家信息）
```

**方法 A：手动创建文件**
- 在 Replit 左侧文件树中点击 ➕ 创建文件
- 复制本地对应文件的内容粘贴进去

**方法 B：从 GitHub 导入**
- 如果你的代码已上传到 GitHub
- 在创建 Repl 时选择 "Import from GitHub"

### 步骤 3：配置环境变量

1. 在 Replit 左侧面板找到 **Tools** → **Secrets**
2. 添加以下两个环境变量：

   ```
   Key: STEAM_API_KEY
   Value: 你的Steam API密钥
   ```

   ```
   Key: DATABASE_URL
   Value: postgresql://user:pass@host:port/database
   ```

### 步骤 4：修改 config.toml

编辑 `config.toml` 文件，设置你要监控的玩家：

```toml
[steam]
# 不需要在这里填写 API Key，从环境变量读取

[[steam.players]]
steamid = "你的Steam ID（64位）"
vanity_url = "你的Steam用户名"

# 如果要监控多个玩家，添加更多：
[[steam.players]]
steamid = "另一个玩家的Steam ID"
vanity_url = "另一个玩家的用户名"
```

**如何获取 Steam ID：**
- 访问 [https://steamid.io](https://steamid.io)
- 输入你的 Steam 个人资料 URL
- 复制 **steamID64** 的值

### 步骤 5：初始化数据库

1. 在 Replit Shell 中运行：

   ```bash
   uv sync
   ```

2. 创建一个临时的 `init_db.py` 文件（复制项目根目录的 `init_database.py`）

3. 运行初始化脚本：

   ```bash
   uv run python init_db.py
   ```

4. 看到 "✅ 数据库初始化完成" 后可以删除 `init_db.py`

### 步骤 6：测试采集器

在 Shell 中运行：

```bash
uv run python collector.py
```

应该看到类似输出：

```
INFO - 数据库连接成功
INFO - 开始采集玩家数据: 76561198958724637
INFO - 成功获取玩家 76561198958724637 的游戏数据
INFO - 成功保存玩家 76561198958724637 的快照
INFO - 玩家 xxx 拥有 xx 个游戏
INFO - 数据采集完成
```

### 步骤 7：设置定时任务（Cron Job）

⚠️ **注意：Replit 的免费账号可能不支持 Scheduler。如果需要定时任务，建议升级到付费计划。**

#### 使用 Replit Scheduler（付费功能）

1. 在 Replit 左侧面板找到 **Tools** → **Cron Jobs**
2. 点击 **Add Cron Job**
3. 设置：
   - **Name**: `collect_steam_data`
   - **Command**: `uv run python collector.py`
   - **Schedule**: 选择 **Custom**
   - **Cron Expression**: `*/10 * * * *`（每 10 分钟运行）
4. 点击 **Save**

#### 替代方案：使用外部 Cron 服务

如果没有付费 Replit 账号，可以使用外部服务：

1. **cron-job.org**（免费）
   - 注册账号
   - 创建一个 HTTP 任务，调用你的 Replit HTTP 端点触发采集

2. **修改代码添加 HTTP 端点**：

   在 `collector.py` 的最后添加：

   ```python
   from flask import Flask
   app = Flask(__name__)

   @app.route('/collect')
   def trigger_collect():
       main()
       return "Collection completed"

   if __name__ == '__main__':
       import sys
       if len(sys.argv) > 1 and sys.argv[1] == 'serve':
           app.run(host='0.0.0.0', port=8080)
       else:
           main()
   ```

   然后在 cron-job.org 设置每 10 分钟访问一次你的 Replit URL + `/collect`

---

## 🌐 部署前端（可视化服务）

### 步骤 1：创建另一个 Replit 项目

1. 登录 Replit，点击 **Create Repl**
2. 选择 **Python** 模板
3. 命名为 `steam-dashboard`
4. 点击 **Create Repl**

### 步骤 2：上传代码

创建以下文件结构：

```
steam-dashboard/
├── app.py                # 从 frontend/app.py 复制内容
├── pyproject.toml        # 从 frontend/pyproject.toml 复制内容
├── requirements.txt      # 从 frontend/requirements.txt 复制内容
└── .replit              # 从 frontend/.replit 复制内容
```

### 步骤 3：配置环境变量

在 **Tools** → **Secrets** 中添加：

```
Key: DATABASE_URL
Value: postgresql://user:pass@host:port/database
```

⚠️ **使用与后端相同的数据库连接字符串**

### 步骤 4：启动服务

1. 在 Shell 中运行：

   ```bash
   uv sync
   ```

2. 点击 Replit 顶部的 **Run** 按钮

3. 服务启动后，Replit 会自动打开预览窗口

### 步骤 5：配置自动部署（Always On）

⚠️ **Always On 是 Replit 的付费功能**

1. 在 Replit 项目页面，点击右上角的 **Deploy**
2. 选择 **Static** 或 **Autoscale**（根据需求）
3. 配置部署设置
4. 点击 **Deploy**

### 步骤 6：访问前端

- **开发预览**：Replit 提供的临时 URL（形如 `https://xxx.replit.dev`）
- **生产部署**：部署后的永久 URL

在浏览器中打开 URL，你应该能看到：
1. 玩家列表页面
2. 点击玩家查看详细分析和图表

---

## 🔍 验证部署

### 检查后端采集器

1. 在 Replit Shell 运行 `uv run python collector.py`
2. 检查日志输出是否正常
3. 如果设置了 Cron Job，检查定时任务日志

### 检查前端服务

1. 访问前端 URL
2. 应该能看到玩家列表
3. 点击查看分析（第一次可能数据较少）

### 检查数据库

连接到 PostgreSQL 数据库，运行查询：

```sql
SELECT player_name, snapshot_time, 
       jsonb_array_length(games_data->'games') as game_count
FROM game_snapshots
ORDER BY snapshot_time DESC
LIMIT 10;
```

应该能看到采集的快照记录。

---

## 🐛 常见问题

### Q1: "ModuleNotFoundError" 错误

**解决方案**：运行 `uv sync` 安装所有依赖

### Q2: "数据库连接失败"

**检查项**：
- DATABASE_URL 是否正确配置
- 数据库是否允许外部连接
- 是否需要添加 `?sslmode=require` 参数

### Q3: "表不存在" 错误

**解决方案**：运行数据库初始化脚本 `init_db.py`

### Q4: Steam API 返回 403 错误

**可能原因**：
- API Key 无效或过期
- 请求频率过高（建议间隔 5-10 分钟）
- 玩家资料设置为私密

### Q5: Replit 免费账号限制

**限制**：
- 不支持后台运行（服务会在一段时间无活动后休眠）
- 不支持 Cron Jobs
- 资源受限

**建议**：
- 升级到 Replit Hacker 或 Pro 计划
- 或使用其他平台（Heroku、Railway、Render等）

---

## 📊 数据累积建议

为了获得有意义的游玩时间推断：

1. **最少需要 2 次快照**：才能计算时长变化
2. **建议采集频率**：5-10 分钟一次
3. **建议运行时长**：至少 24 小时
4. **最佳效果**：运行 1 周以上，可以看到完整的游玩习惯分析

---

## 🔄 更新代码

当需要更新代码时：

1. 在本地修改代码
2. 复制修改后的文件到 Replit
3. 如果修改了依赖，运行 `uv sync`
4. 重启服务

---

## 💡 优化建议

### 性能优化

1. **数据库索引**：已自动创建，无需额外配置
2. **API 缓存**：避免频繁请求同一数据
3. **前端分页**：如果玩家数量多，添加分页功能

### 成本优化

1. **数据保留策略**：定期清理旧快照（超过 30 天）
2. **按需查询**：只在需要时加载详细数据
3. **使用免费数据库**：Neon 和 Supabase 的免费套餐足够使用

---

## 📞 获取帮助

如果遇到问题：

1. 检查 Replit Shell 的日志输出
2. 查看 README.md 中的完整文档
3. 确认所有环境变量配置正确
4. 验证数据库连接和表结构

---

## ✅ 部署清单

- [ ] 获取 Steam API Key
- [ ] 创建 PostgreSQL 数据库
- [ ] 获取数据库连接字符串
- [ ] 创建后端 Replit 项目
- [ ] 上传后端代码
- [ ] 配置后端环境变量
- [ ] 初始化数据库表
- [ ] 测试采集器运行
- [ ] 设置定时任务（可选）
- [ ] 创建前端 Replit 项目
- [ ] 上传前端代码
- [ ] 配置前端环境变量
- [ ] 启动前端服务
- [ ] 测试前端访问
- [ ] 配置 Always On（可选）

---

**祝你部署顺利！🎉**

