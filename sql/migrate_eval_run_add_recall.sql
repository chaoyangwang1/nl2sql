-- ============================================================
-- 迁移脚本：为 eval_run 表添加召回率平均值列
-- 已有数据库执行此脚本即可
-- ============================================================

ALTER TABLE eval_run
    ADD COLUMN avg_table_recall DECIMAL(5,2) NULL COMMENT '平均表召回率 %'
    AFTER avg_latency;

ALTER TABLE eval_run
    ADD COLUMN avg_column_recall DECIMAL(5,2) NULL COMMENT '平均列召回率 %'
    AFTER avg_table_recall;

ALTER TABLE eval_run
    ADD COLUMN avg_keyword_match DECIMAL(5,2) NULL COMMENT '平均关键字匹配率 %'
    AFTER avg_column_recall;
