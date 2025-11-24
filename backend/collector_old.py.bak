#!/usr/bin/env python3
"""
Steam 游戏时长数据采集器
定时调用 Steam Web API 获取玩家游戏列表和游玩时间，存储到 PostgreSQL
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import requests
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv
import toml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SteamCollector:
    """Steam 游戏数据采集器"""
    
    STEAM_API_BASE = "https://api.steampowered.com"
    
    def __init__(self, api_key: str, db_url: str):
        """
        初始化采集器
        
        Args:
            api_key: Steam Web API Key
            db_url: PostgreSQL 数据库连接字符串
        """
        self.api_key = api_key
        self.db_url = db_url
        self.conn = None
        
    def connect_db(self):
        """连接数据库"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def close_db(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")
    
    def get_owned_games(self, steamid: str) -> Optional[Dict[str, Any]]:
        """
        调用 Steam API 获取玩家拥有的游戏
        
        Args:
            steamid: 玩家的 64 位 Steam ID
            
        Returns:
            API 返回的游戏数据，失败返回 None
        """
        url = f"{self.STEAM_API_BASE}/IPlayerService/GetOwnedGames/v1/"
        params = {
            'key': self.api_key,
            'steamid': steamid,
            'include_appinfo': 1,
            'include_played_free_games': 1,
            'format': 'json'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'response' in data:
                logger.info(f"成功获取玩家 {steamid} 的游戏数据")
                return data['response']
            else:
                logger.warning(f"API 返回数据格式异常: {data}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求失败: {e}")
            return None
    
    def get_player_summary(self, steamid: str) -> Optional[Dict[str, Any]]:
        """
        获取玩家基本信息（用户名等）
        
        Args:
            steamid: 玩家的 64 位 Steam ID
            
        Returns:
            玩家信息，失败返回 None
        """
        url = f"{self.STEAM_API_BASE}/ISteamUser/GetPlayerSummaries/v2/"
        params = {
            'key': self.api_key,
            'steamids': steamid,
            'format': 'json'
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if 'response' in data and 'players' in data['response'] and len(data['response']['players']) > 0:
                return data['response']['players'][0]
            else:
                logger.warning(f"无法获取玩家 {steamid} 的基本信息")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"获取玩家信息失败: {e}")
            return None
    
    def normalize_games_data(self, games: List[Dict[str, Any]]) -> str:
        """
        规范化游戏数据用于比较（只保留 appid 和 playtime_forever）
        
        Args:
            games: 游戏列表
            
        Returns:
            规范化后的 JSON 字符串
        """
        normalized = [
            {
                'appid': game['appid'],
                'playtime_forever': game.get('playtime_forever', 0)
            }
            for game in games
        ]
        # 按 appid 排序确保一致性
        normalized.sort(key=lambda x: x['appid'])
        return json.dumps(normalized, sort_keys=True)
    
    def get_last_snapshot(self, player_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定玩家的最后一次快照
        
        Args:
            player_id: 玩家 Steam ID
            
        Returns:
            最后一次快照数据，如果不存在返回 None
        """
        try:
            cursor = self.conn.cursor()
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
                return result[0]  # JSONB 字段直接返回为字典
            return None
            
        except Exception as e:
            logger.error(f"查询最后快照失败: {e}")
            return None
    
    def is_data_changed(self, old_data: Optional[Dict], new_data: Dict) -> bool:
        """
        比较两次快照数据是否有变化
        
        Args:
            old_data: 上次快照数据
            new_data: 本次快照数据
            
        Returns:
            True 表示数据有变化，False 表示无变化
        """
        if old_data is None:
            return True  # 第一次采集，必然保存
        
        # 比较游戏数量
        old_games = old_data.get('games', [])
        new_games = new_data.get('games', [])
        
        if len(old_games) != len(new_games):
            return True
        
        # 规范化后比较
        old_normalized = self.normalize_games_data(old_games)
        new_normalized = self.normalize_games_data(new_games)
        
        return old_normalized != new_normalized
    
    def save_snapshot(self, player_id: str, player_name: str, games_data: Dict[str, Any]) -> bool:
        """
        保存快照到数据库
        
        Args:
            player_id: 玩家 Steam ID
            player_name: 玩家名称
            games_data: 游戏数据
            
        Returns:
            保存成功返回 True，失败返回 False
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT INTO game_snapshots (player_id, player_name, snapshot_time, games_data)
                VALUES (%s, %s, %s, %s)
                """,
                (player_id, player_name, datetime.now(timezone.utc), Json(games_data))
            )
            self.conn.commit()
            cursor.close()
            logger.info(f"成功保存玩家 {player_id} 的快照")
            return True
            
        except Exception as e:
            logger.error(f"保存快照失败: {e}")
            self.conn.rollback()
            return False
    
    def collect_player_data(self, steamid: str, vanity_url: Optional[str] = None):
        """
        采集单个玩家的数据
        
        Args:
            steamid: 玩家的 Steam ID
            vanity_url: 玩家的个性化 URL（可选）
        """
        logger.info(f"开始采集玩家数据: {steamid}")
        
        # 获取游戏数据
        games_data = self.get_owned_games(steamid)
        if not games_data:
            logger.warning(f"无法获取玩家 {steamid} 的游戏数据，跳过")
            return
        
        # 获取玩家名称
        player_info = self.get_player_summary(steamid)
        player_name = player_info.get('personaname', vanity_url or steamid) if player_info else (vanity_url or steamid)
        
        # 检查数据是否有变化
        last_snapshot = self.get_last_snapshot(steamid)
        if not self.is_data_changed(last_snapshot, games_data):
            logger.info(f"玩家 {steamid} 的数据无变化，跳过保存")
            return
        
        # 保存快照
        self.save_snapshot(steamid, player_name, games_data)
        
        game_count = games_data.get('game_count', 0)
        logger.info(f"玩家 {player_name} ({steamid}) 拥有 {game_count} 个游戏")


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
    # 加载环境变量
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        logger.warning(".env 文件不存在，尝试从环境变量读取配置")
    
    # 获取配置
    api_key = os.getenv('STEAM_API_KEY')
    db_url = os.getenv('DATABASE_URL')
    
    if not api_key:
        logger.error("未配置 STEAM_API_KEY 环境变量")
        return
    
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
    
    # 初始化采集器
    collector = SteamCollector(api_key, db_url)
    
    try:
        # 连接数据库
        collector.connect_db()
        
        # 采集每个玩家的数据
        for player in players:
            steamid = player.get('steamid')
            vanity_url = player.get('vanity_url')
            
            if not steamid:
                logger.warning(f"玩家配置缺少 steamid: {player}")
                continue
            
            try:
                collector.collect_player_data(steamid, vanity_url)
            except Exception as e:
                logger.error(f"采集玩家 {steamid} 数据时出错: {e}")
                continue
        
        logger.info("数据采集完成")
        
    except Exception as e:
        logger.error(f"采集过程出错: {e}")
    finally:
        # 关闭数据库连接
        collector.close_db()


if __name__ == '__main__':
    main()

