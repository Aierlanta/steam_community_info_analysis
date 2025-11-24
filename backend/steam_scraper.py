#!/usr/bin/env python3
"""
Steam 个人主页爬虫
从 Steam 个人主页获取最新游戏动态
"""

import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class SteamProfileScraper:
    """Steam 个人主页爬虫"""
    
    def __init__(self, cookies: Optional[str] = None):
        """
        初始化爬虫
        
        Args:
            cookies: Steam Cookie 字符串（可选）
                    格式："sessionid=xxx; steamLoginSecure=xxx; ..."
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        })
        
        # 如果提供了 Cookie，添加到 session
        if cookies:
            self._set_cookies(cookies)
            logger.info("已设置 Steam Cookie，可以访问好友可见的资料")
        
        # 设置超时和重试
        self.timeout = 30
        self.max_retries = 3
    
    def _set_cookies(self, cookie_string: str):
        """
        设置 Cookie
        
        Args:
            cookie_string: Cookie 字符串
                格式："sessionid=xxx; steamLoginSecure=xxx; ..."
        """
        # 解析 Cookie 字符串
        cookies = {}
        for item in cookie_string.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                cookies[key.strip()] = value.strip()
        
        # 设置到 session
        for key, value in cookies.items():
            self.session.cookies.set(key, value, domain='.steamcommunity.com')
        
        logger.debug(f"设置了 {len(cookies)} 个 Cookie")
    
    def get_profile_url(self, steamid: str, vanity_url: Optional[str] = None) -> str:
        """
        获取个人主页 URL
        
        Args:
            steamid: 64位 Steam ID
            vanity_url: 个性化 URL（可选）
            
        Returns:
            完整的个人主页 URL
        """
        if vanity_url:
            return f"https://steamcommunity.com/id/{vanity_url}/"
        else:
            return f"https://steamcommunity.com/profiles/{steamid}/"
    
    def parse_playtime(self, text: str) -> Optional[float]:
        """
        解析游戏时长文本
        
        支持格式：
        - "130.8 小时（过去 2 周）"
        - "总时数 60 小时"
        - "1,409 小时"
        - "60 小时"
        
        Args:
            text: 时长文本
            
        Returns:
            时长（小时），失败返回 None
        """
        if not text:
            return None
        
        # 移除逗号
        text = text.replace(',', '')
        
        # 匹配数字（整数或小数）
        match = re.search(r'([\d\.]+)\s*小时', text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        
        return None
    
    def parse_date(self, text: str) -> Optional[str]:
        """
        解析日期文本
        
        支持格式：
        - "最后运行日期：11 月 24 日"
        - "11 月 24 日"
        
        Args:
            text: 日期文本
            
        Returns:
            格式化日期字符串 "MM月DD日"，失败返回 None
        """
        if not text:
            return None
        
        # 提取月日
        match = re.search(r'(\d+)\s*月\s*(\d+)\s*日', text)
        if match:
            month = match.group(1)
            day = match.group(2)
            return f"{month}月{day}日"
        
        return None
    
    def scrape_recent_games(self, steamid: str, vanity_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        爬取个人主页的最新游戏动态
        
        Args:
            steamid: 64位 Steam ID
            vanity_url: 个性化 URL（可选）
            
        Returns:
            游戏列表，每个游戏包含：
            - game_name: 游戏名称
            - appid: 游戏ID（如果能获取）
            - playtime_recent: 最近2周时长（小时）
            - playtime_total: 总时长（小时）
            - last_played: 最后运行日期
            - achievements: 成就进度（如 "19 / 52"）
        """
        url = self.get_profile_url(steamid, vanity_url)
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                logger.info(f"正在爬取个人主页: {url} (尝试 {attempt + 1}/{self.max_retries})")
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                response.raise_for_status()
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"爬取个人主页失败（已重试{self.max_retries}次）: {e}")
                    return []
                logger.warning(f"连接失败，{2}秒后重试...")
                import time
                time.sleep(2)
        else:
            return []
        
        try:
            
            # 检查是否为私密账号
            if '此用户尚未设置他们的个人资料为公开' in response.text or 'private' in response.text.lower():
                logger.warning(f"账号 {steamid} 的个人资料为私密")
                return []
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找最新动态区域
            games = []
            
            # 方法1：查找 recent_games 区域
            recent_games_div = soup.find('div', {'class': 'recent_games'})
            if recent_games_div:
                game_divs = recent_games_div.find_all('div', {'class': 'recent_game'})
                
                for game_div in game_divs:
                    game_data = self._parse_game_div(game_div)
                    if game_data:
                        games.append(game_data)
            
            # 方法2：如果方法1失败，尝试查找 game_info_details
            if not games:
                game_details = soup.find_all('div', {'class': 'game_info_details'})
                for detail in game_details:
                    game_data = self._parse_game_detail(detail)
                    if game_data:
                        games.append(game_data)
            
            logger.info(f"成功爬取到 {len(games)} 个最新游戏")
            return games
            
        except requests.exceptions.RequestException as e:
            logger.error(f"爬取个人主页失败: {e}")
            return []
        except Exception as e:
            logger.error(f"解析个人主页数据失败: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _parse_game_div(self, game_div) -> Optional[Dict[str, Any]]:
        """解析单个游戏 div"""
        try:
            game_data = {}
            
            # 获取游戏名称和 AppID
            game_name_elem = game_div.find('div', {'class': 'game_name'})
            if game_name_elem:
                game_link = game_name_elem.find('a')
                if game_link:
                    game_data['game_name'] = game_link.text.strip()
                    # 从链接提取 appid
                    href = game_link.get('href', '')
                    appid_match = re.search(r'/app/(\d+)', href)
                    if appid_match:
                        game_data['appid'] = int(appid_match.group(1))
                else:
                    game_data['game_name'] = game_name_elem.text.strip()
            
            if not game_data.get('game_name'):
                return None
            
            # 获取游戏时长信息从 game_info_details
            game_info_details = game_div.find('div', {'class': 'game_info_details'})
            if game_info_details:
                details_text = game_info_details.get_text()
                
                # 解析总时长 - 格式：总时数 722 小时
                total_match = re.search(r'总时数\s*([\d,\.]+)\s*小时', details_text)
                if total_match:
                    playtime_str = total_match.group(1).replace(',', '')
                    game_data['playtime_total'] = float(playtime_str)
                
                # 解析最后运行日期 - 格式：最后运行日期：11 月 23 日
                date_match = re.search(r'最后运行日期[：:]\s*(\d+)\s*月\s*(\d+)\s*日', details_text)
                if date_match:
                    game_data['last_played'] = f"{date_match.group(1)}月{date_match.group(2)}日"
            
            # 解析成就进度
            achievement_summary = game_div.find('span', {'class': 'game_info_achievement_summary'})
            if achievement_summary:
                achievement_text = achievement_summary.get_text()
                # 格式：1 / 1 或 成就进度 1 / 1
                ach_match = re.search(r'(\d+)\s*/\s*(\d+)', achievement_text)
                if ach_match:
                    game_data['achievements'] = f"{ach_match.group(1)} / {ach_match.group(2)}"
                    game_data['achievements_unlocked'] = int(ach_match.group(1))
                    game_data['achievements_total'] = int(ach_match.group(2))
            
            # 设置默认值
            game_data.setdefault('playtime_total', 0)
            
            return game_data
            
        except Exception as e:
            logger.error(f"解析游戏 div 失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_game_detail(self, detail_div) -> Optional[Dict[str, Any]]:
        """解析 game_info_details 格式"""
        try:
            game_data = {}
            
            # 查找游戏名称
            title = detail_div.find('div', {'class': 'game_info_title'})
            if title:
                game_data['game_name'] = title.text.strip()
            
            # 查找时长信息
            hours = detail_div.find_all('div', {'class': 'game_info_hours'})
            for hour_div in hours:
                text = hour_div.get_text()
                if '过去 2 周' in text or '过去2周' in text:
                    game_data['playtime_recent'] = self.parse_playtime(text)
                elif '总时数' in text or '小时' in text:
                    game_data['playtime_total'] = self.parse_playtime(text)
            
            if game_data.get('game_name'):
                game_data.setdefault('playtime_total', 0)
                return game_data
            
            return None
            
        except Exception as e:
            logger.error(f"解析 game_detail 失败: {e}")
            return None
    
    def get_player_name(self, steamid: str, vanity_url: Optional[str] = None) -> Optional[str]:
        """
        获取玩家名称
        
        Args:
            steamid: 64位 Steam ID
            vanity_url: 个性化 URL（可选）
            
        Returns:
            玩家名称，失败返回 None
        """
        url = self.get_profile_url(steamid, vanity_url)
        
        # 重试机制
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                response.raise_for_status()
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"获取玩家名称失败: {e}")
                    return None
                import time
                time.sleep(2)
        else:
            return None
        
        try:
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找玩家名称
            profile_name = soup.find('span', {'class': 'actual_persona_name'})
            if profile_name:
                return profile_name.text.strip()
            
            # 备用方法：从标题提取
            title = soup.find('title')
            if title:
                # 标题格式通常是 "Steam 社区 :: 玩家名"
                title_text = title.text.strip()
                if '::' in title_text:
                    return title_text.split('::')[-1].strip()
            
            return None
            
        except Exception as e:
            logger.error(f"获取玩家名称失败: {e}")
            return None


def test_scraper(save_html=False):
    """测试爬虫功能"""
    scraper = SteamProfileScraper()
    
    # 测试用例 - 使用你的账号
    test_steamid = "76561198958724637"
    test_vanity = "morbisol"
    
    print(f"测试爬取 Steam ID: {test_steamid}")
    print("=" * 80)
    
    # 获取玩家名称
    player_name = scraper.get_player_name(test_steamid, test_vanity)
    print(f"玩家名称: {player_name}")
    print()
    
    # 如果需要保存 HTML 用于调试
    if save_html:
        url = scraper.get_profile_url(test_steamid, test_vanity)
        try:
            response = scraper.session.get(url, timeout=scraper.timeout, allow_redirects=True)
            with open('steam_profile_debug.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("HTML 已保存到 steam_profile_debug.html")
            print()
            
            # 打印 HTML 片段以调试
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找可能包含游戏信息的元素
            print("查找可能的游戏容器...")
            print()
            
            # 方法1: recent_games
            recent_games_div = soup.find('div', {'class': 'recent_games'})
            if recent_games_div:
                print("✅ 找到 recent_games div")
                game_divs = recent_games_div.find_all('div', {'class': 'recent_game'})
                print(f"   包含 {len(game_divs)} 个 recent_game")
            else:
                print("❌ 未找到 recent_games div")
            
            # 方法2: game_info
            game_info_divs = soup.find_all('div', {'class': 'game_info'})
            print(f"找到 {len(game_info_divs)} 个 game_info div")
            
            # 方法3: 查找包含"小时"的所有元素
            hour_texts = soup.find_all(string=re.compile(r'小时'))
            print(f"找到 {len(hour_texts)} 个包含'小时'的文本")
            if hour_texts:
                print("前5个示例:")
                for i, text in enumerate(hour_texts[:5], 1):
                    print(f"  {i}. {text.strip()}")
            
            print()
        except Exception as e:
            print(f"保存HTML失败: {e}")
            print()
    
    # 获取最新游戏
    games = scraper.scrape_recent_games(test_steamid, test_vanity)
    
    if games:
        print(f"找到 {len(games)} 个最新游戏:")
        print()
        for i, game in enumerate(games, 1):
            print(f"{i}. {game['game_name']}")
            if game.get('appid'):
                print(f"   游戏ID: {game['appid']}")
            if game.get('playtime_recent'):
                print(f"   过去2周: {game['playtime_recent']} 小时")
            if game.get('playtime_total'):
                print(f"   总时数: {game['playtime_total']} 小时")
            if game.get('last_played'):
                print(f"   最后运行: {game['last_played']}")
            if game.get('achievements'):
                print(f"   成就: {game['achievements']}")
            print()
    else:
        print("未找到游戏数据")
        print("提示：运行 `python steam_scraper.py --debug` 保存 HTML 用于调试")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    test_scraper()

