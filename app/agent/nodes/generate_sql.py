import time

import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


def _format_few_shot_examples(examples: list[dict]) -> str:
    """将 few-shot 示例格式化为 Prompt 片段"""
    if not examples:
        return ""
    lines = ["【参考示例】以下是相似问题的查询示例，供参考：", ""]
    for i, ex in enumerate(examples, 1):
        lines.append(f"示例{i}:")
        lines.append(f"  问题: {ex.get('question', '')}")
        lines.append(f"  SQL: {ex.get('sql', '')}")
        lines.append("")
    return "\n".join(lines)


async def generate_sql(state: DataAgentState, runtime: Runtime[DataAgentContext]):
    start_time = time.perf_counter()
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "生成SQL", "status": "running"})

    query = state["query"]
    table_infos = state["table_infos"]
    metric_infos = state["metric_infos"]
    date_info = state["date_info"]
    db_info = state["db_info"]
    few_shot_examples = state.get("few_shot_examples", [])

    try:
        base_template = load_prompt("generate_sql")
        few_shot_text = _format_few_shot_examples(few_shot_examples)

        # 将 few-shot 示例插入到 Prompt 中
        if few_shot_text:
            # 在任务要求部分之前插入
            template = base_template.replace("【任务要求】", few_shot_text + "\n【任务要求】")
        else:
            template = base_template

        prompt = PromptTemplate(
            template=template,
            input_variables=["query", "table_infos", "metric_infos", "date_info", "db_info"],
        )
        output_parser = StrOutputParser()
        chain = prompt | llm | output_parser

        result = await chain.ainvoke({
            "query": query,
            "table_infos": yaml.dump(table_infos, allow_unicode=True, sort_keys=False),
            "metric_infos": yaml.dump(metric_infos, allow_unicode=True, sort_keys=False),
            "date_info": yaml.dump(date_info, allow_unicode=True, sort_keys=False),
            "db_info": yaml.dump(db_info, allow_unicode=True, sort_keys=False),
        })

        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "生成SQL", "status": "success", "elapsed": elapsed})
        writer({"type": "sql", "sql": result})
        logger.info(f"生成的SQL: {result}, 耗时: {elapsed}s")
        return {"sql": result}
    except Exception as e:
        elapsed = round(time.perf_counter() - start_time, 3)
        writer({"type": "progress", "step": "生成SQL", "status": "error", "elapsed": elapsed})
        logger.error(f"生成SQL失败: {str(e)}, 耗时: {elapsed}s")
        raise
