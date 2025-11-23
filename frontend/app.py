#!/usr/bin/env python3
"""
Steam 游戏时长可视化分析前端
使用 FastAPI + Plotly 展示玩家游戏时长推断和统计分析
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 创建 FastAPI 应用
app = FastAPI(
    title="Steam 游戏时长追踪系统",
    description="基于快照推断的 Steam 游戏时长可视化分析",
    version="1.0.0"
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 初始化模板
templates = Jinja2Templates(directory="templates")


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    def get_connection(self):
        """获取数据库连接"""
        return psycopg2.connect(self.db_url)
    
    def get_all_players(self) -> List[Dict[str, Any]]:
        """获取所有已记录的玩家列表"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT DISTINCT player_id, player_name,
                       COUNT(*) as snapshot_count,
                       MIN(snapshot_time) as first_snapshot,
                       MAX(snapshot_time) as last_snapshot
                FROM game_snapshots
                GROUP BY player_id, player_name
                ORDER BY last_snapshot DESC
            """)
            
            players = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [dict(p) for p in players]
            
        except Exception as e:
            logger.error(f"获取玩家列表失败: {e}")
            return []
    
    def get_player_snapshots(self, player_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取指定玩家最近 N 天的快照
        
        Args:
            player_id: 玩家 Steam ID
            days: 查询天数
            
        Returns:
            快照列表
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            since_time = datetime.now() - timedelta(days=days)
            
            cursor.execute("""
                SELECT id, player_id, player_name, snapshot_time, games_data
                FROM game_snapshots
                WHERE player_id = %s AND snapshot_time >= %s
                ORDER BY snapshot_time ASC
            """, (player_id, since_time))
            
            snapshots = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return [dict(s) for s in snapshots]
            
        except Exception as e:
            logger.error(f"获取快照失败: {e}")
            return []


class GameplayAnalyzer:
    """游戏时长分析器"""
    
    @staticmethod
    def calculate_playtime_changes(snapshots: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        计算相邻快照之间的游戏时长增量
        
        Args:
            snapshots: 按时间排序的快照列表
            
        Returns:
            游玩记录列表，每条记录包含：
            - game_name: 游戏名称
            - game_id: 游戏 ID
            - start_time: 推断的开始时间（上一个快照时间）
            - end_time: 推断的结束时间（当前快照时间）
            - playtime_increase: 时长增加（分钟）
        """
        if len(snapshots) < 2:
            return []
        
        gameplay_records = []
        
        for i in range(1, len(snapshots)):
            prev_snapshot = snapshots[i - 1]
            curr_snapshot = snapshots[i]
            
            prev_games = {
                game['appid']: game 
                for game in prev_snapshot['games_data'].get('games', [])
            }
            curr_games = {
                game['appid']: game 
                for game in curr_snapshot['games_data'].get('games', [])
            }
            
            # 比较每个游戏的时长
            for appid, curr_game in curr_games.items():
                curr_playtime = curr_game.get('playtime_forever', 0)
                prev_playtime = prev_games.get(appid, {}).get('playtime_forever', 0)
                
                playtime_increase = curr_playtime - prev_playtime
                
                # 只记录有增长的游戏
                if playtime_increase > 0:
                    gameplay_records.append({
                        'game_id': appid,
                        'game_name': curr_game.get('name', f'Game {appid}'),
                        'start_time': prev_snapshot['snapshot_time'],
                        'end_time': curr_snapshot['snapshot_time'],
                        'playtime_increase': playtime_increase,
                        'total_playtime': curr_playtime
                    })
        
        return gameplay_records
    
    @staticmethod
    def aggregate_by_game(gameplay_records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        按游戏聚合总游玩时长
        
        Args:
            gameplay_records: 游玩记录列表
            
        Returns:
            游戏名称 -> 总时长增量（分钟）的字典
        """
        game_totals = {}
        for record in gameplay_records:
            game_name = record['game_name']
            playtime = record['playtime_increase']
            game_totals[game_name] = game_totals.get(game_name, 0) + playtime
        
        return game_totals
    
    @staticmethod
    def aggregate_by_hour(gameplay_records: List[Dict[str, Any]]) -> Dict[int, int]:
        """
        按小时统计游玩活跃度
        
        Args:
            gameplay_records: 游玩记录列表
            
        Returns:
            小时 (0-23) -> 游玩次数的字典
        """
        hour_activity = {h: 0 for h in range(24)}
        
        for record in gameplay_records:
            start_hour = record['start_time'].hour
            end_hour = record['end_time'].hour
            
            # 简化处理：标记开始和结束时间的小时
            hour_activity[start_hour] += 1
            if start_hour != end_hour:
                hour_activity[end_hour] += 1
        
        return hour_activity


class PlotlyVisualizer:
    """Plotly 可视化生成器"""
    
    @staticmethod
    def create_gantt_chart(gameplay_records: List[Dict[str, Any]]) -> go.Figure:
        """
        创建甘特图展示游玩时间轴
        
        Args:
            gameplay_records: 游玩记录列表
            
        Returns:
            Plotly Figure 对象
        """
        if not gameplay_records:
            # 空数据时返回占位图
            fig = go.Figure()
            fig.add_annotation(
                text="暂无游玩记录",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20)
            )
            return fig
        
        # 准备数据
        df = pd.DataFrame(gameplay_records)
        
        # 创建甘特图
        fig = go.Figure()
        
        # 按游戏分组
        games = df['game_name'].unique()
        colors = PlotlyVisualizer._generate_colors(len(games))
        game_colors = {game: colors[i] for i, game in enumerate(games)}
        
        for _, record in df.iterrows():
            fig.add_trace(go.Bar(
                name=record['game_name'],
                x=[record['end_time'] - record['start_time']],
                y=[record['game_name']],
                base=record['start_time'],
                orientation='h',
                marker=dict(color=game_colors[record['game_name']]),
                hovertemplate=(
                    f"<b>{record['game_name']}</b><br>"
                    f"开始: {record['start_time'].strftime('%Y-%m-%d %H:%M')}<br>"
                    f"结束: {record['end_time'].strftime('%Y-%m-%d %H:%M')}<br>"
                    f"时长增加: {record['playtime_increase']} 分钟<br>"
                    "<extra></extra>"
                ),
                showlegend=False
            ))
        
        fig.update_layout(
            title="游戏时长推断时间轴（甘特图）",
            xaxis_title="时间",
            yaxis_title="游戏",
            height=max(400, len(games) * 40),
            hovermode='closest',
            xaxis=dict(type='date', gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8fafc'),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return fig
    
    @staticmethod
    def create_pie_chart(game_totals: Dict[str, int]) -> go.Figure:
        """
        创建饼图展示游戏时长分布
        
        Args:
            game_totals: 游戏名称 -> 总时长的字典
            
        Returns:
            Plotly Figure 对象
        """
        if not game_totals:
            fig = go.Figure()
            fig.add_annotation(
                text="暂无数据",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20)
            )
            return fig
        
        # 排序并取前 10
        sorted_games = sorted(game_totals.items(), key=lambda x: x[1], reverse=True)
        top_games = sorted_games[:10]
        
        if len(sorted_games) > 10:
            other_total = sum(t for _, t in sorted_games[10:])
            top_games.append(("其他", other_total))
        
        labels = [game for game, _ in top_games]
        values = [time for _, time in top_games]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hovertemplate="<b>%{label}</b><br>时长: %{value} 分钟<br>占比: %{percent}<extra></extra>"
        )])
        
        fig.update_layout(
            title="游戏时长分布（分钟）",
            height=500,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8fafc'),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return fig
    
    @staticmethod
    def create_bar_chart(game_totals: Dict[str, int]) -> go.Figure:
        """
        创建柱状图展示游戏时长排名
        
        Args:
            game_totals: 游戏名称 -> 总时长的字典
            
        Returns:
            Plotly Figure 对象
        """
        if not game_totals:
            fig = go.Figure()
            fig.add_annotation(
                text="暂无数据",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=20)
            )
            return fig
        
        # 排序
        sorted_games = sorted(game_totals.items(), key=lambda x: x[1], reverse=True)[:15]
        games = [game for game, _ in sorted_games]
        times = [time for _, time in sorted_games]
        
        fig = go.Figure(data=[go.Bar(
            x=times,
            y=games,
            orientation='h',
            marker=dict(color=times, colorscale='Viridis'),
            hovertemplate="<b>%{y}</b><br>时长: %{x} 分钟<extra></extra>"
        )])
        
        fig.update_layout(
            title="游戏时长排名 Top 15（分钟）",
            xaxis_title="时长（分钟）",
            yaxis_title="游戏",
            height=max(400, len(games) * 30),
            yaxis=dict(autorange="reversed", gridcolor='rgba(255,255,255,0.1)'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8fafc'),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return fig
    
    @staticmethod
    def create_heatmap(hour_activity: Dict[int, int]) -> go.Figure:
        """
        创建热力图展示按小时的游玩活跃度
        
        Args:
            hour_activity: 小时 -> 活跃度的字典
            
        Returns:
            Plotly Figure 对象
        """
        hours = list(range(24))
        activities = [hour_activity.get(h, 0) for h in hours]
        
        fig = go.Figure(data=go.Bar(
            x=[f"{h:02d}:00" for h in hours],
            y=activities,
            marker=dict(color=activities, colorscale='Blues'),
            hovertemplate="<b>%{x}</b><br>活跃次数: %{y}<extra></extra>"
        ))
        
        fig.update_layout(
            title="游玩活跃度热力图（按小时）",
            xaxis_title="时间（小时）",
            yaxis_title="活跃次数",
            height=400,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#f8fafc'),
            xaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(gridcolor='rgba(255,255,255,0.1)'),
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return fig
    
    @staticmethod
    def _generate_colors(n: int) -> List[str]:
        """生成 N 种不同的颜色"""
        import colorsys
        colors = []
        for i in range(n):
            hue = i / n
            rgb = colorsys.hsv_to_rgb(hue, 0.7, 0.9)
            colors.append(f"rgb({int(rgb[0]*255)},{int(rgb[1]*255)},{int(rgb[2]*255)})")
        return colors
    


# 初始化数据库管理器
db_url = os.getenv('DATABASE_URL')
if not db_url:
    logger.error("未配置 DATABASE_URL 环境变量")
    db_manager = None
else:
    # 打印数据库连接信息（隐藏密码）
    masked_url = db_url.split('@')[1] if '@' in db_url else 'unknown'
    logger.info(f"正在连接数据库: {masked_url}")
    db_manager = DatabaseManager(db_url)
    logger.info("数据库管理器初始化完成")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页 - 显示玩家列表"""
    if not db_manager:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "players": [],
            "error": "未配置数据库连接"
        })
    
    players = db_manager.get_all_players()
    logger.info(f"查询到 {len(players)} 个玩家")
    return templates.TemplateResponse("index.html", {"request": request, "players": players})


@app.get("/player/{player_id}", response_class=HTMLResponse)
async def player_dashboard(
    request: Request,
    player_id: str,
    days: int = Query(default=7, ge=1, le=30, description="统计天数")
):
    """玩家数据分析页面"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="数据库未配置")
    
    # 获取快照数据
    snapshots = db_manager.get_player_snapshots(player_id, days)
    
    if not snapshots:
        return templates.TemplateResponse("error.html", {
            "request": request,
            "title": "未找到玩家数据",
            "message": f"无法找到玩家 ID {player_id} 的快照数据，请确认后端采集器是否已运行。"
        })
    
    player_name = snapshots[0]['player_name']
    
    # 分析数据
    analyzer = GameplayAnalyzer()
    gameplay_records = analyzer.calculate_playtime_changes(snapshots)
    game_totals = analyzer.aggregate_by_game(gameplay_records)
    hour_activity = analyzer.aggregate_by_hour(gameplay_records)
    
    # 生成图表
    visualizer = PlotlyVisualizer()
    gantt_fig = visualizer.create_gantt_chart(gameplay_records)
    pie_fig = visualizer.create_pie_chart(game_totals)
    bar_fig = visualizer.create_bar_chart(game_totals)
    heatmap_fig = visualizer.create_heatmap(hour_activity)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "player_name": player_name,
        "days": days,
        "gantt_chart": gantt_fig.to_html(full_html=False, include_plotlyjs=False),
        "pie_chart": pie_fig.to_html(full_html=False, include_plotlyjs=False),
        "bar_chart": bar_fig.to_html(full_html=False, include_plotlyjs=False),
        "heatmap_chart": heatmap_fig.to_html(full_html=False, include_plotlyjs=False)
    })


@app.get("/api/players")
async def api_get_players():
    """API: 获取所有玩家列表"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="数据库未配置")
    
    players = db_manager.get_all_players()
    return {"players": players}


@app.get("/api/debug/status")
async def debug_status():
    """调试接口：查看当前数据库连接状态和数据概况"""
    if not db_manager:
        return {
            "status": "error",
            "message": "数据库未配置",
            "db_url": "未设置 DATABASE_URL"
        }
    
    try:
        # 获取数据库连接信息（隐藏密码）
        db_url = os.getenv('DATABASE_URL', '')
        masked_url = db_url.split('@')[1] if '@' in db_url else 'unknown'
        
        # 查询数据
        players = db_manager.get_all_players()
        
        # 获取总快照数
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM game_snapshots")
        total_snapshots = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return {
            "status": "ok",
            "db_host": masked_url,
            "total_players": len(players),
            "total_snapshots": total_snapshots,
            "players": [
                {
                    "player_id": p['player_id'],
                    "player_name": p['player_name'],
                    "snapshot_count": p['snapshot_count']
                } for p in players
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "db_host": masked_url if 'masked_url' in locals() else 'unknown'
        }


@app.get("/api/snapshots/{player_id}")
async def api_get_snapshots(
    player_id: str,
    days: int = Query(default=7, ge=1, le=30)
):
    """API: 获取玩家快照数据"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="数据库未配置")
    
    snapshots = db_manager.get_player_snapshots(player_id, days)
    
    # 转换 datetime 为字符串
    for snapshot in snapshots:
        snapshot['snapshot_time'] = snapshot['snapshot_time'].isoformat()
    
    return {"snapshots": snapshots}


@app.get("/api/analysis/{player_id}")
async def api_get_analysis(
    player_id: str,
    days: int = Query(default=7, ge=1, le=30)
):
    """API: 获取玩家游戏时长分析数据"""
    if not db_manager:
        raise HTTPException(status_code=500, detail="数据库未配置")
    
    snapshots = db_manager.get_player_snapshots(player_id, days)
    
    if not snapshots:
        raise HTTPException(status_code=404, detail="未找到玩家数据")
    
    analyzer = GameplayAnalyzer()
    gameplay_records = analyzer.calculate_playtime_changes(snapshots)
    game_totals = analyzer.aggregate_by_game(gameplay_records)
    hour_activity = analyzer.aggregate_by_hour(gameplay_records)
    
    # 转换 datetime 为字符串
    for record in gameplay_records:
        record['start_time'] = record['start_time'].isoformat()
        record['end_time'] = record['end_time'].isoformat()
    
    return {
        "player_id": player_id,
        "player_name": snapshots[0]['player_name'],
        "gameplay_records": gameplay_records,
        "game_totals": game_totals,
        "hour_activity": hour_activity
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

