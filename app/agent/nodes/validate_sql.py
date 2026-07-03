import time

from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger

MAX_CORRECT_RETRIES = 2


async def validate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    start_time = time.perf_counter()
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "验证SQL", "status": "running"})

    dw_mysql_repository = runtime.context["dw_mysql_repository"]
    sql = state["sql"]
    correct_count = state.get("correct_count", 0)

    # 纠正次数已达上限，不再验证，直接终止
    if correct_count >= MAX_CORRECT_RETRIES:
        elapsed = round(time.perf_counter() - start_time, 3)
        error_msg = f"SQL 经过 {MAX_CORRECT_RETRIES} 次纠正后仍存在错误，无法生成有效查询。请尝试换一种方式描述您的需求。"
        writer({"type": "progress", "step": "验证SQL", "status": "error", "elapsed": elapsed})
        writer({"type": "error", "message": error_msg})
        logger.warning(f"SQL纠正{MAX_CORRECT_RETRIES}次后仍失败, 最终SQL: {sql}, 耗时: {elapsed}s")
        return {"error": error_msg}

    try:
        await dw_mysql_repository.validate_sql(sql)
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "验证SQL", "status": "success", "elapsed": elapsed})
        logger.info(f"SQL验证成功: {sql}, 耗时: {elapsed}s")
        return {"error": None}
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "验证SQL", "status": "error", "elapsed": elapsed})
        logger.error(f"SQL验证失败: {sql}, 耗时: {elapsed}s")
        return {"error": str(e)}
