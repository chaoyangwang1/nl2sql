# Data-Agent 生产化优化执行计划

## 概述

共 **6 个阶段、22 个文件**，按依赖关系排序。
推荐执行顺序：阶段一 -> 阶段二+三+四(并行) -> 阶段五 -> 阶段六

## 执行依赖关系

```text
阶段一 (Bug修复)
  ├──> 阶段二 (重试循环)  ──> 阶段六.6.1 (剩余节点耗时)
  └──> 阶段五 (性能优化)

阶段三 (安全) ── 独立

阶段四 (可靠性) ── 独立

阶段六.6.2 / 6.3 ── 独立
```

---

## 阶段一：Bug 修复 & 类型完善（基础层，后续所有阶段依赖）

5 个文件，全部独立，可并行修改。

| # | 文件 | 改动要点 |
|---|------|---------|
| 1.1 | `app/agent/nodes/correct_sql.py` | 第27行 `input_variables` 从 2 个补全到 7 个：`["query", "table_infos", "metric_infos", "date_info", "db_info", "sql", "error"]` |
| 1.2 | `app/agent/nodes/filter_table.py` | 第35-42行 `for/remove` 改为列表推导构建新列表 |
| 1.3 | `app/agent/nodes/filter_metric.py` | 第30-32行 同上，`[m for m in metric_infos if m["name"] in result]` |
| 1.4 | `app/core/context.py` | 第3行 `default="1"` 改为 `default=None`，类型标注 `ContextVar[str \| None]` |
| 1.5 | `app/agent/state.py` | `error: str` 改为 `error: str \| None`，新增 `correct_count: int` |

---

## 阶段二：SQL 纠正重试循环（依赖阶段一的 state.py）

3 个文件，需顺序执行。

| # | 文件 | 改动要点 |
|---|------|---------|
| 2.1 | `app/agent/nodes/validate_sql.py` | 新增 `MAX_CORRECT_RETRIES=2`；函数开头检查 `correct_count >= 2` 时通过 SSE 发送 error 并 return；添加 `time.perf_counter()` 耗时统计 |
| 2.2 | `app/agent/nodes/correct_sql.py` | return 追加 `"correct_count": state.get("correct_count", 0) + 1`；添加耗时统计 |
| 2.3 | `app/agent/graph.py` | 第61-66行改为三方路由 + correct 回到 validate 重新验证 |

路由变化：

```text
改前: validate -> (ok)execute / (fail)correct -> execute -> END
改后: validate -> (ok)execute / (fail,count<2)correct -> validate(循环)
                     / (fail,count>=2)END(终止并报错)
```

### validate_sql.py 关键逻辑

```python
MAX_CORRECT_RETRIES = 2

async def validate_sql(state, runtime):
    correct_count = state.get("correct_count", 0)
    if correct_count >= MAX_CORRECT_RETRIES:
        writer({"type": "error", "message": f"SQL 经过 {MAX_CORRECT_RETRIES} 次纠正后仍存在错误..."})
        return {"error": "..."}
    # 正常 EXPLAIN 验证逻辑
```

### graph.py 关键逻辑

```python
graph_builder.add_conditional_edges(
    "validate_sql",
    lambda state: (
        "execute_sql" if state.get("error") is None
        else "end" if state.get("correct_count", 0) >= 2
        else "correct_sql"
    ),
    {"execute_sql": "execute_sql", "correct_sql": "correct_sql", "end": END}
)
graph_builder.add_conditional_edges(
    "correct_sql",
    lambda state: "validate_sql",
    {"validate_sql": "validate_sql"}
)
```

---

## 阶段三：安全加固（独立，可与阶段一并行）

4 个文件。

| # | 文件 | 改动要点 |
|---|------|---------|
| 3.1 | `app/repositories/mysql/dw/dw_mysql_repository.py` | 新增 `SQL_DANGEROUS_PATTERN` 正则 + `_ensure_select_only()` 函数；`execute_sql` 内调用校验并用 `SELECT * FROM (...) LIMIT 1000` 包装 |
| 3.2 | `app/api/schemas/query_schema.py` | `query: str` 改为 `query: str = Field(min_length=1, max_length=500, strip_whitespace=True)` |
| 3.3 | `app/conf/app_config.py` | 注册 `OmegaConf.register_new_resolver("env", ...)`；`password`/`api_key` 字段加 `field(default="")` |
| 3.4 | `conf/app_config.yaml` | `password`/`api_key`/`base_url` 改为 `${env:XXX,默认值}` 格式 |

### dw_mysql_repository.py 关键逻辑

```python
SQL_DANGEROUS_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b",
    re.IGNORECASE
)

def _ensure_select_only(sql: str) -> None:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped.upper().startswith("SELECT"):
        raise ValueError("仅允许执行 SELECT 查询语句")
    if SQL_DANGEROUS_PATTERN.search(stripped):
        raise ValueError("SQL 包含禁止的危险操作关键词")

async def execute_sql(self, sql):
    _ensure_select_only(sql)
    wrapped_sql = f"SELECT * FROM ({sql.rstrip(';')}) AS _safe_result LIMIT {MAX_RESULT_ROWS}"
    ...
```

---

## 阶段四：可靠性提升（独立，可与阶段三并行）

4 个文件。

| # | 文件 | 改动要点 |
|---|------|---------|
| 4.1 | `app/agent/llm.py` | `init_chat_model` 增加 `timeout=60, max_retries=2` |
| 4.2 | `app/services/query_service.py` | `async with asyncio.timeout(120)` 包裹 astream；超时/正常/异常三种 SSE 事件 |
| 4.3 | `app/core/lifespan.py` | 初始化 try/except + RuntimeError；关闭改为 for 循环逐一 try/except |
| 4.4 | `app/clients/mysql_client_manager.py` | 补全 `max_overflow=20, pool_recycle=3600, pool_timeout=30` |

### query_service.py 关键逻辑

```python
QUERY_TIMEOUT_SECONDS = 120

async def query(self, query: str):
    ...
    try:
        async with asyncio.timeout(QUERY_TIMEOUT_SECONDS):
            async for chunk in graph.astream(...):
                yield f"data: {json.dumps(chunk, ...)}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except asyncio.TimeoutError:
        yield f"data: {json.dumps({'type': 'error', 'message': '请求处理超时'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
```

---

## 阶段五：性能优化（依赖阶段一；仓库层先改，节点后改）

6 个文件，执行顺序：`5.1 -> 5.2 -> 5.3/5.4/5.5(并行) -> 5.6`

| # | 文件 | 改动要点 |
|---|------|---------|
| 5.1 | `app/prompt/prompt_loader.py` | 添加 `@lru_cache(maxsize=None)` |
| 5.2 | `app/repositories/mysql/meta/meta_mysql_repository.py` | 新增 3 个批量方法（用 `select().where(.in_())` 替代逐条查询） |
| 5.3 | `app/agent/nodes/recall_column.py` | `aembed_query` 循环改 `aembed_documents` 批量；`search` 循环改 `asyncio.gather` 并行 |
| 5.4 | `app/agent/nodes/recall_metric.py` | 同上 |
| 5.5 | `app/agent/nodes/recall_value.py` | ES `search` 循环改 `asyncio.gather` 并行 |
| 5.6 | `app/agent/nodes/merge_retrieved_info.py` | 收集 missing_column_ids 一次批量查；主外键一次批量查；表信息一次批量查 |

### meta_mysql_repository.py 新增方法

```python
async def get_column_infos_by_ids(self, column_ids: list[str]) -> dict[str, ColumnInfo]
async def get_table_infos_by_ids(self, table_ids: list[str]) -> dict[str, TableInfo]
async def get_key_columns_by_table_ids(self, table_ids: list[str]) -> dict[str, list[ColumnInfo]]
```

### recall 节点批量模式

```python
# 改前（串行，N次网络请求）
for keyword in keywords:
    embedding = await embedding_client.aembed_query(keyword)
    payloads = await repository.search(embedding)

# 改后（1次批量embedding + N次并行search）
embeddings = await embedding_client.aembed_documents(keywords)
search_results = await asyncio.gather(*[repository.search(e) for e in embeddings])
```

---

## 阶段六：可观测性增强（最后执行，避免与阶段二/五重复改文件）

| # | 文件 | 改动要点 |
|---|------|---------|
| 6.1 | `extract_keywords.py` / `filter_table.py` / `filter_metric.py` / `add_extra_context.py` / `merge_retrieved_info.py` | 添加 `time.perf_counter()` 耗时统计（阶段二已覆盖 validate/correct/execute，阶段五已覆盖 recall_xxx/merge） |
| 6.2 | `app/core/log.py` | `inject_request_id`：`request_id if request_id is not None else "system"` |
| 6.3 | `main.py` | 中间件增加请求耗时日志；新增 `@app.get("/health")` 检查 4 个客户端连通性 |

### 节点耗时统计统一模式

```python
async def some_node(state, runtime):
    start_time = time.perf_counter()
    writer({"type": "progress", "step": "XX", "status": "running"})
    try:
        # 业务逻辑
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "XX", "status": "success", "elapsed": elapsed})
        logger.info(f"XX完成, 耗时: {elapsed}s")
        return {...}
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "XX", "status": "error", "elapsed": elapsed})
        logger.error(f"XX失败, 耗时: {elapsed}s")
        raise
```

---

## 不修改的文件

| 文件 | 原因 |
|------|------|
| `app/clients/embedding_client_manager.py` | `HuggingFaceEndpointEmbeddings` 是无状态 HTTP 客户端，不持有持久连接，不需要 close |

---

## 性能预估提升

典型查询 "统计去年各地区的销售总额"：

| 优化项 | 改前 | 改后 | 提升 |
|--------|------|------|------|
| Embedding 调用 | ~10 次串行 HTTP | 1 次批量请求 | 节省 2-3s |
| Qdrant/ES 搜索 | 串行逐个 | asyncio.gather 并行 | 节省 1-2s |
| merge DB 查询 | ~15 次单条 SELECT | 3 次批量 IN 查询 | 节省 0.5-1s |
| Prompt 加载 | 每次磁盘 IO | lru_cache 内存缓存 | 消除重复 IO |
