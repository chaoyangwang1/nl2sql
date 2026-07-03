import asyncio
import json
from typing import Optional

from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.agent.context import DataAgentContext
from app.agent.graph import graph
from app.agent.state import DataAgentState
from app.core.cache import query_cache
from app.core.log import logger
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.few_shot_repository import FewShotQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository

QUERY_TIMEOUT_SECONDS = 120


class QueryService:
    def __init__(self,
                 embedding_client: HuggingFaceEndpointEmbeddings,
                 column_qdrant_repository: ColumnQdrantRepository,
                 value_es_repository: ValueESRepository,
                 metric_qdrant_repository: MetricQdrantRepository,
                 meta_mysql_repository: MetaMySQLRepository,
                 dw_mysql_repository: DWMySQLRepository,
                 few_shot_repository: Optional[FewShotQdrantRepository] = None):
        self.embedding_client = embedding_client
        self.column_qdrant_repository = column_qdrant_repository
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository
        self.few_shot_repository = few_shot_repository

    async def _execute_query(self, query: str):
        """执行查询的核心逻辑，返回全部 SSE 行列表"""
        context = DataAgentContext(
            embedding_client=self.embedding_client,
            column_qdrant_repository=self.column_qdrant_repository,
            value_es_repository=self.value_es_repository,
            metric_qdrant_repository=self.metric_qdrant_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository,
            few_shot_repository=self.few_shot_repository,
        )
        state = DataAgentState(query=query)
        chunks: list[str] = []
        try:
            async with asyncio.timeout(QUERY_TIMEOUT_SECONDS):
                async for chunk in graph.astream(input=state, context=context, stream_mode="custom"):
                    chunks.append(chunk)
            chunks.append({'type': 'done'})
        except asyncio.TimeoutError:
            logger.error(f"查询超时（{QUERY_TIMEOUT_SECONDS}s）: {query}")
            chunks.append({'type': 'error', 'message': '请求处理超时，请稍后重试'})
        except Exception as e:
            logger.error(f"查询异常: {str(e)}")
            chunks.append({'type': 'error', 'message': str(e)})
        return chunks

    async def query(self, query: str):
        """带缓存的查询接口：相同查询 60 秒内直接返回缓存结果"""
        # 1. 检查缓存
        cached = await query_cache.get(query)
        if cached is not None:
            logger.info(f"缓存命中: {query}")
            for chunk in cached:
                yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
            return

        # 2. 执行查询并收集结果
        logger.info(f"缓存未命中，执行查询: {query}")
        chunks = await self._execute_query(query)

        # 3. 仅缓存成功完成的查询（不含 error chunk 的）
        has_error = any(
            isinstance(c, dict) and c.get('type') == 'error' for c in chunks
        )
        if not has_error:
            await query_cache.set(query, chunks)

        # 4. 流式输出
        for chunk in chunks:
            yield f"data: {json.dumps(chunk, ensure_ascii=False, default=str)}\n\n"
