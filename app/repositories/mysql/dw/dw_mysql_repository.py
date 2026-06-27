import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

SQL_DANGEROUS_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b",
    re.IGNORECASE
)

MAX_RESULT_ROWS = 1000


def _ensure_select_only(sql: str) -> None:
    """校验 SQL 安全性：仅允许 SELECT，禁止一切写操作"""
    stripped = sql.strip().rstrip(";").strip()
    if not stripped.upper().startswith("SELECT"):
        raise ValueError("仅允许执行 SELECT 查询语句")
    if SQL_DANGEROUS_PATTERN.search(stripped):
        raise ValueError("SQL 包含禁止的危险操作关键词")


class DWMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_column_types(self, table_name: str) -> dict[str, str]:
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        return {row.Field: row.Type for row in result.fetchall()}

    async def get_column_values(self, table_name: str, column_name: str, limit: int):
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return result.scalars().fetchall()

    async def get_db_info(self):
        result = await self.session.execute(text("select version()"))
        version = result.scalar()

        dialect = self.session.get_bind().dialect.name

        return {'version': version, 'dialect': dialect}

    async def validate_sql(self, sql):
        await self.session.execute(text(f"explain {sql}"))

    async def execute_sql(self, sql):
        _ensure_select_only(sql)
        wrapped_sql = f"SELECT * FROM ({sql.rstrip(';')}) AS _safe_result LIMIT {MAX_RESULT_ROWS}"
        result = await self.session.execute(text(wrapped_sql))
        return [dict(row) for row in result.mappings().fetchall()]
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class DWMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_column_types(self, table_name: str) -> dict[str, str]:
        sql = f"show columns from {table_name}"
        result = await self.session.execute(text(sql))
        return {row.Field: row.Type for row in result.fetchall()}

    async def get_column_values(self, table_name: str, column_name: str, limit: int):
        sql = f"select distinct {column_name} from {table_name} limit {limit}"
        result = await self.session.execute(text(sql))
        return result.scalars().fetchall()

    async def get_db_info(self):
        result = await self.session.execute(text("select version()"))
        version = result.scalar()

        dialect = self.session.get_bind().dialect.name

        return {'version': version, 'dialect': dialect}

    async def validate_sql(self, sql):
        await self.session.execute(text(f"explain {sql}"))

    async def execute_sql(self, sql):
        result = await self.session.execute(text(sql))
        return [dict(row) for row in result.mappings().fetchall()]
