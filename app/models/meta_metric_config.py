from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MetaMetricConfig(Base):
    __tablename__ = "meta_metric_config"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
        comment="自增主键",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        comment="指标名（如 GMV）",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        comment="指标描述",
    )
    alias: Mapped[list | None] = mapped_column(
        JSON,
        comment="别名列表",
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
