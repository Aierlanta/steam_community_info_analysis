#!/usr/bin/env python3
"""
测试脚本：查看 Steam API 返回的原始数据
用于调试和验证数据结构
"""

import os
import json
import requests
from dotenv import load_dotenv
import toml

# 加载环境变量
load_dotenv()

def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.toml')
    with open(config_path, 'r', encoding='utf-8') as f:
        return toml.load(f)

def test_get_owned_games(api_key: str, steamid: str):
    """测试 GetOwnedGames API"""
    url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
    params = {
        'key': api_key,
        'steamid': steamid,
        'include_appinfo': 1,
        'include_played_free_games': 1,
        'format': 'json'
    }
    
    print(f"🔍 正在获取玩家 {steamid} 的游戏数据...")
    print(f"📡 API URL: {url}")
    print(f"📋 参数: steamid={steamid}, include_appinfo=1\n")
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    print("=" * 80)
    print("📦 完整的 API 响应数据：")
    print("=" * 80)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("\n" + "=" * 80)
    
    # 分析数据结构
    if 'response' in data:
        response_data = data['response']
        game_count = response_data.get('game_count', 0)
        games = response_data.get('games', [])
        
        print(f"\n✅ 成功获取数据！")
        print(f"📊 游戏总数: {game_count}")
        print(f"📝 返回的游戏列表长度: {len(games)}")
        
        if games:
            print(f"\n🎮 第一个游戏的数据示例：")
            print(json.dumps(games[0], indent=2, ensure_ascii=False))
            
            # 统计字段
            print(f"\n🔑 游戏对象包含的字段：")
            for key in games[0].keys():
                print(f"  - {key}")
            
            # 显示前 5 个游戏
            print(f"\n📋 前 5 个游戏列表：")
            for i, game in enumerate(games[:5], 1):
                name = game.get('name', f"Game {game['appid']}")
                playtime = game.get('playtime_forever', 0)
                print(f"  {i}. {name} (ID: {game['appid']}) - {playtime} 分钟")
        
        return response_data
    else:
        print("❌ API 返回格式异常")
        return None

def test_get_player_summary(api_key: str, steamid: str):
    """测试 GetPlayerSummaries API"""
    url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
    params = {
        'key': api_key,
        'steamids': steamid,
        'format': 'json'
    }
    
    print(f"\n🔍 正在获取玩家 {steamid} 的基本信息...")
    
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    
    print("\n" + "=" * 80)
    print("👤 玩家基本信息：")
    print("=" * 80)
    print(json.dumps(data, indent=2, ensure_ascii=False))
    print("=" * 80)
    
    if 'response' in data and 'players' in data['response']:
        player = data['response']['players'][0]
        print(f"\n✅ 玩家名称: {player.get('personaname', 'Unknown')}")
        print(f"📍 Steam ID: {player.get('steamid')}")
        print(f"🔗 个人主页: {player.get('profileurl', 'N/A')}")
        return player
    
    return None

def main():
    """主函数"""
    # 获取配置
    api_key = os.getenv('STEAM_API_KEY')
    if not api_key:
        print("❌ 错误：未配置 STEAM_API_KEY 环境变量")
        return
    
    config = load_config()
    players = config.get('steam', {}).get('players', [])
    
    if not players:
        print("❌ 错误：配置文件中未找到玩家信息")
        return
    
    player = players[0]
    steamid = player.get('steamid')
    
    if not steamid:
        print("❌ 错误：玩家配置缺少 steamid")
        return
    
    print("🎮 Steam API 数据测试工具")
    print("=" * 80)
    
    try:
        # 测试获取玩家信息
        test_get_player_summary(api_key, steamid)
        
        # 测试获取游戏数据
        print("\n" + "=" * 80 + "\n")
        games_data = test_get_owned_games(api_key, steamid)
        
        if games_data:
            # 保存到文件
            output_file = 'steam_api_sample.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(games_data, f, indent=2, ensure_ascii=False)
            print(f"\n💾 完整数据已保存到: {output_file}")
        
        print("\n✅ 测试完成！")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()

