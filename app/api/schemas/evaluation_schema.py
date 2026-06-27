from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ============================================================
# 标准问题集 Schema
# ============================================================

class GoldenQuestionCreate(BaseModel):
    question_id: str = Field(..., max_length=32, description="问题编号，如 q001")
    question: str = Field(..., description="自然语言问题")
    difficulty: str = Field("medium", max_length=16, description="难度: easy/medium/hard")
    expected_tables: Optional[list[str]] = Field(None, description="期望引用的表名列表")
    expected_columns: Optional[list[str]] = Field(None, description="期望引用的列名列表")
    expected_keywords: Optional[list[str]] = Field(None, description="期望包含的 SQL 关键字")
    reference_sql: Optional[str] = Field(None, description="参考 SQL")


class GoldenQuestionUpdate(BaseModel):
    question: Optional[str] = Field(None, description="自然语言问题")
    difficulty: Optional[str] = Field(None, max_length=16, description="难度")
    expected_tables: Optional[list[str]] = Field(None, description="期望引用的表名列表")
    expected_columns: Optional[list[str]] = Field(None, description="期望引用的列名列表")
    expected_keywords: Optional[list[str]] = Field(None, description="期望包含的 SQL 关键字")
    reference_sql: Optional[str] = Field(None, description="参考 SQL")


class GoldenQuestionResponse(BaseModel):
    id: int
    question_id: str
    question: str
    difficulty: str
    expected_tables: Optional[list[str]] = None
    expected_columns: Optional[list[str]] = None
    expected_keywords: Optional[list[str]] = None
    reference_sql: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ============================================================
# 评估运行 Schema
# ============================================================

class EvalRunResponse(BaseModel):
    id: int
    run_name: str
    total_questions: int
    passed: int
    failed: int
    pass_rate: float
    avg_latency: float
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ============================================================
# 评估结果 Schema
# ============================================================

class EvalResultResponse(BaseModel):
    id: int
    run_id: int
    question_id: str
    question: str
    generated_sql: Optional[str] = None
    reference_sql: Optional[str] = None
    execution_success: bool
    sql_valid: bool
    table_recall: Optional[float] = None
    column_recall: Optional[float] = None
    keyword_match: Optional[float] = None
    execution_error: Optional[str] = None
    result_data: Optional[list | dict] = None
    elapsed_seconds: float
    is_passed: bool
    failure_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalRunDetailResponse(EvalRunResponse):
    results: list[EvalResultResponse] = []
    failed_results: list[EvalResultResponse] = []


# ============================================================
# 触发评估响应 Schema
# ============================================================

class EvalRunTriggerResponse(BaseModel):
    status: str
    message: str
    run_id: Optional[int] = None
