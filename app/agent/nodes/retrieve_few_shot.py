"""检索相似历史查询示例，作为 SQL 生成的 few-shot 参考"""
import time

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def retrieve_few_shot(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    start_time = time.perf_counter()
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "检索相似示例", "status": "running"})

    query = state["query"]
    embedding_client = runtime.context["embedding_client"]
    few_shot_repo = runtime.context.get("few_shot_repository")

    if few_shot_repo is None:
        # 未配置 few-shot 仓库时跳过
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "检索相似示例", "status": "skipped", "elapsed": elapsed})
        return {"few_shot_examples": []}

    try:
        question_embedding = await embedding_client.aembed_query(query)
        examples = await few_shot_repo.search(question_embedding, limit=3)

        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "检索相似示例", "status": "success", "elapsed": elapsed})
        logger.info(f"检索到 {len(examples)} 个相似示例, 耗时: {elapsed}s")
        return {"few_shot_examples": examples}
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "检索相似示例", "status": "error", "elapsed": elapsed})
        logger.warning(f"检索相似示例失败，降级为无 few-shot 模式: {str(e)}")
        return {"few_shot_examples": []}
