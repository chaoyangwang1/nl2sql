import time

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def extend_keywords(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    """统一扩展关键词：一次 LLM 调用同时生成列/值/指标三路关键词"""
    start_time = time.perf_counter()
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "扩展关键词", "status": "running"})

    query = state["query"]
    jieba_keywords = state["keywords"]

    try:
        prompt = PromptTemplate(
            template=load_prompt("extend_keywords"),
            input_variables=["query"],
        )
        output_parser = JsonOutputParser()
        chain = prompt | llm | output_parser
        result = await chain.ainvoke({"query": query})

        # 合并 jieba 关键词与 LLM 扩展结果，去重
        column_keywords = list(set(jieba_keywords + result.get("column_keywords", [])))
        value_keywords = list(set(jieba_keywords + result.get("value_keywords", [])))
        metric_keywords = list(set(jieba_keywords + result.get("metric_keywords", [])))

        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "扩展关键词", "status": "success", "elapsed": elapsed})
        logger.info(f"扩展关键词完成, 耗时 {elapsed}s: 列={len(column_keywords)}个, 值={len(value_keywords)}个, 指标={len(metric_keywords)}个")

        return {
            "column_keywords": column_keywords,
            "value_keywords": value_keywords,
            "metric_keywords": metric_keywords,
        }
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 3)
        # 降级：LLM 扩展失败时，所有召回使用 jieba 关键词
        writer({"type": "progress", "step": "扩展关键词", "status": "error", "elapsed": elapsed})
        logger.error(f"扩展关键词失败，降级使用 jieba 关键词: {str(e)}")
        return {
            "column_keywords": jieba_keywords,
            "value_keywords": jieba_keywords,
            "metric_keywords": jieba_keywords,
        }
