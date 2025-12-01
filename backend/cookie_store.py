#!/usr/bin/env python3
"""
Steam Cookie 存储与加载工具

负责在不同来源之间统一管理 Steam Cookie：
- 优先从由外部工具维护的 Cookie 文件读取
- 如无 Cookie 文件，则回退到环境变量 STEAM_COOKIES
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _resolve_cookie_file_path(raw_path: str) -> str:
    """
    解析 Cookie 文件路径

    支持绝对路径和相对路径：
    - 绝对路径：直接使用
    - 相对路径：相对于 backend 目录解析
    """
    if os.path.isabs(raw_path):
        return raw_path

    backend_dir = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(backend_dir, raw_path))


def load_steam_cookies(
    env_var: str = "STEAM_COOKIES",
    file_env_var: str = "STEAM_COOKIES_FILE",
) -> Optional[str]:
    """
    加载 Steam Cookie 字符串

    优先级：
    1. 环境变量 STEAM_COOKIES_FILE 指定的文件内容
       文件内容为标准的 Cookie 头字符串：
       "sessionid=xxx; steamLoginSecure=xxx; ..."
    2. 环境变量 STEAM_COOKIES

    Returns:
        Cookie 字符串，若均不可用则返回 None
    """
    cookie_file_env = os.getenv(file_env_var)

    if cookie_file_env:
        cookie_file_path = _resolve_cookie_file_path(cookie_file_env)
        if os.path.exists(cookie_file_path):
            try:
                with open(cookie_file_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    logger.info(
                        "已从 Cookie 文件加载 Steam Cookie: %s",
                        cookie_file_path,
                    )
                    return content
                logger.warning("Cookie 文件存在但内容为空: %s", cookie_file_path)
            except Exception as exc:
                logger.error("读取 Cookie 文件失败: %s (%s)", cookie_file_path, exc)
        else:
            logger.warning("Cookie 文件不存在: %s", cookie_file_path)

    env_value = os.getenv(env_var)
    if env_value:
        logger.info("已从环境变量 %s 加载 Steam Cookie", env_var)
        return env_value.strip()

    logger.info("未配置 Steam Cookie（Cookie 文件和环境变量均不可用）")
    return None


def save_steam_cookies(
    cookie_string: str,
    file_env_var: str = "STEAM_COOKIES_FILE",
) -> Optional[str]:
    """
    将最新的 Steam Cookie 写入由环境变量指定的 Cookie 文件

    Args:
        cookie_string: 标准 Cookie 字符串
        file_env_var: 指定 Cookie 文件路径的环境变量名

    Returns:
        实际写入的文件路径；如未配置路径则返回 None
    """
    target_path_env = os.getenv(file_env_var)
    if not target_path_env:
        logger.error(
            "无法保存 Cookie：未配置环境变量 %s（请设置 Cookie 文件路径）",
            file_env_var,
        )
        return None

    target_path = _resolve_cookie_file_path(target_path_env)

    try:
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(cookie_string.strip())
        logger.info("已将最新 Steam Cookie 写入文件: %s", target_path)
        return target_path
    except Exception as exc:
        logger.error("写入 Cookie 文件失败: %s (%s)", target_path, exc)
        return None

