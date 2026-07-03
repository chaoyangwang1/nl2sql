-- ============================================================
-- 迁移脚本：为 eval_result 表添加预期表/列字段
-- 已有数据库执行此脚本即可
-- ============================================================

ALTER TABLE eval_result
    ADD COLUMN expected_tables JSON NULL COMMENT '预期引用的表名列表'
    AFTER node_timings;

ALTER TABLE eval_result
    ADD COLUMN expected_columns JSON NULL COMMENT '预期引用的列名列表'
    AFTER expected_tables;
