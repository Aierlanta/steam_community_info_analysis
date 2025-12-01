#!/usr/bin/env python3
"""
统一启动脚本 main.py

负责串联整个流程：
- 可选：使用 undetected-chromedriver 刷新 / 校验 Steam Cookie
- 启动原有的 collector.py 进行数据采集

行为通过环境变量控制，避免硬编码策略：
- STEAM_AUTO_REFRESH_COOKIES=1 时，先尝试用 undetected-chromedriver 刷新失效的 Cookie
  （依赖 backend/refresh_steam_cookies_udc.py 和 STEAM_COOKIES_FILE 配置）
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv

from cookie_store import load_steam_cookies, save_steam_cookies
from steam_scraper import SteamProfileScraper
from refresh_steam_cookies_udc import refresh_cookies_with_udc
from collector import main as collector_main


logger = logging.getLogger(__name__)


def _bootstrap_cookie_file_if_needed() -> None:
    """
    如果配置了 STEAM_COOKIES_FILE 但文件不存在，且存在环境变量 STEAM_COOKIES，
    则用环境变量内容创建该文件，方便后续刷新逻辑复用同一存储。
    """
    cookie_file_env = os.getenv("STEAM_COOKIES_FILE")
    env_cookie_value = os.getenv("STEAM_COOKIES")

    if not cookie_file_env:
        return

    if os.path.isabs(cookie_file_env):
        target_path = cookie_file_env
    else:
        target_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), cookie_file_env)
        )

    if os.path.exists(target_path):
        return

    if env_cookie_value:
        saved_path = save_steam_cookies(env_cookie_value)
        if saved_path:
            logger.info(
                "Cookie 文件缺失，已从环境变量 STEAM_COOKIES 写入文件: %s", saved_path
            )
    else:
        logger.info("Cookie 文件缺失，且未配置 STEAM_COOKIES，无法自动创建")


def _ensure_valid_cookies_with_udc() -> None:
    """
    在启用自动刷新时：
    - 如当前没有 Cookie，则尝试直接创建新的 Cookie 文件
    - 如已有 Cookie，则先调用 steam_scraper.verify_cookies() 校验
      - 通过：不刷新
      - 未通过或异常：调用 undetected-chromedriver 刷新 Cookie 文件
    - 刷新后再次验证，记录结果
    """
    cookies = load_steam_cookies()
    need_refresh = False

    if not cookies:
        logger.info("当前未配置 Steam Cookie，将尝试通过 undetected-chromedriver 创建新的 Cookie")
        need_refresh = True
    else:
        scraper = SteamProfileScraper(cookies=cookies)

        try:
            if scraper.verify_cookies():
                logger.info("现有 Steam Cookie 验证通过，无需刷新")
                return
            logger.warning("检测到 Steam Cookie 可能已失效，准备尝试自动刷新")
            need_refresh = True
        except Exception as exc:
            logger.warning("验证现有 Cookie 时发生异常，将尝试刷新: %s", exc)
            need_refresh = True

    if not need_refresh:
        return

    try:
        refresh_cookies_with_udc()
    except RuntimeError as exc:
        logger.error("使用 undetected-chromedriver 刷新 Cookie 失败: %s", exc)
        return
    except Exception as exc:
        logger.error("刷新 Cookie 过程中发生未知错误: %s", exc)
        return

    # 刷新完成后再验证一次
    new_cookies = load_steam_cookies()
    if not new_cookies:
        logger.warning("刷新后未能从 Cookie 文件加载到 Cookie")
        return

    new_scraper = SteamProfileScraper(cookies=new_cookies)
    try:
        if new_scraper.verify_cookies():
            logger.info("刷新后的 Steam Cookie 验证成功")
        else:
            logger.warning("刷新后的 Steam Cookie 仍无法通过验证")
    except Exception as exc:
        logger.warning("验证刷新后的 Cookie 时发生异常: %s", exc)


def main() -> None:
    """
    主入口：
    - 根据 STEAM_AUTO_REFRESH_COOKIES 决定是否先尝试自动刷新 Cookie
    - 然后调用原有 collector.main() 执行采集流程
    """
    # 先加载 backend 目录下的 .env，确保环境变量可用
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        logger.warning(".env 文件不存在，尝试从环境变量读取配置")

    _bootstrap_cookie_file_if_needed()

    auto_refresh_flag = os.getenv("STEAM_AUTO_REFRESH_COOKIES", "0").strip()

    if auto_refresh_flag == "1":
        logger.info("已启用自动刷新 Cookie（STEAM_AUTO_REFRESH_COOKIES=1）")
        _ensure_valid_cookies_with_udc()
    else:
        logger.info(
            "未启用自动刷新 Cookie（如需启用，请设置 STEAM_AUTO_REFRESH_COOKIES=1）"
        )

    # 调用原有采集器主入口
    collector_main()

    # 采集结束后再刷新一次 Cookie，保持文件为最新值
    if auto_refresh_flag == "1":
        logger.info("采集完成，开始执行采集后 Cookie 刷新...")
        try:
            refresh_cookies_with_udc()
        except RuntimeError as exc:
            logger.error("采集后刷新 Cookie 失败: %s", exc)
        except Exception as exc:
            logger.error("采集后刷新 Cookie 发生未知错误: %s", exc)


if __name__ == "__main__":
    main()
