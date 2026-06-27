from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from app.api.dependencies import get_meta_config_service
from app.api.schemas.meta_config_schema import (
    BuildResponse,
    MetaColumnConfigCreate,
    MetaColumnConfigResponse,
    MetaColumnConfigUpdate,
    MetaMetricConfigCreate,
    MetaMetricConfigResponse,
    MetaMetricConfigUpdate,
    MetaTableConfigCreate,
    MetaTableConfigListItem,
    MetaTableConfigResponse,
    MetaTableConfigUpdate,
)
from app.services.meta_config_service import MetaConfigService

meta_config_router = APIRouter(prefix="/api/meta-config", tags=["元数据配置管理"])


# ===========================================================
# 表配置接口
# ===========================================================

@meta_config_router.get("/tables", response_model=list[MetaTableConfigListItem])
async def list_tables(
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """查询所有表配置"""
    return await service.list_tables()


@meta_config_router.get("/tables/{name}", response_model=MetaTableConfigResponse)
async def get_table(
    name: str,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """查询单张表配置（含列）"""
    result = await service.get_table(name)
    if not result:
        raise HTTPException(status_code=404, detail=f"表 '{name}' 不存在")
    return result


@meta_config_router.post("/tables", response_model=MetaTableConfigListItem, status_code=201)
async def create_table(
    data: MetaTableConfigCreate,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """新增表配置"""
    return await service.create_table(data)


@meta_config_router.put("/tables/{name}", response_model=MetaTableConfigListItem)
async def update_table(
    name: str,
    data: MetaTableConfigUpdate,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """修改表配置"""
    result = await service.update_table(name, data)
    if not result:
        raise HTTPException(status_code=404, detail=f"表 '{name}' 不存在")
    return result


@meta_config_router.delete("/tables/{name}", status_code=204)
async def delete_table(
    name: str,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """删除表配置（级联删除列）"""
    deleted = await service.delete_table(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"表 '{name}' 不存在")


# ===========================================================
# 列配置接口
# ===========================================================

@meta_config_router.get(
    "/tables/{table_name}/columns", response_model=list[MetaColumnConfigResponse]
)
async def list_columns(
    table_name: str,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """查询某表所有列"""
    return await service.list_columns(table_name)


@meta_config_router.post(
    "/tables/{table_name}/columns",
    response_model=MetaColumnConfigResponse,
    status_code=201,
)
async def create_column(
    table_name: str,
    data: MetaColumnConfigCreate,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """新增列"""
    return await service.create_column(table_name, data)


@meta_config_router.put("/columns/{column_id}", response_model=MetaColumnConfigResponse)
async def update_column(
    column_id: int,
    data: MetaColumnConfigUpdate,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """修改列"""
    result = await service.update_column(column_id, data)
    if not result:
        raise HTTPException(status_code=404, detail=f"列 ID={column_id} 不存在")
    return result


@meta_config_router.delete("/columns/{column_id}", status_code=204)
async def delete_column(
    column_id: int,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """删除列"""
    deleted = await service.delete_column(column_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"列 ID={column_id} 不存在")


# ===========================================================
# 指标配置接口
# ===========================================================

@meta_config_router.get("/metrics", response_model=list[MetaMetricConfigResponse])
async def list_metrics(
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """查询所有指标"""
    return await service.list_metrics()


@meta_config_router.post(
    "/metrics", response_model=MetaMetricConfigResponse, status_code=201
)
async def create_metric(
    data: MetaMetricConfigCreate,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """新增指标"""
    return await service.create_metric(data)


@meta_config_router.put("/metrics/{name}", response_model=MetaMetricConfigResponse)
async def update_metric(
    name: str,
    data: MetaMetricConfigUpdate,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """修改指标"""
    result = await service.update_metric(name, data)
    if not result:
        raise HTTPException(status_code=404, detail=f"指标 '{name}' 不存在")
    return result


@meta_config_router.delete("/metrics/{name}", status_code=204)
async def delete_metric(
    name: str,
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """删除指标（级联删除关联）"""
    deleted = await service.delete_metric(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"指标 '{name}' 不存在")


# ===========================================================
# 构建元知识库接口
# ===========================================================

@meta_config_router.post("/build", response_model=BuildResponse)
async def build_meta_knowledge(
    service: MetaConfigService = Depends(get_meta_config_service),
):
    """触发元知识库构建（从数据库配置读取）"""
    result = await service.build_meta_knowledge()
    return BuildResponse(**result)
