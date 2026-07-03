from fastapi import APIRouter, Request
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from starlette.responses import StreamingResponse

from app.api.dependencies import get_query_service
from app.api.schemas.query_schema import QuerySchema
from app.core.rate_limiter import query_rate_limiter
from app.services.query_service import QueryService

query_router = APIRouter()


@query_router.post("/api/query")
async def query(
    query: QuerySchema,
    request: Request,
    query_service: QueryService = Depends(get_query_service),
):
    # 限流：按客户端 IP 限制
    client_ip = request.client.host if request.client else "unknown"
    if not await query_rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={"detail": "请求过于频繁，请稍后重试", "type": "rate_limit"},
        )

    return StreamingResponse(
        query_service.query(query.query), media_type="text/event-stream"
    )
