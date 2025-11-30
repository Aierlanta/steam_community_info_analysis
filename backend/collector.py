#!/usr/bin/env python3
"""
Steam 游戏时长数据采集器 V2 - 基于网页爬虫
从 Steam 个人主页爬取"最新动态"的游戏数据
"""

import os
import sys
import json
import logging
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from dotenv import load_dotenv
import toml

from steam_scraper import SteamProfileScraper

# 配置日志 - 使用更精确的时间格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - [PID:%(process)d] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def generate_data_hash(games_data: List[Dict[str, Any]]) -> str:
    """
    生成游戏数据的哈希值，用于数据校验
    
    Args:
        games_data: 游戏数据列表
        
    Returns:
        数据哈希值
    """
    # 只对关键字段进行哈希
    key_data = []
    for game in games_data:
        key_data.append({
            'appid': game.get('appid'),
            'game_name': game.get('game_name'),
            'playtime_total': game.get('playtime_total')
        })
    
    data_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(data_str.encode()).hexdigest()[:8]


class SteamCollectorV2:
    """Steam 游戏数据采集器 V2 - 基于爬虫"""
    
    def __init__(self, db_url: str, steam_cookies: Optional[str] = None):
        """
        初始化采集器
        
        Args:
            db_url: PostgreSQL 数据库连接字符串
            steam_cookies: Steam Cookie 字符串（可选，用于访问好友可见的资料）
        """
        self.db_url = db_url
        self.scraper = SteamProfileScraper(cookies=steam_cookies)
        # conn 属性将在每个线程中独立创建
        self.conn: Optional[psycopg2.extensions.connection] = None

    def connect_db(self):
        """连接数据库"""
        if not self.conn or self.conn.closed:
            try:
                self.conn = psycopg2.connect(self.db_url)
                logger.info(f"[PID:{os.getpid()}] 数据库连接成功")
            except Exception as e:
                logger.error(f"[PID:{os.getpid()}] 数据库连接失败: {e}")
                raise
    
    def close_db(self):
        """关闭数据库连接"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info(f"[PID:{os.getpid()}] 数据库连接已关闭")
    
    def get_last_snapshot(self, player_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定玩家的最后一次快照
        
        Args:
            player_id: 玩家 Steam ID
            
        Returns:
            最后一次快照数据，如果不存在返回 None
        """
        try:
            assert self.conn is not None
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute(
                """
                SELECT games_data 
                FROM game_snapshots 
                WHERE player_id = %s 
                ORDER BY snapshot_time DESC 
                LIMIT 1
                """,
                (player_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                return result['games_data']
            return None
            
        except Exception as e:
            logger.error(f"查询最后快照失败: {e}")
            return None
    
    def is_data_changed(self, old_data: Optional[Dict], new_data: List[Dict]) -> bool:
        """
        比较两次快照数据是否有变化
        
        现在只关注最近3个游戏的总时数变化
        
        Args:
            old_data: 上次快照数据（完整的 games_data 对象）
            new_data: 本次爬取的游戏列表
            
        Returns:
            True 表示数据有变化，False 表示无变化
        """
        if old_data is None:
            return True  # 第一次采集，必然保存
        
        # 从旧数据中提取游戏列表
        old_games = old_data.get('recent_games', []) if isinstance(old_data, dict) else []
        
        if len(old_games) != len(new_data):
            return True
        
        # 比较每个游戏的总时数
        # 创建字典方便查找
        old_games_dict = {game['appid']: game for game in old_games}
        
        for new_game in new_data:
            appid = new_game.get('appid')
            if not appid:
                continue
            
            old_game = old_games_dict.get(appid)
            if not old_game:
                # 新增游戏
                return True
            
            # 比较总时数（允许小误差，防止浮点数问题）
            old_time = old_game.get('playtime_total', 0)
            new_time = new_game.get('playtime_total', 0)
            
            if abs(old_time - new_time) > 0.01:  # 差异超过0.01小时才算变化
                return True
        
        return False
    
    def save_snapshot(self, player_id: str, player_name: str, games_data: List[Dict[str, Any]]) -> bool:
        """
        保存快照到数据库
        
        Args:
            player_id: 玩家 Steam ID
            player_name: 玩家名称
            games_data: 游戏列表（最近3个游戏）
            
        Returns:
            保存成功返回 True，失败返回 False
        """
        try:
            assert self.conn is not None
            cursor = self.conn.cursor()
            
            # 构造要保存的数据结构
            snapshot_data = {
                'data_source': 'web_scraper',  # 标记数据来源
                'game_count': len(games_data),
                'recent_games': games_data  # 最近玩过的游戏
            }
            
            cursor.execute(
                """
                INSERT INTO game_snapshots (player_id, player_name, snapshot_time, games_data)
                VALUES (%s, %s, %s, %s)
                """,
                (player_id, player_name, datetime.now(timezone.utc), Json(snapshot_data))
            )
            self.conn.commit()
            cursor.close()
            logger.info(f"成功保存玩家 {player_id} 的快照（{len(games_data)} 个游戏）")
            return True
            
        except Exception as e:
            logger.error(f"保存快照失败: {e}")
            if self.conn:
                self.conn.rollback()
            return False
    
    def collect_player_data(self, steamid: str, vanity_url: Optional[str] = None) -> Optional[str]:
        """
        采集单个玩家的数据（线程安全）
        
        Args:
            steamid: 玩家的 Steam ID
            vanity_url: 玩家的个性化 URL（可选）
        
        Returns:
            成功时返回 Steam ID, 失败时返回 None
        """
        try:
            self.connect_db()  # 每个线程独立的数据库连接
            logger.info(f"========== 开始采集玩家 {steamid} ==========")
            
            # 爬取游戏数据
            logger.info(f"[{steamid}] 正在爬取游戏数据...")
            games_data = self.scraper.scrape_recent_games(steamid, vanity_url)
            
            if not games_data:
                logger.warning(f"[{steamid}] 无法获取游戏数据，可能是账号私密或网络问题")
                logger.info(f"========== 完成采集玩家 {steamid} (无数据) ==========")
                return steamid # 标记为处理完成
            
            # 计算数据哈希，用于追踪
            data_hash = generate_data_hash(games_data)
            logger.info(f"[{steamid}] 爬取到 {len(games_data)} 个游戏，数据哈希: {data_hash}")
            
            # 打印详细的游戏列表（用于调试）
            for i, game in enumerate(games_data, 1):
                logger.info(f"[{steamid}] 游戏{i}: {game.get('game_name')} - {game.get('playtime_total', 0)}h (appid: {game.get('appid')})")
            
            # 获取玩家名称
            logger.info(f"[{steamid}] 正在获取玩家名称...")
            player_name = self.scraper.get_player_name(steamid, vanity_url)
            if not player_name:
                player_name = vanity_url or steamid
            logger.info(f"[{steamid}] 玩家名称: {player_name}")
            
            # 检查数据是否有变化
            logger.info(f"[{steamid}] 正在检查数据变化...")
            last_snapshot = self.get_last_snapshot(steamid)
            if not self.is_data_changed(last_snapshot, games_data):
                logger.info(f"[{steamid}] 数据无变化，跳过保存")
                logger.info(f"========== 完成采集玩家 {steamid} (无变化) ==========")
                return steamid
            
            # 保存快照前再次确认数据一致性
            save_hash = generate_data_hash(games_data)
            if save_hash != data_hash:
                logger.error(f"[{steamid}] 数据一致性校验失败！爬取哈希: {data_hash}, 保存哈希: {save_hash}")
                logger.info(f"========== 完成采集玩家 {steamid} (校验失败) ==========")
                return steamid

            # 保存快照
            logger.info(f"[{steamid}] 正在保存快照...")
            success = self.save_snapshot(steamid, player_name, games_data)
            
            if success:
                logger.info(f"[{steamid}] 快照保存成功，数据哈希: {data_hash}")
            else:
                logger.error(f"[{steamid}] 快照保存失败")
            
            logger.info(f"========== 完成采集玩家 {steamid} ==========")
            return steamid
            
        except Exception as e:
            logger.error(f"采集玩家 {steamid} 数据时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            self.close_db() # 确保每个线程的连接都被关闭


def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.toml')
    if not os.path.exists(config_path):
        logger.error(f"配置文件不存在: {config_path}")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = toml.load(f)
        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return None


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("Steam 数据采集器启动")
    logger.info("=" * 60)
    
    # 加载环境变量
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        logger.warning(".env 文件不存在，尝试从环境变量读取配置")
    
    # 获取配置
    db_url = os.getenv('DATABASE_URL')
    steam_cookies = os.getenv('STEAM_COOKIES')  # 从环境变量读取 Cookie（可选）
    
    if not db_url:
        logger.error("未配置 DATABASE_URL 环境变量")
        return
    
    # 加载玩家配置
    config = load_config()
    if not config:
        return
    
    players = config.get('steam', {}).get('players', [])
    if not players:
        logger.error("配置文件中未找到玩家信息")
        return
    
    logger.info(f"配置加载完成，共 {len(players)} 个玩家")
    
    # 使用文件锁防止并发执行
    # Windows 不支持 fcntl，使用简单的锁文件方案
    lock_path = os.path.join(os.path.dirname(__file__), '.collector.lock')
    
    # 检查是否有其他实例在运行
    if os.path.exists(lock_path):
        try:
            with open(lock_path, 'r') as f:
                lock_info = f.read()
            logger.warning(f"发现锁文件，可能有另一个任务在运行: {lock_info}")
            # 检查锁文件是否过期（超过 5 分钟视为过期）
            lock_mtime = os.path.getmtime(lock_path)
            if datetime.now().timestamp() - lock_mtime > 300:
                logger.warning("锁文件已过期，删除并继续执行")
                os.remove(lock_path)
            else:
                logger.error("另一个采集任务正在运行，退出")
                return
        except Exception as e:
            logger.warning(f"检查锁文件时出错: {e}")
    
    # 创建锁文件
    try:
        with open(lock_path, 'w') as f:
            f.write(f"PID: {os.getpid()}, 启动时间: {datetime.now().isoformat()}")
        logger.info(f"创建锁文件: {lock_path}")
    except Exception as e:
        logger.error(f"创建锁文件失败: {e}")
        return
    
    # 初始化一个 collector 实例，用于验证 cookie
    # 这个实例不会用于并发采集，避免共享 scraper session
    main_collector = SteamCollectorV2(db_url, steam_cookies)

    # 验证 Cookie 有效性
    if steam_cookies:
        if not main_collector.scraper.verify_cookies():
            logger.critical("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.critical("!!! Steam Cookie 已失效，请立即更新 .env 文件 !!!")
            logger.critical("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            try:
                if os.path.exists(lock_path):
                    os.remove(lock_path)
            except Exception as e:
                logger.warning(f"删除锁文件失败: {e}")
            return

    # 设置并发数，默认为 4
    max_workers = config.get('steam', {}).get('max_workers', 4)
    logger.info(f"使用 {max_workers} 个线程进行并发采集")

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 为每个线程创建一个独立的 collector 实例
            futures = {
                executor.submit(
                    SteamCollectorV2(db_url, steam_cookies).collect_player_data,
                    player.get('steamid'),
                    player.get('vanity_url')
                ): player
                for player in players if player.get('steamid')
            }
            
            success_count = 0
            fail_count = 0
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    success_count += 1
                else:
                    fail_count += 1
                
                player_info = futures[future]
                logger.info(f"玩家 {player_info.get('steamid')} 处理完成，结果: {'成功' if result else '失败'}")
        
        logger.info("=" * 60)
        logger.info(f"数据采集完成: {success_count} 个成功, {fail_count} 个失败")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"并发采集过程出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 删除锁文件
        try:
            if os.path.exists(lock_path):
                os.remove(lock_path)
                logger.info("已删除锁文件")
        except Exception as e:
            logger.warning(f"删除锁文件失败: {e}")


if __name__ == '__main__':
    main()

