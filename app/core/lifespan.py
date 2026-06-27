from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager
from app.core.log import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # FastAPI 应用启动前执行
    try:
        embedding_client_manager.init()
        qdrant_client_manager.init()
        es_client_manager.init()
        meta_mysql_client_manager.init()
        dw_mysql_client_manager.init()
        logger.info("所有客户端初始化成功")
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        raise RuntimeError(f"应用启动失败: {e}") from e

    yield

    # FastAPI 应用结束前执行
    clients = [
        ("qdrant", qdrant_client_manager),
        ("es", es_client_manager),
        ("meta_mysql", meta_mysql_client_manager),
        ("dw_mysql", dw_mysql_client_manager),
    ]
    for name, manager in clients:
        try:
            await manager.close()
        except Exception as e:
            logger.warning(f"关闭 {name} 客户端时出错: {e}")
