-- Steam 游戏时长追踪系统数据库初始化脚本
-- 创建游戏快照表

-- 如果表已存在则删除（谨慎使用）
-- DROP TABLE IF EXISTS game_snapshots;

-- 创建游戏快照表
CREATE TABLE IF NOT EXISTS game_snapshots (
    id SERIAL PRIMARY KEY,
    player_id VARCHAR(20) NOT NULL,
    player_name VARCHAR(100),
    snapshot_time TIMESTAMP NOT NULL,
    games_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 创建索引以优化查询性能
-- 按玩家和时间降序查询（用于获取最新快照）
CREATE INDEX IF NOT EXISTS idx_player_time ON game_snapshots(player_id, snapshot_time DESC);

-- 按玩家 ID 查询
CREATE INDEX IF NOT EXISTS idx_player_id ON game_snapshots(player_id);

-- 按快照时间查询
CREATE INDEX IF NOT EXISTS idx_snapshot_time ON game_snapshots(snapshot_time);

-- 为 JSONB 数据创建 GIN 索引（用于复杂 JSON 查询）
CREATE INDEX IF NOT EXISTS idx_games_data_gin ON game_snapshots USING GIN (games_data);

-- 添加表注释
COMMENT ON TABLE game_snapshots IS 'Steam 玩家游戏拥有数据快照表';
COMMENT ON COLUMN game_snapshots.id IS '主键 ID';
COMMENT ON COLUMN game_snapshots.player_id IS '玩家 Steam ID（64位）';
COMMENT ON COLUMN game_snapshots.player_name IS '玩家显示名称';
COMMENT ON COLUMN game_snapshots.snapshot_time IS '快照采集时间';
COMMENT ON COLUMN game_snapshots.games_data IS '游戏数据（JSON 格式，包含游戏列表和时长）';
COMMENT ON COLUMN game_snapshots.created_at IS '记录创建时间';

-- 查询示例
-- 1. 获取某玩家最新快照
-- SELECT * FROM game_snapshots 
-- WHERE player_id = '76561198958724637' 
-- ORDER BY snapshot_time DESC 
-- LIMIT 1;

-- 2. 获取某玩家最近 7 天的所有快照
-- SELECT * FROM game_snapshots 
-- WHERE player_id = '76561198958724637' 
--   AND snapshot_time >= NOW() - INTERVAL '7 days'
-- ORDER BY snapshot_time ASC;

-- 3. 统计各玩家的快照数量
-- SELECT player_id, player_name, COUNT(*) as snapshot_count
-- FROM game_snapshots
-- GROUP BY player_id, player_name
-- ORDER BY snapshot_count DESC;

-- 4. 查询包含特定游戏的快照（使用 JSONB 查询）
-- SELECT player_id, player_name, snapshot_time
-- FROM game_snapshots
-- WHERE games_data->'games' @> '[{"appid": 730}]';

