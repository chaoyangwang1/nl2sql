import asyncio
import time

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.column_info import ColumnInfo


async def recall_column(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    start_time = time.perf_counter()
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回字段", "status": "running"})

    embedding_client = runtime.context["embedding_client"]
    column_qdrant_repository = runtime.context["column_qdrant_repository"]

    # 使用统一扩展后的关键词（由 extend_keywords 节点生成）
    keywords = state.get("column_keywords", state["keywords"])
    logger.info(f"召回字段信息关键词：{keywords}")

    try:
        retrieved_columns_map: dict[str, ColumnInfo] = {}

        # 批量获取 embedding
        embeddings = await embedding_client.aembed_documents(keywords)

        # 并行执行所有搜索请求
        search_tasks = [
            column_qdrant_repository.search(embedding)
            for embedding in embeddings
        ]
        search_results = await asyncio.gather(*search_tasks)

        for payloads in search_results:
            for payload in payloads:
                if payload.id not in retrieved_columns_map:
                    retrieved_columns_map[payload.id] = payload

        retrieved_columns = list(retrieved_columns_map.values())

        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "召回字段", "status": "success", "elapsed": elapsed})
        logger.info(f"召回字段信息完成，耗时 {elapsed}s，召回字段：{list(retrieved_columns_map.keys())}")
        return {"retrieved_columns": retrieved_columns}
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "召回字段", "status": "error", "elapsed": elapsed})
        logger.error(f"召回字段信息失败，耗时 {elapsed}s: {str(e)}")
        raise
