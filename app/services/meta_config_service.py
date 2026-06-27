from app.api.schemas.meta_config_schema import (
    MetaColumnConfigCreate,
    MetaColumnConfigResponse,
    MetaColumnConfigUpdate,
    MetaMetricConfigCreate,
    MetaMetricConfigResponse,
    MetaMetricConfigUpdate,
    MetaTableConfigCreate,
    MetaTableConfigListItem,
    MetaTableConfigResponse,
    MetaTableConfigUpdate,
)
from app.core.log import logger
from app.repositories.mysql.meta.meta_config_repository import MetaConfigRepository
from app.services.meta_knowledge_service import MetaKnowledgeService


class MetaConfigService:
    def __init__(
        self,
        config_repo: MetaConfigRepository,
        meta_knowledge_service: MetaKnowledgeService,
    ):
        self.config_repo = config_repo
        self.meta_knowledge_service = meta_knowledge_service

    # ===========================================================
    # 表配置
    # ===========================================================

    async def list_tables(self) -> list[MetaTableConfigListItem]:
        tables = await self.config_repo.list_tables()
        return [MetaTableConfigListItem.model_validate(t) for t in tables]

    async def get_table(self, name: str) -> MetaTableConfigResponse | None:
        table = await self.config_repo.get_table_by_name(name)
        if not table:
            return None
        columns = await self.config_repo.list_columns_by_table(name)
        resp = MetaTableConfigResponse.model_validate(table)
        resp.columns = [MetaColumnConfigResponse.model_validate(c) for c in columns]
        return resp

    async def create_table(self, data: MetaTableConfigCreate) -> MetaTableConfigListItem:
        async with self.config_repo.session.begin():
            model = await self.config_repo.create_table(
                name=data.name, role=data.role, description=data.description
            )
        return MetaTableConfigListItem.model_validate(model)

    async def update_table(self, name: str, data: MetaTableConfigUpdate) -> MetaTableConfigListItem | None:
        async with self.config_repo.session.begin():
            model = await self.config_repo.update_table(
                name=name, role=data.role, description=data.description
            )
        if not model:
            return None
        return MetaTableConfigListItem.model_validate(model)

    async def delete_table(self, name: str) -> bool:
        async with self.config_repo.session.begin():
            return await self.config_repo.delete_table(name)

    # ===========================================================
    # 列配置
    # ===========================================================

    async def list_columns(self, table_name: str) -> list[MetaColumnConfigResponse]:
        columns = await self.config_repo.list_columns_by_table(table_name)
        return [MetaColumnConfigResponse.model_validate(c) for c in columns]

    async def create_column(
        self, table_name: str, data: MetaColumnConfigCreate
    ) -> MetaColumnConfigResponse:
        async with self.config_repo.session.begin():
            model = await self.config_repo.create_column(
                table_name=table_name,
                name=data.name,
                role=data.role,
                description=data.description,
                alias=data.alias,
                sync=data.sync,
            )
        return MetaColumnConfigResponse.model_validate(model)

    async def update_column(
        self, column_id: int, data: MetaColumnConfigUpdate
    ) -> MetaColumnConfigResponse | None:
        async with self.config_repo.session.begin():
            model = await self.config_repo.update_column(
                column_id=column_id,
                role=data.role,
                description=data.description,
                alias=data.alias,
                sync=data.sync,
            )
        if not model:
            return None
        return MetaColumnConfigResponse.model_validate(model)

    async def delete_column(self, column_id: int) -> bool:
        async with self.config_repo.session.begin():
            return await self.config_repo.delete_column(column_id)

    # ===========================================================
    # 指标配置
    # ===========================================================

    async def list_metrics(self) -> list[MetaMetricConfigResponse]:
        metrics = await self.config_repo.list_metrics()
        result = []
        for m in metrics:
            rels = await self.config_repo.list_rels_by_metric(m.name)
            resp = MetaMetricConfigResponse.model_validate(m)
            resp.relevant_columns = [r.column_ref for r in rels]
            result.append(resp)
        return result

    async def create_metric(self, data: MetaMetricConfigCreate) -> MetaMetricConfigResponse:
        async with self.config_repo.session.begin():
            model = await self.config_repo.create_metric(
                name=data.name, description=data.description, alias=data.alias
            )
            if data.relevant_columns:
                await self.config_repo.replace_metric_column_rels(
                    data.name, data.relevant_columns
                )
        # 重新查询完整的关联信息
        rels = await self.config_repo.list_rels_by_metric(model.name)
        resp = MetaMetricConfigResponse.model_validate(model)
        resp.relevant_columns = [r.column_ref for r in rels]
        return resp

    async def update_metric(
        self, name: str, data: MetaMetricConfigUpdate
    ) -> MetaMetricConfigResponse | None:
        async with self.config_repo.session.begin():
            model = await self.config_repo.update_metric(
                name=name, description=data.description, alias=data.alias
            )
            if not model:
                return None
            if data.relevant_columns is not None:
                await self.config_repo.replace_metric_column_rels(
                    name, data.relevant_columns
                )
        rels = await self.config_repo.list_rels_by_metric(model.name)
        resp = MetaMetricConfigResponse.model_validate(model)
        resp.relevant_columns = [r.column_ref for r in rels]
        return resp

    async def delete_metric(self, name: str) -> bool:
        async with self.config_repo.session.begin():
            return await self.config_repo.delete_metric(name)

    # ===========================================================
    # 构建元知识库
    # ===========================================================

    async def build_meta_knowledge(self) -> dict:
        """从数据库配置触发元知识库构建"""
        try:
            meta_config = await self.config_repo.load_meta_config()
            logger.info("从数据库加载元数据配置完成，开始构建元知识库")
            await self.meta_knowledge_service.build_from_config(meta_config)
            return {"status": "success", "message": "元知识库构建完成"}
        except Exception as e:
            logger.error(f"元知识库构建失败: {e}")
            return {"status": "error", "message": str(e)}
