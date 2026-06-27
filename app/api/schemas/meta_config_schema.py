from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 列配置 Schema
# ============================================================

class MetaColumnConfigCreate(BaseModel):
    name: str = Field(..., max_length=128, description="列名")
    role: str = Field(..., max_length=32, description="列角色（primary_key/foreign_key/dimension/measure）")
    description: Optional[str] = Field(None, description="列描述")
    alias: Optional[list[str]] = Field(None, description="别名列表")
    sync: bool = Field(False, description="是否同步取值到 ES")


class MetaColumnConfigUpdate(BaseModel):
    role: Optional[str] = Field(None, max_length=32, description="列角色")
    description: Optional[str] = Field(None, description="列描述")
    alias: Optional[list[str]] = Field(None, description="别名列表")
    sync: Optional[bool] = Field(None, description="是否同步取值到 ES")


class MetaColumnConfigResponse(BaseModel):
    id: int
    table_name: str
    name: str
    role: str
    description: Optional[str] = None
    alias: Optional[list[str]] = None
    sync: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# 表配置 Schema
# ============================================================

class MetaTableConfigCreate(BaseModel):
    name: str = Field(..., max_length=128, description="表名")
    role: str = Field(..., max_length=32, description="表角色（dim / fact）")
    description: Optional[str] = Field(None, description="表描述")


class MetaTableConfigUpdate(BaseModel):
    role: Optional[str] = Field(None, max_length=32, description="表角色")
    description: Optional[str] = Field(None, description="表描述")


class MetaTableConfigResponse(BaseModel):
    id: int
    name: str
    role: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    columns: list[MetaColumnConfigResponse] = []

    model_config = {"from_attributes": True}


class MetaTableConfigListItem(BaseModel):
    id: int
    name: str
    role: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# 指标-列关联 Schema
# ============================================================

class MetaMetricColumnRelCreate(BaseModel):
    column_ref: str = Field(..., max_length=256, description="列引用，格式 table.column")


class MetaMetricColumnRelResponse(BaseModel):
    id: int
    metric_name: str
    column_ref: str

    model_config = {"from_attributes": True}


# ============================================================
# 指标配置 Schema
# ============================================================

class MetaMetricConfigCreate(BaseModel):
    name: str = Field(..., max_length=128, description="指标名")
    description: Optional[str] = Field(None, description="指标描述")
    alias: Optional[list[str]] = Field(None, description="别名列表")
    relevant_columns: Optional[list[str]] = Field(None, description="关联列列表，格式 table.column")


class MetaMetricConfigUpdate(BaseModel):
    description: Optional[str] = Field(None, description="指标描述")
    alias: Optional[list[str]] = Field(None, description="别名列表")
    relevant_columns: Optional[list[str]] = Field(None, description="关联列列表")


class MetaMetricConfigResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    alias: Optional[list[str]] = None
    relevant_columns: list[str] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# 构建响应 Schema
# ============================================================

class BuildResponse(BaseModel):
    status: str
    message: str
