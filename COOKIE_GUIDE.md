# Steam Cookie 获取指南

## 🔐 为什么需要 Cookie？

如果你想追踪的好友设置了"仅好友可见"的个人资料，爬虫默认无法访问。通过添加你的 Steam Cookie，爬虫可以模拟登录状态，访问好友的资料。

## 📋 获取 Steam Cookie

### 方法1：使用浏览器开发者工具

1. **打开 Steam 社区并登录**
   - 访问 [https://steamcommunity.com](https://steamcommunity.com)
   - 确保已登录你的账号

2. **打开开发者工具**
   - Chrome/Edge: 按 `F12` 或 `Ctrl + Shift + I`
   - Firefox: 按 `F12`

3. **切换到 Application/Storage 标签**
   - Chrome/Edge: 点击顶部的 **Application** 标签
   - Firefox: 点击 **Storage** 标签

4. **查看 Cookies**
   - 左侧展开 **Cookies**
   - 点击 `https://steamcommunity.com`

5. **复制重要的 Cookie**

需要复制的 Cookie：

- `sessionid`
- `steamLoginSecure`
- `steamRememberLogin` (可选)
- `steamCountry` (可选)

### 方法2：使用浏览器扩展

使用 **EditThisCookie** 或类似扩展：

1. 安装扩展 ([Chrome 商店](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg))
2. 访问 Steam 社区并登录
3. 点击扩展图标
4. 点击 **Export** 导出所有 Cookie

## 🔧 配置 Cookie

### 在 .env 文件中配置

编辑 `backend/.env` 文件，添加：

```env
STEAM_COOKIES=sessionid=你的sessionid; steamLoginSecure=你的steamLoginSecure; steamRememberLogin=你的值
```

### Cookie 格式说明

```
sessionid=xxxx; steamLoginSecure=xxxx; steamRememberLogin=xxxx
```

**重要**：

- Cookie 值之间用 `;` 分号加空格分隔
- 不要包含 `Domain`、`Path` 等额外字段
- 只需要 `key=value` 格式

### 示例

```env
STEAM_COOKIES=sessionid=abc123def456; steamLoginSecure=76561198958724637%7C%7CEyAD; steamRememberLogin=76561198958724637%7C%7C123456789
```

## ⚠️ 安全注意事项

### 1. Cookie 是敏感信息

**Cookie 相当于你的登录凭证**，泄露后他人可以：

- 登录你的账号
- 查看你的个人信息
- 进行交易等操作

### 2. 保护你的 Cookie

- ✅ 将 `.env` 文件添加到 `.gitignore`
- ✅ 不要分享你的 Cookie
- ✅ 不要上传包含 Cookie 的文件到 GitHub
- ✅ 定期更换密码（会使 Cookie 失效）

### 3. Cookie 有效期

Steam Cookie 通常有效期很长（几个月），但会在以下情况失效：

- 修改密码
- 退出登录
- 清除浏览器 Cookie
- Steam 安全机制触发

### 4. 发现泄露怎么办？

如果 Cookie 不慎泄露：

1. 立即修改 Steam 密码
2. 启用 Steam 令牌（如果未启用）
3. 检查账号活动记录

## 🧪 测试 Cookie

### 方法1：使用测试脚本

创建 `test_cookie.py`：

```python
from steam_scraper import SteamProfileScraper
import os
from dotenv import load_dotenv

load_dotenv()

cookies = os.getenv('STEAM_COOKIES')
scraper = SteamProfileScraper(cookies=cookies)

# 测试访问一个好友的资料
steamid = "76561198817252303"  # 替换为你好友的 Steam ID
games = scraper.scrape_recent_games(steamid)

if games:
    print(f"✅ Cookie 有效！找到 {len(games)} 个游戏")
    for game in games:
        print(f"  - {game['game_name']}")
else:
    print("❌ 无法获取数据，Cookie 可能无效或账号设置为私密")
```

运行：

```bash
cd backend
uv run python test_cookie.py
```

### 方法2：使用 curl 测试

```bash
curl -H "Cookie: sessionid=你的值; steamLoginSecure=你的值" \
     https://steamcommunity.com/profiles/76561198817252303/
```

如果返回 HTML 包含游戏信息，说明 Cookie 有效。

## 📝 常见问题

### Q: Cookie 格式不对？

**错误示例**：

```
sessionid=abc123; domain=.steamcommunity.com; path=/; secure
```

**正确示例**：

```
sessionid=abc123; steamLoginSecure=xyz789
```

只保留 `key=value` 部分。

### Q: 设置了 Cookie 还是无法访问？

可能原因：

1. Cookie 已过期 - 重新获取
2. 好友屏蔽了你 - 无法访问
3. Cookie 格式错误 - 检查格式
4. 账号已退出登录 - 重新登录浏览器

### Q: 需要所有 Cookie 吗？

最重要的是：

- **必需**：`sessionid` 和 `steamLoginSecure`
- **可选**：其他 Cookie

只有这两个也能工作。

### Q: Cookie 会被存储到哪里？

Cookie 只在内存中使用，不会被：

- 存储到数据库
- 写入日志文件
- 上传到服务器

但 `.env` 文件会保存，请确保不要分享。

## 🔄 Cookie 轮换建议

为了安全，建议：

1. **定期更换** (每 1-3 个月)
   - 修改 Steam 密码
   - 重新获取 Cookie

2. **监控使用**
   - 检查 Steam 账号活动
   - 注意异常登录提示

3. **限制权限**
   - 仅在必要时使用 Cookie
   - 考虑使用专门的小号

## 📖 相关文档

- [Steam Web API 文档](https://steamcommunity.com/dev)
- [Cookie 安全最佳实践](https://owasp.org/www-community/controls/SecureCookieAttribute)

## ⚖️ 免责声明

使用 Cookie 访问他人资料时，请：

- 确保你有权限访问这些信息
- 遵守 Steam 使用条款
- 尊重他人隐私

本工具仅用于个人学习和数据分析，使用者需自行承担风险。

---

**最后更新**: 2024-11-24
