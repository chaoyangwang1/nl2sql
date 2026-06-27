from datetime import datetime

from sqlalchemy import String, Integer, Text, DECIMAL, DateTime, SmallInteger
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EvalResultMySQL(Base):
    __tablename__ = "eval_result"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
        comment="自增主键",
    )
    run_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="关联 eval_run.id",
    )
    question_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="关联 eval_golden_question.question_id",
    )
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="问题文本",
    )
    generated_sql: Mapped[str | None] = mapped_column(
        Text,
        comment="生成的 SQL",
    )
    reference_sql: Mapped[str | None] = mapped_column(
        Text,
        comment="参考 SQL",
    )
    execution_success: Mapped[bool] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default="0",
        comment="SQL 是否执行成功",
    )
    sql_valid: Mapped[bool] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default="0",
        comment="SQL 是否通过验证",
    )
    table_recall: Mapped[float | None] = mapped_column(
        DECIMAL(5, 2),
        comment="表召回率 0~1",
    )
    column_recall: Mapped[float | None] = mapped_column(
        DECIMAL(5, 2),
        comment="列召回率 0~1",
    )
    keyword_match: Mapped[float | None] = mapped_column(
        DECIMAL(5, 2),
        comment="关键字匹配率 0~1",
    )
    execution_error: Mapped[str | None] = mapped_column(
        Text,
        comment="执行错误信息",
    )
    result_data: Mapped[dict | list | None] = mapped_column(
        JSON,
        comment="执行结果数据",
    )
    elapsed_seconds: Mapped[float] = mapped_column(
        DECIMAL(8, 3),
        nullable=False,
        server_default="0.000",
        comment="耗时(秒)",
    )
    is_passed: Mapped[bool] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default="0",
        comment="是否通过",
    )
    failure_reason: Mapped[str | None] = mapped_column(
        String(64),
        comment="失败原因分类: sql_error/execution_error/low_recall",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        comment="创建时间",
    )
