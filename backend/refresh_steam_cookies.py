#!/usr/bin/env python3
"""
使用浏览器刷新 Steam Cookie 并写入 Cookie 文件

本脚本只负责流程和入口：
- 读取现有 Cookie（如有）以复用会话
- 打开浏览器访问 Steam 社区
- 从浏览器上下文中提取最新 Cookie
- 通过 cookie_store.save_steam_cookies 写入由 STEAM_COOKIES_FILE 指定的文件

具体使用哪种浏览器引擎、是否启用无头模式等细节，交由 Playwright 等库配置。
"""

import asyncio
import logging
import os
from typing import List

from dotenv import load_dotenv
from cookie_store import load_steam_cookies, save_steam_cookies

logger = logging.getLogger(__name__)


async def _collect_cookie_string_from_playwright() -> str:
    """
    使用 Playwright 收集最新的 Steam Cookie 字符串

    默认使用 Chromium，界面模式由环境变量控制：
    - STEAM_BROWSER_HEADLESS = "1" 时启用无头模式
    - 其他情况使用有界面模式，便于手动登录

    Returns:
        标准 Cookie 字符串
    """
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except Exception as exc:
        raise RuntimeError("未安装 playwright 依赖，请先执行 `uv add playwright`") from exc

    headless_flag = os.getenv("STEAM_BROWSER_HEADLESS", "").strip()
    headless = headless_flag == "1"

    existing_cookie_string = load_steam_cookies()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        if existing_cookie_string:
            pairs: List[dict] = []
            for item in existing_cookie_string.split(";"):
                item = item.strip()
                if not item or "=" not in item:
                    continue
                name, value = item.split("=", 1)
                pairs.append(
                    {
                        "name": name.strip(),
                        "value": value.strip(),
                        "domain": ".steamcommunity.com",
                        "path": "/",
                    }
                )
            if pairs:
                await context.add_cookies(pairs)

        target_url = "https://steamcommunity.com/my"
        logger.info("正在打开浏览器访问: %s", target_url)
        await page.goto(target_url, wait_until="networkidle")

        if "login" in page.url:
            if not headless:
                logger.info("检测到登录页面，请在浏览器中完成登录后按 Enter 继续...")
                input()
            else:
                logger.warning(
                    "当前为无头模式且页面为登录页，无法进行人工登录，如需手动登录请关闭无头模式"
                )

        await page.wait_for_timeout(3000)

        cookies = await context.cookies("https://steamcommunity.com")
        await browser.close()

        parts: List[str] = []
        for c in cookies:
            name = c.get("name")
            value = c.get("value")
            if not name or value is None:
                continue
            parts.append(f"{name}={value}")

        if not parts:
            raise RuntimeError("未能从浏览器上下文获取到任何 Cookie")

        return "; ".join(parts)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        logger.warning(".env 文件不存在，尝试从环境变量读取配置")

    logger.info("Steam Cookie 刷新工具启动")

    cookie_string = asyncio.run(_collect_cookie_string_from_playwright())
    target_path = save_steam_cookies(cookie_string)

    if target_path:
        logger.info("已完成 Cookie 刷新，输出文件: %s", target_path)
    else:
        logger.error("Cookie 刷新已获取到数据，但未能写入文件")


if __name__ == "__main__":
    main()
