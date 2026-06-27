import time

import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_metric(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    start_time = time.perf_counter()
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "过滤指标", "status": "running"})

    query = state["query"]
    metric_infos = state["metric_infos"]
    try:
        # 用LLM过滤表信息
        prompt = PromptTemplate(template=load_prompt("filter_metric_info"), input_variables=["query", "metric_infos"])
        output_parser = JsonOutputParser()

        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {"query": query, "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False)})

        # 构建过滤后的新列表（避免遍历中修改列表）
        filtered_metric_infos = [m for m in metric_infos if m["name"] in result]

        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "过滤指标", "status": "success", "elapsed": elapsed})
        logger.info(f"过滤后的指标: {[m['name'] for m in filtered_metric_infos]}, 耗时: {elapsed}s")
        return {"metric_infos": filtered_metric_infos}
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "过滤指标", "status": "error", "elapsed": elapsed})
        logger.error(f"过滤指标失败:{str(e)}, 耗时: {elapsed}s")
        raise
