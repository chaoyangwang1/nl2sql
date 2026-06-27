from datetime import datetime

from sqlalchemy import String, Text, DateTime, SmallInteger, ForeignKey
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MetaColumnConfig(Base):
    __tablename__ = "meta_column_config"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
        comment="自增主键",
    )
    table_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="关联 meta_table_config.name",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="列名",
    )
    role: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="列角色（primary_key/foreign_key/dimension/measure）",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        comment="列描述",
    )
    alias: Mapped[list | None] = mapped_column(
        JSON,
        comment='别名列表，如 ["省份","省"]',
    )
    sync: Mapped[bool] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default="0",
        comment="是否同步取值到 ES（0=否，1=是）",
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
