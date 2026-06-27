from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EvalGoldenQuestionMySQL(Base):
    __tablename__ = "eval_golden_question"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
        comment="自增主键",
    )
    question_id: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        comment="问题编号，如 q001",
    )
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="自然语言问题",
    )
    difficulty: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="medium",
        comment="难度: easy/medium/hard",
    )
    expected_tables: Mapped[list | None] = mapped_column(
        JSON,
        comment="期望引用的表名列表",
    )
    expected_columns: Mapped[list | None] = mapped_column(
        JSON,
        comment="期望引用的列名列表",
    )
    expected_keywords: Mapped[list | None] = mapped_column(
        JSON,
        comment="期望包含的 SQL 关键字",
    )
    reference_sql: Mapped[str | None] = mapped_column(
        Text,
        comment="参考 SQL",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP",
        comment="更新时间",
    )
