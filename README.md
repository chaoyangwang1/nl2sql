# Data Agent — Text-to-SQL 智能数据查询代理

将自然语言问题转换为 SQL 查询并返回结果的智能代理系统。基于 LangGraph 构建多节点工作流，结合向量检索、关键词召回与 LLM 推理，实现高精度的自然语言到 SQL 转换。

---

## 功能特性

- **自然语言查询**：输入中文问题，自动生成并执行对应 SQL，以 SSE 流式返回结果
- **多路召回**：列名向量召回、值（ES）召回、指标向量召回并行执行，提升上下文覆盖
- **自动纠错**：SQL 生成后自动校验，失败时由 LLM 修正（最多 2 轮）
- **元数据配置管理**：RESTful API 管理表、列、指标配置，支持动态构建知识库
- **SQL 质量评估**：标准问题集 + 自动化评估流水线，量化生成准确率
- **可观测性**：每个请求自动生成 Request-ID，Loguru 结构化日志，耗时统计

---

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| Agent 框架 | LangGraph + LangChain |
| LLM | DeepSeek API |
| 向量数据库 | Qdrant |
| 全文检索 | Elasticsearch 8.x |
| 关系数据库 | MySQL（asyncmy + SQLAlchemy 2.0） |
| Embedding | HuggingFace（BAAI/bge-large-zh-v1.5） |
| 配置管理 | OmegaConf + YAML |
| 日志 | Loguru |
| 依赖管理 | uv |
| Python 版本 | ≥ 3.12 |

---

## 系统架构

```
用户提问
   │
   ▼
extract_keywords ──────────────────────────────┐
   │              │                │            │
   ▼              ▼                ▼            │
recall_column  recall_value  recall_metric      │
   │              │                │            │
   └──────────────┴────────────────┘            │
                  ▼                             │
        merge_retrieved_info                    │
                  │                             │
          ┌───────┴───────┐                     │
          ▼               ▼                     │
    filter_table    filter_metric               │
          │               │                     │
          └───────┬───────┘                     │
                  ▼                             │
       add_extra_context                        │
                  ▼                             │
         generate_sql                           │
                  ▼                             │
         validate_sql ── 有错误 ──► correct_sql │
              │                        │        │
            无错误                      │        │
              ▼                        │        │
         execute_sql ◄─────────────────┘        │
              ▼                                 │
           返回结果                              │
```

---

## 快速开始

### 1. 环境准备

确保以下服务已启动：
- MySQL 8.x
- Qdrant（默认端口 6333）
- Elasticsearch 8.x（默认端口 9200）
- Embedding 服务（默认端口 8088，模型 `BAAI/bge-large-zh-v1.5`）

### 2. 安装依赖

```bash
# 安装 uv（如未安装）
pip install uv

# 创建虚拟环境并安装依赖
uv sync
```

### 3. 初始化数据库

依次执行 `sql/` 目录下的建表脚本：

```sql
-- 元数据库
sql/init_meta.sql
sql/init_meta_config.sql

-- 数据仓库（示例数据）
sql/init_dw.sql

-- 评估系统
sql/init_evaluation.sql
```

### 4. 配置应用

```bash
# 复制示例配置并填写实际连接信息
cp conf/app_config.example.yaml conf/app_config.yaml
```

编辑 `conf/app_config.yaml`，填入数据库密码、API Key 等敏感信息。

### 5. 构建元知识库

启动服务后，调用构建接口将元数据写入向量库：

```bash
curl -X POST http://localhost:8000/api/meta-config/build
```

### 6. 启动服务

```bash
uv run main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 可使用内置的调试页面。

---

## API 接口

### 查询接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/query` | 自然语言查询，SSE 流式返回 |

### 元数据配置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/meta-config/tables` | 表配置列表 / 新增 |
| GET/PUT/DELETE | `/api/meta-config/tables/{name}` | 单表查询 / 修改 / 删除 |
| GET/POST | `/api/meta-config/tables/{table_name}/columns` | 列列表 / 新增 |
| PUT/DELETE | `/api/meta-config/columns/{column_id}` | 列修改 / 删除 |
| GET/POST | `/api/meta-config/metrics` | 指标列表 / 新增 |
| PUT/DELETE | `/api/meta-config/metrics/{name}` | 指标修改 / 删除 |
| POST | `/api/meta-config/build` | 触发元知识库构建 |

### SQL 质量评估

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/api/evaluation/questions` | 标准问题集管理 |
| POST | `/api/evaluation/run` | 触发评估运行 |
| GET | `/api/evaluation/runs` | 查看运行记录 |
| GET | `/api/evaluation/runs/{run_id}` | 运行详情 |
| POST | `/api/evaluation/runs/{run_id}/retry/{question_id}` | 重试失败题目 |

### 系统

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查（MySQL / Qdrant / ES） |

---

## 项目结构

```
nl2sql/
├── app/
│   ├── agent/          # LangGraph 工作流节点（召回、过滤、生成、纠错）
│   ├── api/            # FastAPI 路由层 & 请求/响应 Schema
│   ├── clients/        # 外部服务客户端管理器（MySQL/Qdrant/ES/Embedding）
│   ├── conf/           # 配置加载（OmegaConf）
│   ├── core/           # 基础设施（日志、生命周期、请求上下文）
│   ├── entities/       # 领域实体
│   ├── models/         # SQLAlchemy ORM 模型
│   ├── prompt/         # 提示词加载器
│   ├── repositories/   # 数据访问层（MySQL/ES/Qdrant）
│   ├── scripts/        # 脚本工具
│   └── services/       # 业务服务层
├── conf/
│   ├── app_config.example.yaml  # 应用配置示例（需复制后填写）
│   └── meta_config.yaml         # 元数据声明文件
├── prompts/            # LLM 提示词模板
├── sql/                # 数据库建表 & 初始化脚本
├── static/             # 静态文件（调试页面）
├── main.py             # 应用入口
└── pyproject.toml      # 依赖声明（uv）
```

---

## 配置说明

| 配置项 | 说明 |
|--------|------|
| `db_meta` | 元数据库连接（存储表/列/指标配置） |
| `db_dw` | 数据仓库连接（业务查询目标库） |
| `qdrant` | Qdrant 向量库连接 |
| `embedding` | 本地 Embedding 服务地址 |
| `es` | Elasticsearch 连接 |
| `llm` | LLM 接口配置（模型名、API Key、Base URL） |
| `logging` | 日志级别、轮转、保留策略 |

完整配置示例见 [`conf/app_config.example.yaml`](conf/app_config.example.yaml)。

---

## License

MIT
