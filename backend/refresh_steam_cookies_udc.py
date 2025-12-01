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
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

from cookie_store import load_steam_cookies, save_steam_cookies
from dotenv import load_dotenv


logger = logging.getLogger(__name__)


def _is_replit_environment() -> bool:
    """检测是否在 Replit 环境中运行。"""
    return bool(os.getenv("REPL_ID") or os.getenv("REPLIT"))


def _find_chromium_paths() -> tuple[Optional[str], Optional[str]]:
    """
    在系统中查找 chromium 和 chromedriver 的路径。
    返回 (browser_path, driver_path) 元组。
    """
    browser_path = None
    driver_path = None

    # 尝试查找 chromium 浏览器
    for browser_name in ["chromium", "chromium-browser", "google-chrome", "chrome"]:
        path = shutil.which(browser_name)
        if path:
            browser_path = path
            logger.info("找到浏览器: %s", browser_path)
            break

    # 尝试查找 chromedriver
    for driver_name in ["chromedriver", "chromium-chromedriver"]:
        path = shutil.which(driver_name)
        if path:
            driver_path = path
            logger.info("找到 chromedriver: %s", driver_path)
            break

    return browser_path, driver_path


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

    # Replit 环境中需要添加额外的参数
    is_replit = _is_replit_environment()
    browser_path = None
    driver_path = None

    if is_replit:
        logger.info("检测到 Replit 环境，正在配置 Chromium...")
        browser_path, driver_path = _find_chromium_paths()

        # 添加 Replit 环境所需的 Chrome 参数
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")

        if not browser_path:
            raise RuntimeError(
                "Replit 环境中未找到 Chromium 浏览器，请确保 .replit 文件中包含 chromium 包"
            )

    logger.info("正在启动 undetected-chromedriver（headless=%s）", headless)

    # 构建 uc.Chrome 参数
    chrome_kwargs = {"options": options}
    if browser_path:
        chrome_kwargs["browser_executable_path"] = browser_path
    if driver_path:
        chrome_kwargs["driver_executable_path"] = driver_path

    driver = uc.Chrome(**chrome_kwargs)
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
