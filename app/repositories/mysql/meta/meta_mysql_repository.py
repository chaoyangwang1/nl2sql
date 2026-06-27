from sqlalchemy import text, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.column_info import ColumnInfo
from app.entities.column_metric import ColumnMetric
from app.entities.metric_info import MetricInfo
from app.entities.table_info import TableInfo
from app.models.column_info_mysql import ColumnInfoMySQL
from app.models.column_metric_mysql import ColumnMetricMySQL
from app.models.metric_info_mysql import MetricInfoMySQL
from app.models.table_info_mysql import TableInfoMySQL
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper


class MetaMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_table_infos(self, table_infos: list[TableInfo]):
        models = [TableInfoMapper.to_model(table_info) for table_info in table_infos]
        self.session.add_all(models)

    async def save_column_infos(self, columns_info: list[ColumnInfo]):
        models = [ColumnInfoMapper.to_model(column_info) for column_info in columns_info]
        self.session.add_all(models)

    async def save_metric_infos(self, metric_infos: list[MetricInfo]):
        self.session.add_all([MetricInfoMapper.to_model(metric_info) for metric_info in metric_infos])

    async def save_column_metrics(self, column_metrics: list[ColumnMetric]):
        self.session.add_all([ColumnMetricMapper.to_model(column_metric) for column_metric in column_metrics])

    async def clear_runtime_data(self):
        """清除运行时数据（重建元知识库前调用）"""
        await self.session.execute(delete(ColumnMetricMySQL))
        await self.session.execute(delete(ColumnInfoMySQL))
        await self.session.execute(delete(MetricInfoMySQL))
        await self.session.execute(delete(TableInfoMySQL))

    async def get_column_info_by_id(self, column_id: str) -> ColumnInfo | None:
        result: ColumnInfoMySQL | None = await self.session.get(ColumnInfoMySQL, column_id)
        if result:
            return ColumnInfoMapper.to_entity(result)
        return None

    async def get_table_info_by_id(self, table_id: str) -> TableInfo | None:
        result: TableInfoMySQL | None = await self.session.get(TableInfoMySQL, table_id)
        if result:
            return TableInfoMapper.to_entity(result)
        return None

    async def get_key_columns_by_table_id(self, table_id: str) -> list[ColumnInfo]:
        sql = """
            select * 
            from column_info 
            where table_id = :table_id 
            and role in ('primary_key', 'foreign_key')
        """
        result = await self.session.execute(text(sql), {"table_id": table_id})
        return [ColumnInfo(**row) for row in result.mappings().fetchall()]

    async def get_column_infos_by_ids(self, column_ids: list[str]) -> dict[str, ColumnInfo]:
        """批量查询字段信息"""
        if not column_ids:
            return {}
        result = await self.session.execute(
            select(ColumnInfoMySQL).where(ColumnInfoMySQL.id.in_(column_ids))
        )
        return {row.id: ColumnInfoMapper.to_entity(row) for row in result.scalars().all()}

    async def get_table_infos_by_ids(self, table_ids: list[str]) -> dict[str, TableInfo]:
        """批量查询表信息"""
        if not table_ids:
            return {}
        result = await self.session.execute(
            select(TableInfoMySQL).where(TableInfoMySQL.id.in_(table_ids))
        )
        return {row.id: TableInfoMapper.to_entity(row) for row in result.scalars().all()}

    async def get_key_columns_by_table_ids(self, table_ids: list[str]) -> dict[str, list[ColumnInfo]]:
        """批量查询多张表的主外键字段"""
        if not table_ids:
            return {}
        sql = """
            select *
            from column_info
            where table_id in :table_ids
            and role in ('primary_key', 'foreign_key')
        """
        result = await self.session.execute(text(sql), {"table_ids": tuple(table_ids)})
        columns_by_table: dict[str, list[ColumnInfo]] = {tid: [] for tid in table_ids}
        for row in result.mappings().fetchall():
            col = ColumnInfo(**row)
            columns_by_table[col.table_id].append(col)
        return columns_by_table
