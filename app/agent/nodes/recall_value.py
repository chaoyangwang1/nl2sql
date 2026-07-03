import asyncio
import time

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.value_info import ValueInfo


async def recall_value(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    start_time = time.perf_counter()
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回字段取值", "status": "running"})

    value_es_repository = runtime.context["value_es_repository"]

    # 使用统一扩展后的关键词（由 extend_keywords 节点生成）
    keywords = state.get("value_keywords", state["keywords"])
    logger.info(f"召回字段取值关键词：{keywords}")

    try:
        values_map: dict[str, ValueInfo] = {}

        # 并行执行所有 ES 搜索请求
        search_tasks = [value_es_repository.search(keyword) for keyword in keywords]
        search_results = await asyncio.gather(*search_tasks)

        for values in search_results:
            for value in values:
                if value.id not in values_map:
                    values_map[value.id] = value

        retrieved_values = list(values_map.values())

        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "召回字段取值", "status": "success", "elapsed": elapsed})
        logger.info(f"召回字段取值完成，耗时 {elapsed}s，召回字段取值：{list(values_map.keys())}")

        return {'retrieved_values': retrieved_values}
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "召回字段取值", "status": "error", "elapsed": elapsed})
        logger.error(f"召回字段取值失败，耗时 {elapsed}s: {str(e)}")
        raise
