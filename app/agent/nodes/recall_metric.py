import asyncio
import time

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.metric_info import MetricInfo


async def recall_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    start_time = time.perf_counter()
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回指标", "status": "running"})

    embedding_client = runtime.context['embedding_client']
    metric_qdrant_repository = runtime.context['metric_qdrant_repository']

    # 使用统一扩展后的关键词（由 extend_keywords 节点生成）
    keywords = state.get("metric_keywords", state["keywords"])
    logger.info(f"召回指标信息关键词：{keywords}")

    try:
        retrieved_metrics_map: dict[str, MetricInfo] = {}

        # 批量获取 embedding
        embeddings = await embedding_client.aembed_documents(keywords)

        # 并行执行所有搜索请求
        search_tasks = [
            metric_qdrant_repository.search(embedding)
            for embedding in embeddings
        ]
        search_results = await asyncio.gather(*search_tasks)

        for payloads in search_results:
            for payload in payloads:
                if payload.id not in retrieved_metrics_map:
                    retrieved_metrics_map[payload.id] = payload

        retrieved_metrics = list(retrieved_metrics_map.values())

        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "召回指标", "status": "success", "elapsed": elapsed})
        logger.info(f"召回指标信息完成，耗时 {elapsed}s，召回指标：{list(retrieved_metrics_map.keys())}")
        return {"retrieved_metrics": retrieved_metrics}
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "召回指标", "status": "error", "elapsed": elapsed})
        logger.error(f"召回指标信息失败，耗时 {elapsed}s: {str(e)}")
        raise
