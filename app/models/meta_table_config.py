from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MetaTableConfig(Base):
    __tablename__ = "meta_table_config"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
        comment="自增主键",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        nullable=False,
        comment="表名（如 dim_region）",
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="表角色（dim / fact）",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        comment="表描述",
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
