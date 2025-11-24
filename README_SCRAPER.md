# Steam 游戏时长追踪系统 - 爬虫版本说明

## 🔄 重大更新

系统已从 **Steam Web API** 切换到 **网页爬虫模式**，以获取更实时的游戏数据。

## 📋 工作原理

### 旧版本（Steam API）
- 调用 `IPlayerService/GetOwnedGames` API
- 获取玩家所有游戏的时长
- **问题**：数据更新不够实时

### 新版本（网页爬虫）⭐
- 爬取 Steam 个人主页的"最新动态"区域
- 获取最近玩过的 **3个游戏** 的实时数据
- **优点**：数据更实时、更准确

## 🎯 获取的数据

从个人主页"最新动态"获取：
- 游戏名称
- 游戏ID (AppID)
- 总游戏时长
- 最后运行日期
- 成就进度

## ⚙️ 使用方法

### 后端采集器

```bash
cd backend
uv run python collector.py
```

采集器会：
1. 读取 `config.toml` 中配置的玩家列表
2. 爬取每个玩家的个人主页
3. 提取"最新动态"中的3个游戏数据
4. 与上次快照对比，如有变化则保存

### 配置玩家

编辑 `config.toml`：

```toml
[[steam.players]]
steamid = "76561198958724637"
vanity_url = "morbisol"  # 个性化URL（可选）
```

**注意**：
- `steamid` 是必填的 64位 Steam ID
- `vanity_url` 是你的个性化链接（如果有）

### 获取 Steam ID

访问 [https://steamid.io](https://steamid.io)，输入你的个人主页链接，复制 **steamID64**。

## 📊 数据格式

### 数据库存储格式

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

### 字段说明

- `data_source`: 数据来源标识（`web_scraper` 或 `steam_api`）
- `game_count`: 游戏数量
- `recent_games`: 最近玩过的游戏列表
- `playtime_total`: 总时长（小时）
- `last_played`: 最后运行日期

## ⚠️ 限制

### 1. 只追踪最近3个游戏

Steam 个人主页的"最新动态"默认只显示最近玩过的3个游戏，因此：
- ✅ 适合追踪"当前在玩什么"
- ✅ 数据更实时
- ⚠️ 不会记录所有游戏的历史

### 2. 账号隐私设置

如果玩家的个人资料设为私密，将无法爬取数据。

确保要监控的账号：
- 个人资料设为 **公开**
- 游戏详情设为 **公开**

### 3. 网络要求

- 需要能访问 `steamcommunity.com`
- 如果遇到连接问题，可能需要代理

## 🔧 故障排除

### 问题1：无法获取游戏数据

**可能原因**：
- 账号设为私密
- 网络连接问题
- Steam 社区暂时无法访问

**解决方案**：
1. 检查账号隐私设置
2. 尝试手动访问个人主页确认可访问
3. 检查日志了解具体错误

### 问题2：数据不更新

**可能原因**：
- 游戏时长未发生变化
- 采集间隔太短

**解决方案**：
- 确认实际玩了游戏
- 等待几分钟后再次采集
- 查看日志确认是否检测到变化

### 问题3：某些游戏不显示

这是正常的！"最新动态"只显示最近玩过的3个游戏。如果想追踪更多游戏，需要：
- 保持定期采集（如每10分钟）
- 通过历史快照查看之前玩过的游戏

## 📈 前端可视化

前端会自动兼容新旧两种数据格式：

```bash
cd frontend
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000` 查看：
- 玩家列表
- 游戏时长推断时间轴
- 游戏时长统计图表
- 游玩习惯分析

## 🔄 数据兼容性

系统同时支持：
- ✅ 新格式（爬虫数据）
- ✅ 旧格式（Steam API数据）

如果数据库中有旧的 API 数据，前端仍然可以正常显示。

## 📝 最佳实践

### 采集频率

推荐设置：
- **开发/测试**：每 5-10 分钟
- **生产环境**：每 10-15 分钟

避免过于频繁的请求，以免被 Steam 限制。

### 数据保留

建议定期清理旧快照：

```sql
-- 删除30天前的快照
DELETE FROM game_snapshots 
WHERE snapshot_time < NOW() - INTERVAL '30 days';
```

## 🆚 对比

| 特性 | Steam API | 网页爬虫 |
|------|-----------|---------|
| 数据实时性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 游戏覆盖 | 所有游戏 | 最近3个 |
| API Key | 需要 | 不需要 |
| 限流风险 | 低 | 中 |
| 隐私要求 | 账号公开 | 账号公开 |

## 🔗 相关文件

- `backend/steam_scraper.py` - 爬虫核心代码
- `backend/collector.py` - 采集器主程序
- `frontend/app.py` - 前端数据处理
- `config.toml` - 玩家配置

## ❓ 常见问题

**Q: 能同时监控多个玩家吗？**  
A: 可以！在 `config.toml` 中添加多个 `[[steam.players]]` 配置块。

**Q: 数据多久更新一次？**  
A: 取决于采集器运行频率。建议设置定时任务每10分钟运行一次。

**Q: 可以追踪历史上玩过的所有游戏吗？**  
A: 可以通过查看历史快照记录，但只能看到当时出现在"最新动态"中的游戏。

**Q: 如果我想追踪所有游戏怎么办？**  
A: 可以使用旧版本的 `collector_old_api.py.bak`（需要 Steam API Key）。

---

**更新日期**: 2024-11-24  
**版本**: 2.0 (Scraper Edition)

