from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.conf.meta_config import ColumnConfig, MetaConfig, MetricConfig, TableConfig
from app.models.meta_column_config import MetaColumnConfig
from app.models.meta_metric_column_rel import MetaMetricColumnRel
from app.models.meta_metric_config import MetaMetricConfig
from app.models.meta_table_config import MetaTableConfig


class MetaConfigRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ===========================================================
    # 表配置 CRUD
    # ===========================================================

    async def list_tables(self) -> list[MetaTableConfig]:
        result = await self.session.execute(
            select(MetaTableConfig).order_by(MetaTableConfig.id)
        )
        return list(result.scalars().all())

    async def get_table_by_name(self, name: str) -> MetaTableConfig | None:
        result = await self.session.execute(
            select(MetaTableConfig).where(MetaTableConfig.name == name)
        )
        return result.scalar_one_or_none()

    async def create_table(self, name: str, role: str, description: str | None) -> MetaTableConfig:
        model = MetaTableConfig(name=name, role=role, description=description)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_table(self, name: str, role: str | None, description: str | None) -> MetaTableConfig | None:
        model = await self.get_table_by_name(name)
        if not model:
            return None
        if role is not None:
            model.role = role
        if description is not None:
            model.description = description
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_table(self, name: str) -> bool:
        model = await self.get_table_by_name(name)
        if not model:
            return False
        # 先删除关联的列配置
        await self.session.execute(
            delete(MetaColumnConfig).where(MetaColumnConfig.table_name == name)
        )
        await self.session.delete(model)
        await self.session.flush()
        return True

    # ===========================================================
    # 列配置 CRUD
    # ===========================================================

    async def list_columns_by_table(self, table_name: str) -> list[MetaColumnConfig]:
        result = await self.session.execute(
            select(MetaColumnConfig)
            .where(MetaColumnConfig.table_name == table_name)
            .order_by(MetaColumnConfig.id)
        )
        return list(result.scalars().all())

    async def get_column_by_id(self, column_id: int) -> MetaColumnConfig | None:
        return await self.session.get(MetaColumnConfig, column_id)

    async def create_column(
        self,
        table_name: str,
        name: str,
        role: str,
        description: str | None,
        alias: list[str] | None,
        sync: bool,
    ) -> MetaColumnConfig:
        model = MetaColumnConfig(
            table_name=table_name,
            name=name,
            role=role,
            description=description,
            alias=alias or [],
            sync=1 if sync else 0,
        )
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_column(
        self,
        column_id: int,
        role: str | None,
        description: str | None,
        alias: list[str] | None,
        sync: bool | None,
    ) -> MetaColumnConfig | None:
        model = await self.get_column_by_id(column_id)
        if not model:
            return None
        if role is not None:
            model.role = role
        if description is not None:
            model.description = description
        if alias is not None:
            model.alias = alias
        if sync is not None:
            model.sync = 1 if sync else 0
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_column(self, column_id: int) -> bool:
        model = await self.get_column_by_id(column_id)
        if not model:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True

    # ===========================================================
    # 指标配置 CRUD
    # ===========================================================

    async def list_metrics(self) -> list[MetaMetricConfig]:
        result = await self.session.execute(
            select(MetaMetricConfig).order_by(MetaMetricConfig.id)
        )
        return list(result.scalars().all())

    async def get_metric_by_name(self, name: str) -> MetaMetricConfig | None:
        result = await self.session.execute(
            select(MetaMetricConfig).where(MetaMetricConfig.name == name)
        )
        return result.scalar_one_or_none()

    async def create_metric(
        self, name: str, description: str | None, alias: list[str] | None
    ) -> MetaMetricConfig:
        model = MetaMetricConfig(name=name, description=description, alias=alias or [])
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_metric(
        self, name: str, description: str | None, alias: list[str] | None
    ) -> MetaMetricConfig | None:
        model = await self.get_metric_by_name(name)
        if not model:
            return None
        if description is not None:
            model.description = description
        if alias is not None:
            model.alias = alias
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_metric(self, name: str) -> bool:
        model = await self.get_metric_by_name(name)
        if not model:
            return False
        # 先删除关联的列关系
        await self.session.execute(
            delete(MetaMetricColumnRel).where(MetaMetricColumnRel.metric_name == name)
        )
        await self.session.delete(model)
        await self.session.flush()
        return True

    # ===========================================================
    # 指标-列关联 CRUD
    # ===========================================================

    async def list_rels_by_metric(self, metric_name: str) -> list[MetaMetricColumnRel]:
        result = await self.session.execute(
            select(MetaMetricColumnRel)
            .where(MetaMetricColumnRel.metric_name == metric_name)
            .order_by(MetaMetricColumnRel.id)
        )
        return list(result.scalars().all())

    async def create_metric_column_rel(
        self, metric_name: str, column_ref: str
    ) -> MetaMetricColumnRel:
        model = MetaMetricColumnRel(metric_name=metric_name, column_ref=column_ref)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_metric_column_rel(self, rel_id: int) -> bool:
        model = await self.session.get(MetaMetricColumnRel, rel_id)
        if not model:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True

    async def replace_metric_column_rels(
        self, metric_name: str, column_refs: list[str]
    ) -> list[MetaMetricColumnRel]:
        """替换某指标的所有列关联（先删后增）"""
        await self.session.execute(
            delete(MetaMetricColumnRel).where(
                MetaMetricColumnRel.metric_name == metric_name
            )
        )
        rels = []
        for ref in column_refs:
            rel = MetaMetricColumnRel(metric_name=metric_name, column_ref=ref)
            self.session.add(rel)
            rels.append(rel)
        await self.session.flush()
        for rel in rels:
            await self.session.refresh(rel)
        return rels

    # ===========================================================
    # 组装 MetaConfig（供构建元知识库使用）
    # ===========================================================

    async def load_meta_config(self) -> MetaConfig:
        """从数据库加载全部配置，组装成 MetaConfig dataclass"""
        tables = await self.list_tables()
        table_configs: list[TableConfig] = []
        for table in tables:
            columns = await self.list_columns_by_table(table.name)
            column_configs = [
                ColumnConfig(
                    name=col.name,
                    role=col.role,
                    description=col.description or "",
                    alias=list(col.alias) if col.alias else [],
                    sync=bool(col.sync),
                )
                for col in columns
            ]
            table_configs.append(
                TableConfig(
                    name=table.name,
                    role=table.role,
                    description=table.description or "",
                    columns=column_configs,
                )
            )

        metrics = await self.list_metrics()
        metric_configs: list[MetricConfig] = []
        for metric in metrics:
            rels = await self.list_rels_by_metric(metric.name)
            metric_configs.append(
                MetricConfig(
                    name=metric.name,
                    description=metric.description or "",
                    relevant_columns=[rel.column_ref for rel in rels],
                    alias=list(metric.alias) if metric.alias else [],
                )
            )

        return MetaConfig(tables=table_configs, metrics=metric_configs)
