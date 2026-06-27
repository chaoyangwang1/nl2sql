from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MetaMetricColumnRel(Base):
    __tablename__ = "meta_metric_column_rel"

    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True,
        comment="自增主键",
    )
    metric_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="关联 meta_metric_config.name",
    )
    column_ref: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="列引用，格式 table.column",
    )
