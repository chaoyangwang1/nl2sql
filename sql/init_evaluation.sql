-- ============================================================
-- SQL 质量评估表建表语句 + 初始标准问题数据
-- ============================================================

-- 1. 标准问题集
CREATE TABLE IF NOT EXISTS eval_golden_question (
    id               INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    question_id      VARCHAR(32)  NOT NULL UNIQUE COMMENT '问题编号，如 q001',
    question         TEXT         NOT NULL COMMENT '自然语言问题',
    difficulty       VARCHAR(16)  NOT NULL DEFAULT 'medium' COMMENT '难度: easy/medium/hard',
    expected_tables  JSON         NULL COMMENT '期望引用的表名列表',
    expected_columns JSON         NULL COMMENT '期望引用的列名列表',
    expected_keywords JSON        NULL COMMENT '期望包含的 SQL 关键字',
    reference_sql    TEXT         NULL COMMENT '参考 SQL',
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评估-标准问题集';

-- 2. 评估运行记录
CREATE TABLE IF NOT EXISTS eval_run (
    id              INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    run_name        VARCHAR(128) NOT NULL COMMENT '运行名称，如 baseline_20260626',
    total_questions INT          NOT NULL DEFAULT 0 COMMENT '总问题数',
    passed          INT          NOT NULL DEFAULT 0 COMMENT '通过数',
    failed          INT          NOT NULL DEFAULT 0 COMMENT '失败数',
    pass_rate       DECIMAL(5,2) NOT NULL DEFAULT 0.00 COMMENT '通过率 %',
    avg_latency     DECIMAL(8,3) NOT NULL DEFAULT 0.000 COMMENT '平均延迟(秒)',
    avg_table_recall DECIMAL(5,2) NULL COMMENT '平均表召回率 %',
    avg_column_recall DECIMAL(5,2) NULL COMMENT '平均列召回率 %',
    avg_keyword_match DECIMAL(5,2) NULL COMMENT '平均关键字匹配率 %',
    status          VARCHAR(16)  NOT NULL DEFAULT 'running' COMMENT 'running/completed/failed',
    started_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    finished_at     DATETIME     NULL COMMENT '结束时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评估-运行记录';

-- 3. 评估单题结果
CREATE TABLE IF NOT EXISTS eval_result (
    id                INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    run_id            INT          NOT NULL COMMENT '关联 eval_run.id',
    question_id       VARCHAR(32)  NOT NULL COMMENT '关联 eval_golden_question.question_id',
    question          TEXT         NOT NULL COMMENT '问题文本',
    generated_sql     TEXT         NULL COMMENT '生成的 SQL',
    reference_sql     TEXT         NULL COMMENT '参考 SQL',
    execution_success TINYINT(1)   NOT NULL DEFAULT 0 COMMENT 'SQL 是否执行成功',
    sql_valid         TINYINT(1)   NOT NULL DEFAULT 0 COMMENT 'SQL 是否通过验证',
    table_recall      DECIMAL(5,2) NULL COMMENT '表召回率 0~1',
    column_recall     DECIMAL(5,2) NULL COMMENT '列召回率 0~1',
    keyword_match     DECIMAL(5,2) NULL COMMENT '关键字匹配率 0~1',
    execution_error   TEXT         NULL COMMENT '执行错误信息',
    result_data       JSON         NULL COMMENT '执行结果数据',
    elapsed_seconds   DECIMAL(8,3) NOT NULL DEFAULT 0.000 COMMENT '耗时(秒)',
    node_timings      JSON         NULL COMMENT '各节点耗时统计 {节点名: 秒数}',
    recall_details    JSON         NULL COMMENT '召回详情 {tables: [], columns: [], metrics: []}',
    is_passed         TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否通过',
    failure_reason    VARCHAR(64)  NULL COMMENT '失败原因分类: sql_error/execution_error/low_recall',
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    CONSTRAINT fk_eval_result_run FOREIGN KEY (run_id)
        REFERENCES eval_run(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='评估-单题结果';


-- ============================================================
-- 初始标准问题数据
-- ============================================================

INSERT INTO eval_golden_question (question_id, question, difficulty, expected_tables, expected_columns, expected_keywords, reference_sql) VALUES

('q001', '各省的订单总额是多少', 'easy',
 '["fact_order","dim_region"]', '["order_amount","province"]', '["SUM","GROUP BY"]',
 'SELECT dr.province, SUM(fo.order_amount) AS total_amount FROM fact_order fo JOIN dim_region dr ON fo.region_id = dr.region_id GROUP BY dr.province'),

('q002', '哪个品类的销量最高', 'easy',
 '["fact_order","dim_product"]', '["order_quantity","category"]', '["SUM","ORDER BY","LIMIT"]',
 'SELECT dp.category, SUM(fo.order_quantity) AS total_qty FROM fact_order fo JOIN dim_product dp ON fo.product_id = dp.product_id GROUP BY dp.category ORDER BY total_qty DESC LIMIT 1'),

('q003', '男性客户和女性客户的平均订单金额分别是多少', 'medium',
 '["fact_order","dim_customer"]', '["order_amount","gender"]', '["AVG","GROUP BY"]',
 'SELECT dc.gender, AVG(fo.order_amount) AS avg_amount FROM fact_order fo JOIN dim_customer dc ON fo.customer_id = dc.customer_id GROUP BY dc.gender'),

('q004', '2024年华东地区的GMV是多少', 'medium',
 '["fact_order","dim_region","dim_date"]', '["order_amount","region_name","year"]', '["SUM","WHERE"]',
 'SELECT SUM(fo.order_amount) AS gmv FROM fact_order fo JOIN dim_region dr ON fo.region_id = dr.region_id JOIN dim_date dd ON fo.date_id = dd.date_id WHERE dr.region_name = ''华东'' AND dd.year = 2024'),

('q005', '黄金会员中消费最多的客户是谁', 'hard',
 '["fact_order","dim_customer"]', '["customer_name","member_level","order_amount"]', '["SUM","WHERE","ORDER BY","LIMIT"]',
 'SELECT dc.customer_name, SUM(fo.order_amount) AS total FROM fact_order fo JOIN dim_customer dc ON fo.customer_id = dc.customer_id WHERE dc.member_level = ''黄金'' GROUP BY dc.customer_name ORDER BY total DESC LIMIT 1'),

('q006', '每个季度的销售总额趋势', 'medium',
 '["fact_order","dim_date"]', '["order_amount","quarter","year"]', '["SUM","GROUP BY","ORDER BY"]',
 'SELECT dd.year, dd.quarter, SUM(fo.order_amount) AS total FROM fact_order fo JOIN dim_date dd ON fo.date_id = dd.date_id GROUP BY dd.year, dd.quarter ORDER BY dd.year, dd.quarter'),

('q007', '中国的订单总额是多少', 'easy',
 '["fact_order","dim_region"]', '["order_amount","country"]', '["SUM","WHERE"]',
 'SELECT SUM(fo.order_amount) AS total FROM fact_order fo JOIN dim_region dr ON fo.region_id = dr.region_id WHERE dr.country = ''中国'''),

('q008', '各个品牌的平均订单数量', 'medium',
 '["fact_order","dim_product"]', '["order_quantity","brand"]', '["AVG","GROUP BY"]',
 'SELECT dp.brand, AVG(fo.order_quantity) AS avg_qty FROM fact_order fo JOIN dim_product dp ON fo.product_id = dp.product_id GROUP BY dp.brand'),

('q009', '列出所有客户的姓名和消费总额，按消费从高到低排序', 'medium',
 '["fact_order","dim_customer"]', '["customer_name","order_amount"]', '["SUM","GROUP BY","ORDER BY"]',
 'SELECT dc.customer_name, SUM(fo.order_amount) AS total FROM fact_order fo JOIN dim_customer dc ON fo.customer_id = dc.customer_id GROUP BY dc.customer_name ORDER BY total DESC'),

('q010', '华南地区哪个商品卖得最好', 'hard',
 '["fact_order","dim_region","dim_product"]', '["product_name","region_name","order_quantity"]', '["SUM","WHERE","ORDER BY","LIMIT"]',
 'SELECT dp.product_name, SUM(fo.order_quantity) AS total FROM fact_order fo JOIN dim_region dr ON fo.region_id = dr.region_id JOIN dim_product dp ON fo.product_id = dp.product_id WHERE dr.region_name = ''华南'' GROUP BY dp.product_name ORDER BY total DESC LIMIT 1');
