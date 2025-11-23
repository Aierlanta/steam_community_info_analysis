#!/usr/bin/env python3
"""
数据库初始化脚本
自动执行 init_db.sql 创建表结构和索引
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('backend/.env')

def init_database():
    """初始化数据库表结构"""
    db_url = os.getenv('DATABASE_URL')
    
    if not db_url:
        print("❌ 错误：未配置 DATABASE_URL 环境变量")
        print("请在 backend/.env 文件中配置 DATABASE_URL")
        return False
    
    # 读取 SQL 脚本
    sql_file = 'init_db.sql'
    if not os.path.exists(sql_file):
        print(f"❌ 错误：找不到 SQL 文件: {sql_file}")
        return False
    
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        print(f"📖 读取 SQL 脚本: {sql_file}")
        print(f"📊 脚本长度: {len(sql_script)} 字符\n")
        
        # 连接数据库
        print(f"🔌 正在连接数据库...")
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        print("✅ 数据库连接成功\n")
        
        # 执行 SQL 脚本
        print("🚀 开始执行 SQL 脚本...")
        cursor.execute(sql_script)
        conn.commit()
        
        print("✅ SQL 脚本执行成功\n")
        
        # 验证表是否创建成功
        print("🔍 验证表结构...")
        cursor.execute("""
            SELECT table_name, column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'game_snapshots'
            ORDER BY ordinal_position
        """)
        
        columns = cursor.fetchall()
        if columns:
            print("✅ 表 'game_snapshots' 创建成功！\n")
            print("📋 表结构:")
            for table, column, dtype in columns:
                print(f"  - {column}: {dtype}")
            
            # 查询索引
            print("\n🔑 索引列表:")
            cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'game_snapshots'
            """)
            indexes = cursor.fetchall()
            for idx_name, idx_def in indexes:
                print(f"  - {idx_name}")
            
            print("\n✅ 数据库初始化完成！")
            print("📌 你现在可以运行后端采集器了:")
            print("   cd backend")
            print("   uv run python collector.py")
            
            return True
        else:
            print("❌ 表创建失败或不存在")
            return False
            
    except psycopg2.Error as e:
        print(f"❌ 数据库错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
            print("\n🔒 数据库连接已关闭")

if __name__ == '__main__':
    print("=" * 80)
    print("🎮 Steam 游戏时长追踪系统 - 数据库初始化工具")
    print("=" * 80)
    print()
    
    success = init_database()
    
    if not success:
        print("\n❌ 初始化失败")
        sys.exit(1)
    else:
        print("\n🎉 初始化成功！")
        sys.exit(0)

