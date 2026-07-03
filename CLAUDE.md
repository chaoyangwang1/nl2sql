# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 常用命令

```bash
# 安装依赖
uv sync

# 启动开发服务器
uv run main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8000

# 初始化数据库（按顺序执行）
# sql/init_meta.sql → sql/init_meta_config.sql → sql/init_dw.sql → sql/init_evaluation.sql

# 构建元知识库（服务启动后调用）
curl -X POST http://localhost:8000/api/meta-config/build
```

## 架构概览

本项目是一个 **Text-to-SQL 智能数据查询代理**，将自然语言问题转换为 SQL 查询并返回结果。

**分层结构：**

```
API 层 (FastAPI routers)
  ↓
服务层 (QueryService / MetaConfigService / EvaluationService / MetaKnowledgeService)
  ↓
代理编排层 (LangGraph 状态机，12 个节点)
  ↓
数据访问层 (Repository 模式: MySQL / Qdrant / Elasticsearch)
  ↓
客户端管理器 (单例连接: MySQL / Qdrant / ES / Embedding)
```

**关键文件和目录：**

| 路径 | 职责 |
|------|------|
| `main.py` | FastAPI 应用入口，注册路由、中间件、生命周期 |
| `app/agent/graph.py` | LangGraph 状态图定义，构建完整工作流节点和边 |
| `app/agent/state.py` | 工作流状态类型（TypedDict），贯穿所有节点 |
| `app/agent/context.py` | 运行时上下文（注入 Repository + Embedding 客户端） |
| `app/agent/nodes/` | 12 个工作流节点函数 |
| `app/services/query_service.py` | 核心查询服务，组装 context/state 并 SSE 流式输出 |
| `app/api/routers/` | 三类路由：查询、元数据配置、SQL 评估 |
| `app/api/dependencies.py` | FastAPI 依赖注入，组装所有 Service 和 Repository |
| `app/repositories/` | 仓储模式封装数据访问（MySQL/ES/Qdrant） |
| `app/clients/` | 外部服务客户端管理器，统一连接池生命周期 |
| `app/conf/` | OmegaConf + Dataclass 类型安全的配置系统 |
| `app/models/` | SQLAlchemy ORM 模型 |
| `app/entities/` | 领域实体（业务对象） |
| `app/prompt/prompt_loader.py` | 提示词加载器，从 `prompts/*.prompt` 读取并 LRU 缓存 |
| `app/core/` | 基础设施：日志（Loguru）、生命周期、请求上下文（ContextVar） |

## 工作流核心设计

LangGraph 状态图流程：

```
START → extract_keywords → recall_column/recall_value/recall_metric (三路并行)
       → merge_retrieved_info → filter_table/filter_metric (并行)
       → add_extra_context → generate_sql → validate_sql
       → 通过 → execute_sql → END
       → 失败 & 重试<2次 → correct_sql → validate_sql (循环)
       → 失败 & 重试≥2次 → END (报错返回)
```

- **并行召回**：列向量召回（Qdrant）、指标向量召回（Qdrant）、字段值召回（ES）三路并发
- **SQL 验证**：通过 `EXPLAIN` 检查语法，失败则 LLM 纠错，最多 2 轮
- **安全限制**：仅允许 SELECT 语句

## 编码规范

- 所有 Agent 节点函数签名：`(state: DataAgentState, runtime: Runtime[DataAgentContext])`，通过 `runtime.stream_writer` 发送 SSE 进度事件
- 所有 Repository 在 `__init__` 中注入底层客户端/Session，实现依赖倒置
- 配置使用 OmegaConf 加载 YAML，映射到 Dataclass 结构体，支持 `${env:KEY,默认值}` 环境变量插值
- Prompt 模板统一放在 `prompts/*.prompt`，通过 `load_prompt(name)` 加载（已 LRU 缓存）
- Entity 和 Model 之间通过 Mapper 类（`app/repositories/mysql/meta/mappers/`）互相转换
- 使用 `ContextVar` 传递 `request_id`，Loguru 通过 `patch` 机制自动注入到每条日志
- 事务处理需检测 `session.in_transaction()` 避免 autobegin 冲突

## 技术栈

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI + SSE 流式 |
| Agent 框架 | LangGraph + LangChain |
| LLM | DeepSeek API（OpenAI 兼容协议） |
| 向量数据库 | Qdrant |
| 全文检索 | Elasticsearch 8.x |
| 关系数据库 | MySQL（asyncmy + SQLAlchemy 2.0 异步） |
| Embedding | HuggingFace（BAAI/bge-large-zh-v1.5） |
| 中文分词 | jieba |
| 配置管理 | OmegaConf + YAML + Dataclass |
| 日志 | Loguru |
| 依赖管理 | uv（Python ≥ 3.12） |
