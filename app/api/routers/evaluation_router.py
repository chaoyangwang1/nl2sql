from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Depends

from app.api.dependencies import get_evaluation_service
from app.api.schemas.evaluation_schema import (
    EvalResultResponse,
    EvalRunDetailResponse,
    EvalRunResponse,
    EvalRunTriggerResponse,
    GoldenQuestionCreate,
    GoldenQuestionResponse,
    GoldenQuestionUpdate,
)
from app.services.evaluation_service import EvaluationService

evaluation_router = APIRouter(prefix="/api/evaluation", tags=["SQL质量评估"])


# ============================================================
# 标准问题集管理
# ============================================================

@evaluation_router.get("/questions", response_model=list[GoldenQuestionResponse])
async def list_questions(
    service: EvaluationService = Depends(get_evaluation_service),
):
    """列出所有标准问题"""
    return await service.list_questions()


@evaluation_router.post("/questions", response_model=GoldenQuestionResponse, status_code=201)
async def create_question(
    data: GoldenQuestionCreate,
    service: EvaluationService = Depends(get_evaluation_service),
):
    """新增标准问题"""
    return await service.create_question(data)


@evaluation_router.put("/questions/{question_id}", response_model=GoldenQuestionResponse)
async def update_question(
    question_id: str,
    data: GoldenQuestionUpdate,
    service: EvaluationService = Depends(get_evaluation_service),
):
    """修改标准问题"""
    result = await service.update_question(question_id, data)
    if not result:
        raise HTTPException(status_code=404, detail=f"问题 '{question_id}' 不存在")
    return result


@evaluation_router.delete("/questions/{question_id}", status_code=204)
async def delete_question(
    question_id: str,
    service: EvaluationService = Depends(get_evaluation_service),
):
    """删除标准问题"""
    if not await service.delete_question(question_id):
        raise HTTPException(status_code=404, detail=f"问题 '{question_id}' 不存在")


# ============================================================
# 评估运行
# ============================================================

@evaluation_router.post("/run", response_model=EvalRunTriggerResponse)
async def trigger_evaluation(
    run_name: str | None = Query(None, description="运行名称，不填则自动生成"),
    service: EvaluationService = Depends(get_evaluation_service),
):
    """触发一次完整的 SQL 质量评估"""
    return await service.run_evaluation(run_name)


@evaluation_router.get("/runs", response_model=list[EvalRunResponse])
async def list_runs(
    service: EvaluationService = Depends(get_evaluation_service),
):
    """查看所有评估运行记录"""
    return await service.list_runs()


@evaluation_router.get("/runs/{run_id}", response_model=EvalRunDetailResponse)
async def get_run_detail(
    run_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
):
    """查看评估运行详情（含所有结果 + 失败结果）"""
    result = await service.get_run_detail(run_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"运行记录 ID={run_id} 不存在")
    return result


@evaluation_router.post("/runs/{run_id}/retry/{question_id}", response_model=EvalResultResponse)
async def retry_single_question(
    run_id: int,
    question_id: str,
    service: EvaluationService = Depends(get_evaluation_service),
):
    """重试某个失败的单题"""
    result = await service.retry_single_question(run_id, question_id)
    if not result:
        raise HTTPException(status_code=404, detail="运行记录或问题不存在")
    return result
