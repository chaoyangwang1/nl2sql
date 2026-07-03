-- ============================================================
-- 迁移脚本：为 eval_result 表添加节点耗时和召回详情列
-- 已有数据库执行此脚本即可
-- ============================================================

ALTER TABLE eval_result
    ADD COLUMN node_timings JSON NULL COMMENT '各节点耗时统计 {节点名: 秒数}'
    AFTER elapsed_seconds;

ALTER TABLE eval_result
    ADD COLUMN recall_details JSON NULL COMMENT '召回详情 {tables: [], columns: [], metrics: []}'
    AFTER node_timings;
