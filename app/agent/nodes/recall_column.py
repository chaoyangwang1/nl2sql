import asyncio
import time

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.prompt.prompt_loader import load_prompt


async def recall_column(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    start_time = time.perf_counter()
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回字段", "status": "running"})

    query = state["query"]
    keywords = state["keywords"]

    embedding_client = runtime.context["embedding_client"]
    column_qdrant_repository = runtime.context["column_qdrant_repository"]

    try:
        # 使用LLM扩展关键词
        prompt = PromptTemplate(
            template=load_prompt("extend_keywords_for_column_recall"),
            input_variables=["query"],
        )
        output_parser = JsonOutputParser()

        chain = prompt | llm | output_parser

        result = await chain.ainvoke({"query": query})

        # 使用扩展后的关键词召回字段信息
        retrieved_columns_map: dict[str, ColumnInfo] = {}

        keywords = list(set(keywords + result))
        logger.info(f"召回字段信息扩展关键词：{keywords}")

        # 批量获取embedding（替代逐个调用）
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
