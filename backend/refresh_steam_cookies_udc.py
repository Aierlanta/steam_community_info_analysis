#!/usr/bin/env python3
"""
使用 undetected-chromedriver 刷新 Steam Cookie 并写入 Cookie 文件。

流程：
- 可选：加载已有 Cookie 并注入浏览器，复用会话
- 打开 https://steamcommunity.com/my
- 若出现登录页，人工登录（非无头模式）
- 从浏览器读取最新 Cookie，写入由 STEAM_COOKIES_FILE 指定的文件
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List

from cookie_store import load_steam_cookies, save_steam_cookies
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


def _parse_cookie_string(cookie_string: str) -> List[Dict[str, str]]:
    """将标准 Cookie 串解析为 Selenium 可用的 cookie 对象列表。"""
    result: List[Dict[str, str]] = []
    for item in cookie_string.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        name, value = item.split("=", 1)
        result.append(
            {
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".steamcommunity.com",
                "path": "/",
            }
        )
    return result


def refresh_cookies_with_udc() -> None:
    """使用 undetected-chromedriver 刷新 Cookie 并写入文件。"""
    try:
        import undetected_chromedriver as uc  # type: ignore
    except Exception as exc:  # pragma: no cover - 依赖缺失时的防御性分支
        raise RuntimeError(
            "未安装 undetected-chromedriver 依赖，请先在 backend 目录执行：\n"
            "  uv add undetected-chromedriver"
        ) from exc

    # 容错：undetected-chromedriver 在 __del__ 里有时会对已关闭的句柄重复 quit，导致 WinError 6。
    # 这里给它打个补丁，忽略析构阶段的异常，避免噪声。
    def _silent_del(self):  # type: ignore
        try:
            self.quit()
        except Exception:
            pass

    try:
        uc.Chrome.__del__ = _silent_del  # type: ignore
    except Exception:
        pass

    headless_flag = os.getenv("STEAM_BROWSER_HEADLESS", "").strip()
    headless = headless_flag == "1"

    options = uc.ChromeOptions()
    # 保持通用配置，将具体指纹、代理等交给环境配置
    if headless:
        options.add_argument("--headless=new")

    logger.info("正在启动 undetected-chromedriver（headless=%s）", headless)
    driver = uc.Chrome(options=options)
    driver.set_window_size(1280, 720)

    try:
        # 先访问主站，为注入 cookie 做准备
        base_url = "https://steamcommunity.com"
        driver.get(base_url)

        existing_cookie_string = load_steam_cookies()
        if existing_cookie_string:
            cookies = _parse_cookie_string(existing_cookie_string)
            for c in cookies:
                try:
                    driver.add_cookie(c)
                except Exception as add_exc:
                    logger.debug("注入单个 Cookie 失败: %s (%s)", c.get("name"), add_exc)
            driver.get(base_url)

        target_url = "https://steamcommunity.com/my"
        logger.info("正在打开: %s", target_url)
        driver.get(target_url)

        current_url = driver.current_url or ""
        if "login" in current_url.lower() and not headless:
            logger.info("检测到登录页面，请在浏览器中完成登录后按 Enter 继续...")
            input()
            time.sleep(3)
        elif "login" in current_url.lower() and headless:
            logger.warning(
                "当前为无头模式且页面为登录页，无法人工登录，如需手动登录请关闭无头模式"
            )
            time.sleep(3)

        time.sleep(3)

        cookies = driver.get_cookies()
        if not cookies:
            raise RuntimeError("未能从浏览器获取到任何 Cookie")

        parts = []
        for c in cookies:
            name = c.get("name")
            value = c.get("value")
            if not name or value is None:
                continue
            parts.append(f"{name}={value}")

        if not parts:
            raise RuntimeError("获取到的 Cookie 列表为空")

        cookie_string = "; ".join(parts)
        target_path = save_steam_cookies(cookie_string)

        if target_path:
            logger.info("已完成 Cookie 刷新，输出文件: %s", target_path)
        else:
            logger.error("Cookie 刷新已获取到数据，但未能写入文件")

    finally:
        try:
            driver.quit()
        except Exception:
            pass


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    load_dotenv(Path(__file__).with_name(".env"))
    logger.info("Steam Cookie 刷新工具（undetected-chromedriver）启动")
    refresh_cookies_with_udc()


if __name__ == "__main__":
    main()
