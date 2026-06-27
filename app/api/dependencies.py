from fastapi import Depends
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.mysql.meta.meta_config_repository import MetaConfigRepository
from app.repositories.mysql.meta.evaluation_repository import EvaluationRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository
from app.services.meta_config_service import MetaConfigService
from app.services.evaluation_service import EvaluationService
from app.services.query_service import QueryService


async def get_meta_session():
    async with meta_mysql_client_manager.session_factory() as session:
        yield session


async def get_dw_session():
    async with dw_mysql_client_manager.session_factory() as session:
        yield session


async def get_embedding_client():
    return embedding_client_manager.client


async def get_column_qdrant_repository():
    return ColumnQdrantRepository(qdrant_client_manager.client)


async def get_value_es_repository():
    return ValueESRepository(es_client_manager.client)


async def get_metric_qdrant_repository():
    return MetricQdrantRepository(qdrant_client_manager.client)


async def get_meta_mysql_repository(session: AsyncSession = Depends(get_meta_session)):
    return MetaMySQLRepository(session)


async def get_dw_mysql_repository(session: AsyncSession = Depends(get_dw_session)):
    return DWMySQLRepository(session)


async def get_query_service(
        embedding_client: HuggingFaceEndpointEmbeddings = Depends(get_embedding_client),
        column_qdrant_repository: ColumnQdrantRepository = Depends(get_column_qdrant_repository),
        value_es_repository: ValueESRepository = Depends(get_value_es_repository),
        metric_qdrant_repository: MetricQdrantRepository = Depends(get_metric_qdrant_repository),
        meta_mysql_repository: MetaMySQLRepository = Depends(get_meta_mysql_repository),
        dw_mysql_repository: DWMySQLRepository = Depends(get_dw_mysql_repository)
) -> QueryService:
    return QueryService(
        embedding_client=embedding_client,
        column_qdrant_repository=column_qdrant_repository,
        value_es_repository=value_es_repository,
        metric_qdrant_repository=metric_qdrant_repository,
        meta_mysql_repository=meta_mysql_repository,
        dw_mysql_repository=dw_mysql_repository
    )


async def get_meta_config_repository(
    session: AsyncSession = Depends(get_meta_session),
) -> MetaConfigRepository:
    return MetaConfigRepository(session)


async def get_meta_knowledge_service(
    embedding_client: HuggingFaceEndpointEmbeddings = Depends(get_embedding_client),
    column_qdrant_repository: ColumnQdrantRepository = Depends(get_column_qdrant_repository),
    value_es_repository: ValueESRepository = Depends(get_value_es_repository),
    metric_qdrant_repository: MetricQdrantRepository = Depends(get_metric_qdrant_repository),
    meta_mysql_repository: MetaMySQLRepository = Depends(get_meta_mysql_repository),
    dw_mysql_repository: DWMySQLRepository = Depends(get_dw_mysql_repository),
):
    from app.services.meta_knowledge_service import MetaKnowledgeService

    return MetaKnowledgeService(
        meta_mysql_repository=meta_mysql_repository,
        dw_mysql_repository=dw_mysql_repository,
        column_qdrant_repository=column_qdrant_repository,
        embedding_client=embedding_client,
        value_es_repository=value_es_repository,
        metric_qdrant_repository=metric_qdrant_repository,
    )


async def get_meta_config_service(
    config_repo: MetaConfigRepository = Depends(get_meta_config_repository),
    meta_knowledge_service=Depends(get_meta_knowledge_service),
) -> MetaConfigService:
    return MetaConfigService(
        config_repo=config_repo,
        meta_knowledge_service=meta_knowledge_service,
    )


async def get_evaluation_repository(
    session: AsyncSession = Depends(get_meta_session),
) -> EvaluationRepository:
    return EvaluationRepository(session)


async def get_evaluation_service(
    eval_repo: EvaluationRepository = Depends(get_evaluation_repository),
    query_service: QueryService = Depends(get_query_service),
) -> EvaluationService:
    return EvaluationService(
        eval_repo=eval_repo,
        query_service=query_service,
    )