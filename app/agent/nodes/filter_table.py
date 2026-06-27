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


async def filter_table(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    start_time = time.perf_counter()
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "过滤表格", "status": "running"})

    query = state["query"]
    table_infos = state["table_infos"]

    try:
        # 用LLM过滤表信息
        prompt = PromptTemplate(template=load_prompt("filter_table_info"), input_variables=["query", "table_infos"])
        output_parser = JsonOutputParser()

        chain = prompt | llm | output_parser

        result = await chain.ainvoke(
            {"query": query, "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False)})

        # 利用模型输出过滤table_infos
        # {
        #   'fact_order':['order_amount', 'region_id'],
        #   'dim_region':['region_id', 'region_name']
        # }
        # 构建过滤后的新列表（避免遍历中修改列表）
        filtered_table_infos = []
        for table_info in table_infos:
            if table_info["name"] in result:
                selected_columns = result[table_info["name"]]
                table_info["columns"] = [
                    col for col in table_info["columns"] if col["name"] in selected_columns
                ]
                filtered_table_infos.append(table_info)

        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "过滤表格", "status": "success", "elapsed": elapsed})
        logger.info(f"过滤后的表信息: {[t['name'] for t in filtered_table_infos]}, 耗时: {elapsed}s")
        return {"table_infos": filtered_table_infos}
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "过滤表格", "status": "error", "elapsed": elapsed})
        logger.error(f"过滤表失败:{str(e)}, 耗时: {elapsed}s")
        raise
