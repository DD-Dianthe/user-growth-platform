-- ============================================================
-- 数据仓库索引优化脚本
-- 在数据导入完成后执行，优化查询性能
-- ============================================================

USE user_growth;

-- ============================================================
-- 分析统计表（ANALYZE TABLE 更新索引统计信息）
-- ============================================================
ANALYZE TABLE users;
ANALYZE TABLE user_events;
ANALYZE TABLE orders;

-- ============================================================
-- 查看索引使用情况（验证所有索引已生效）
-- ============================================================
SELECT
  TABLE_NAME AS '表名',
  INDEX_NAME AS '索引名',
  GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS '索引列',
  INDEX_TYPE AS '索引类型'
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'user_growth'
GROUP BY TABLE_NAME, INDEX_NAME, INDEX_TYPE
ORDER BY TABLE_NAME, INDEX_NAME;

-- ============================================================
-- 查看表统计信息
-- ============================================================
SELECT
  TABLE_NAME AS '表名',
  TABLE_ROWS AS '估计行数',
  ROUND(DATA_LENGTH / 1024 / 1024, 2) AS '数据大小(MB)',
  ROUND(INDEX_LENGTH / 1024 / 1024, 2) AS '索引大小(MB)',
  TABLE_COMMENT AS '表注释'
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'user_growth'
ORDER BY TABLE_NAME;
