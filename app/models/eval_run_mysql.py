from datetime import datetime

from sqlalchemy import String, Integer, DECIMAL, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EvalRunMySQL(Base):
    __tablename__ = "eval_run"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
        comment="自增主键",
    )
    run_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="运行名称，如 baseline_20260626",
    )
    total_questions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="总问题数",
    )
    passed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="通过数",
    )
    failed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="0",
        comment="失败数",
    )
    pass_rate: Mapped[float] = mapped_column(
        DECIMAL(5, 2),
        nullable=False,
        server_default="0.00",
        comment="通过率 %",
    )
    avg_latency: Mapped[float] = mapped_column(
        DECIMAL(8, 3),
        nullable=False,
        server_default="0.000",
        comment="平均延迟(秒)",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default="running",
        comment="running/completed/failed",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        comment="开始时间",
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        comment="结束时间",
    )
