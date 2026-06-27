import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routers.query_router import query_router
from app.api.routers.meta_config_router import meta_config_router
from app.api.routers.evaluation_router import evaluation_router
from app.core.context import request_id_ctx_var
from app.core.lifespan import lifespan
from app.core.log import logger

# 创建FastAPI应用，并注册生命周期函数
app = FastAPI(lifespan=lifespan) 

# 注册路由
app.include_router(query_router)
app.include_router(meta_config_router)
app.include_router(evaluation_router)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


# 添加中间件，在每个请求中生成唯一的request_id并记录请求耗时
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    # 调用路径函数之前
    request_id = str(uuid.uuid4())
    request_id_ctx_var.set(request_id)
    start_time = time.perf_counter()

    # 调用路径函数
    response = await call_next(request)

    # 调用路径函数之后，记录请求耗时
    elapsed = round(time.perf_counter() - start_time, 3)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {elapsed}s")
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(elapsed)
    return response


@app.get("/health")
async def health_check():
    """健康检查端点，检查各依赖服务的连通性"""
    from sqlalchemy import text as sa_text
    from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
    from app.clients.qdrant_client_manager import qdrant_client_manager
    from app.clients.es_client_manager import es_client_manager

    checks = {}

    # 检查 meta MySQL
    try:
        async with meta_mysql_client_manager.session_factory() as session:
            await session.execute(sa_text("SELECT 1"))
        checks["meta_mysql"] = "ok"
    except Exception as e:
        checks["meta_mysql"] = f"error: {e}"

    # 检查 dw MySQL
    try:
        async with dw_mysql_client_manager.session_factory() as session:
            await session.execute(sa_text("SELECT 1"))
        checks["dw_mysql"] = "ok"
    except Exception as e:
        checks["dw_mysql"] = f"error: {e}"

    # 检查 Qdrant
    try:
        await qdrant_client_manager.client.get_collections()
        checks["qdrant"] = "ok"
    except Exception as e:
        checks["qdrant"] = f"error: {e}"

    # 检查 Elasticsearch
    try:
        await es_client_manager.client.cluster.health()
        checks["elasticsearch"] = "ok"
    except Exception as e:
        checks["elasticsearch"] = f"error: {e}"

    # 判断整体状态
    all_healthy = all(v == "ok" for v in checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "healthy" if all_healthy else "degraded", "checks": checks}
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
