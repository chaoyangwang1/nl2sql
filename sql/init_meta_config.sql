-- ============================================================
-- 元数据配置表建表语句 + 初始数据（基于 conf/meta_config.yaml）
-- ============================================================

-- 1. 表配置
CREATE TABLE IF NOT EXISTS meta_table_config (
    id          INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    name        VARCHAR(128) NOT NULL UNIQUE COMMENT '表名（如 dim_region）',
    role        VARCHAR(32)  NOT NULL COMMENT '表角色（dim / fact）',
    description TEXT         NULL     COMMENT '表描述',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='元数据-表配置';

-- 2. 列配置
CREATE TABLE IF NOT EXISTS meta_column_config (
    id          INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    table_name  VARCHAR(128) NOT NULL COMMENT '关联 meta_table_config.name',
    name        VARCHAR(128) NOT NULL COMMENT '列名',
    role        VARCHAR(32)  NOT NULL COMMENT '列角色（primary_key/foreign_key/dimension/measure）',
    description TEXT         NULL     COMMENT '列描述',
    alias       JSON         NULL     COMMENT '别名列表，如 ["省份","省"]',
    sync        TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '是否同步取值到 ES（0=否，1=是）',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY uk_table_column (table_name, name),
    CONSTRAINT fk_column_table FOREIGN KEY (table_name)
        REFERENCES meta_table_config(name) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='元数据-列配置';

-- 3. 指标配置
CREATE TABLE IF NOT EXISTS meta_metric_config (
    id          INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    name        VARCHAR(128) NOT NULL UNIQUE COMMENT '指标名（如 GMV）',
    description TEXT         NULL     COMMENT '指标描述',
    alias       JSON         NULL     COMMENT '别名列表',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='元数据-指标配置';

-- 4. 指标-列关联
CREATE TABLE IF NOT EXISTS meta_metric_column_rel (
    id           INT AUTO_INCREMENT PRIMARY KEY COMMENT '自增主键',
    metric_name  VARCHAR(128) NOT NULL COMMENT '关联 meta_metric_config.name',
    column_ref   VARCHAR(256) NOT NULL COMMENT '列引用，格式 table.column',
    UNIQUE KEY uk_metric_column (metric_name, column_ref),
    CONSTRAINT fk_metric_rel FOREIGN KEY (metric_name)
        REFERENCES meta_metric_config(name) ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='元数据-指标与列关联';


-- ============================================================
-- 初始数据
-- ============================================================

-- meta_table_config
INSERT INTO meta_table_config (name, role, description) VALUES
('dim_region',   'dim',  '地区维度表，用于描述订单发生的地理区域信息。'),
('dim_customer', 'dim',  '客户维度表，描述下单客户的基本属性。'),
('dim_product',  'dim',  '商品维度表，描述商品的基本属性信息。'),
('dim_date',     'dim',  '时间维度表，用于多时间粒度分析。'),
('fact_order',   'fact', '订单事实表，记录订单数量和金额等核心指标。');

-- meta_column_config: dim_region
INSERT INTO meta_column_config (table_name, name, role, description, alias, sync) VALUES
('dim_region', 'region_id',   'primary_key', '地区唯一标识。',           '["地区ID","区域ID"]',       0),
('dim_region', 'province',    'dimension',   '订单所属的省份名称。',     '["省份","省","所在省份"]',  1),
('dim_region', 'region_name', 'dimension',   '订单所属的大区名称，如华东、华南等。', '["地区","区域","大区"]', 1),
('dim_region', 'country',     'dimension',   '地区所属国家名称。',       '["国家","国家名称"]',       1);

-- meta_column_config: dim_customer
INSERT INTO meta_column_config (table_name, name, role, description, alias, sync) VALUES
('dim_customer', 'customer_id',   'primary_key', '客户唯一标识。',   '["客户ID","用户ID"]',     0),
('dim_customer', 'customer_name', 'dimension',   '客户名称。',       '["客户名称","用户名称"]', 1),
('dim_customer', 'gender',        'dimension',   '客户性别。',       '["性别"]',               1),
('dim_customer', 'member_level',  'dimension',   '客户会员等级。',   '["会员等级","用户等级"]', 1);

-- meta_column_config: dim_product
INSERT INTO meta_column_config (table_name, name, role, description, alias, sync) VALUES
('dim_product', 'product_id',   'primary_key', '商品唯一标识。',   '["商品ID","产品ID"]',     0),
('dim_product', 'product_name', 'dimension',   '商品名称。',       '["商品名称","产品名称"]', 1),
('dim_product', 'category',     'dimension',   '商品所属品类。',   '["商品类别","品类","分类"]', 1),
('dim_product', 'brand',        'dimension',   '商品品牌名称。',   '["品牌","品牌名称"]',     1);

-- meta_column_config: dim_date
INSERT INTO meta_column_config (table_name, name, role, description, alias, sync) VALUES
('dim_date', 'date_id', 'primary_key', '日期唯一标识，格式 yyyyMMdd。', '["日期ID","日期"]',  0),
('dim_date', 'year',    'dimension',   '年份。',                       '["年","年份"]',      0),
('dim_date', 'quarter', 'dimension',   '季度。',                       '["季度"]',           1),
('dim_date', 'month',   'dimension',   '月份。',                       '["月","月份"]',      0),
('dim_date', 'day',     'dimension',   '日。',                         '["日","天"]',        0);

-- meta_column_config: fact_order
INSERT INTO meta_column_config (table_name, name, role, description, alias, sync) VALUES
('fact_order', 'order_id',        'primary_key', '订单唯一标识。',         '["订单ID"]',               0),
('fact_order', 'customer_id',     'foreign_key', '关联客户维度的外键。',   '["客户ID","用户ID"]',      0),
('fact_order', 'product_id',      'foreign_key', '关联商品维度的外键。',   '["商品ID","产品ID"]',      0),
('fact_order', 'date_id',         'foreign_key', '关联时间维度的外键。',   '["日期","下单日期"]',      0),
('fact_order', 'region_id',       'foreign_key', '关联地区维度的外键。',   '["地区ID","区域ID"]',      0),
('fact_order', 'order_quantity',  'measure',     '订单中商品的购买数量。', '["销量","购买数量","件数"]', 0),
('fact_order', 'order_amount',    'measure',     '订单金额。',             '["销售额","订单金额","收入"]', 0);

-- meta_metric_config
INSERT INTO meta_metric_config (name, description, alias) VALUES
('GMV', '全称Gross Merchandise Value，表示所有订单的成交金额总和。',  '["成交总额","订单总额"]'),
('AOV', '全称Average Order Value，表示所有订单的成交金额平均值。',    '["平均单价","平均订单金额"]');

-- meta_metric_column_rel
INSERT INTO meta_metric_column_rel (metric_name, column_ref) VALUES
('GMV', 'fact_order.order_amount'),
('AOV', 'fact_order.order_quantity');
