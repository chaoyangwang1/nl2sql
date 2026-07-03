"""Few-shot 示例向量仓储"""
from dataclasses import dataclass, asdict

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from app.conf.app_config import app_config


@dataclass
class FewShotExample:
    question: str
    sql: str
    tables: list[str]  # 涉及的表名
    description: str = ""  # 示例说明


class FewShotQdrantRepository:
    collection_name = 'data-agent-few-shot'

    def __init__(self, client: AsyncQdrantClient):
        self.client = client

    async def ensure_collection(self):
        if not await self.client.collection_exists(self.collection_name):
            await self.client.create_collection(
                self.collection_name,
                vectors_config=VectorParams(
                    size=app_config.qdrant.embedding_size,
                    distance=Distance.COSINE,
                ),
            )

    async def add_example(self, example: FewShotExample, embedding: list[float]):
        """添加一个 few-shot 示例到向量库"""
        payload = asdict(example)
        await self.client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=example.question,  # 用问题文本做唯一 ID
                    vector=embedding,
                    payload=payload,
                )
            ],
        )

    async def search(self, question_embedding: list[float], limit: int = 3) -> list[FewShotExample]:
        """检索最相似的历史示例"""
        result = await self.client.query_points(
            collection_name=self.collection_name,
            query=question_embedding,
            score_threshold=0.7,
            limit=limit,
        )
        return [FewShotExample(**point.payload) for point in result.points]
