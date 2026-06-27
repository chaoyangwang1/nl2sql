import json
import time
from contextlib import nullcontext
from datetime import datetime

from app.api.schemas.evaluation_schema import (
    EvalResultResponse,
    EvalRunDetailResponse,
    EvalRunResponse,
    EvalRunTriggerResponse,
    GoldenQuestionCreate,
    GoldenQuestionResponse,
    GoldenQuestionUpdate,
)
from app.core.log import logger
from app.repositories.mysql.meta.evaluation_repository import EvaluationRepository
from app.services.query_service import QueryService


class EvaluationService:
    def __init__(
        self,
        eval_repo: EvaluationRepository,
        query_service: QueryService,
    ):
        self.eval_repo = eval_repo
        self.query_service = query_service

    def _tx_context(self):
        """返回安全的事务上下文：已在事务中则跳过 begin"""
        session = self.eval_repo.session
        if session.in_transaction():
            return nullcontext()
        return session.begin()

    async def _commit_if_needed(self):
        """已在事务中时显式 commit，避免 nullcontext 路径不提交"""
        session = self.eval_repo.session
        if session.in_transaction():
            await session.commit()

    # ============================================================
    # 标准问题集 CRUD（透传 repo）
    # ============================================================

    async def list_questions(self) -> list[GoldenQuestionResponse]:
        questions = await self.eval_repo.list_questions()
        return [GoldenQuestionResponse.model_validate(q) for q in questions]

    async def create_question(self, data: GoldenQuestionCreate) -> GoldenQuestionResponse:
        async with self._tx_context():
            model = await self.eval_repo.create_question(**data.model_dump())
            await self._commit_if_needed()
        return GoldenQuestionResponse.model_validate(model)

    async def update_question(self, question_id: str, data: GoldenQuestionUpdate) -> GoldenQuestionResponse | None:
        async with self._tx_context():
            model = await self.eval_repo.update_question(
                question_id, **data.model_dump(exclude_unset=True)
            )
            await self._commit_if_needed()
        if not model:
            return None
        return GoldenQuestionResponse.model_validate(model)

    async def delete_question(self, question_id: str) -> bool:
        async with self._tx_context():
            result = await self.eval_repo.delete_question(question_id)
            await self._commit_if_needed()
            return result

    # ============================================================
    # 评估运行查询
    # ============================================================

    async def list_runs(self) -> list[EvalRunResponse]:
        runs = await self.eval_repo.list_runs()
        return [EvalRunResponse.model_validate(r) for r in runs]

    async def get_run_detail(self, run_id: int) -> EvalRunDetailResponse | None:
        run = await self.eval_repo.get_run(run_id)
        if not run:
            return None
        results = await self.eval_repo.get_results_by_run(run_id)
        failed = await self.eval_repo.get_failed_results(run_id)
        resp = EvalRunDetailResponse.model_validate(run)
        resp.results = [EvalResultResponse.model_validate(r) for r in results]
        resp.failed_results = [EvalResultResponse.model_validate(r) for r in failed]
        return resp

    # ============================================================
    # 单题重试
    # ============================================================

    async def retry_single_question(self, run_id: int, question_id: str) -> EvalResultResponse | None:
        """重试某个失败的单题，并更新运行汇总"""
        run = await self.eval_repo.get_run(run_id)
        if not run:
            return None
        q = await self.eval_repo.get_question(question_id)
        if not q:
            return None

        # 执行单题查询
        q_start = time.perf_counter()
        generated_sql = ""
        execution_success = False
        execution_error = None
        result_data = None
        sql_valid = False

        try:
            async for raw_chunk in self.query_service.query(q.question):
                line = raw_chunk.strip()
                if not line.startswith("data:"):
                    continue
                try:
                    data = json.loads(line[5:].strip())
                except (json.JSONDecodeError, AttributeError):
                    continue
                if data.get("type") == "sql":
                    generated_sql = data.get("sql", "")
                if data.get("type") == "progress" and data.get("step") == "验证SQL":
                    sql_valid = data.get("status") == "success"
                if data.get("type") == "result":
                    result_data = data.get("data")
                    execution_success = True
                if data.get("type") == "error":
                    execution_error = data.get("message")
        except Exception as e:
            execution_error = str(e)
            logger.error(f"重试问题 [{question_id}] 异常: {e}")

        elapsed = round(time.perf_counter() - q_start, 3)

        # 计算指标
        sql_lower = (generated_sql or "").lower()
        expected_tables = q.expected_tables or []
        expected_columns = q.expected_columns or []
        expected_keywords = q.expected_keywords or []

        table_recall = (
            sum(1 for t in expected_tables if t.lower() in sql_lower) / len(expected_tables)
            if expected_tables else 1.0
        )
        column_recall = (
            sum(1 for c in expected_columns if c.lower() in sql_lower) / len(expected_columns)
            if expected_columns else 1.0
        )
        keyword_match = (
            sum(1 for k in expected_keywords if k.upper() in (generated_sql or "").upper()) / len(expected_keywords)
            if expected_keywords else 1.0
        )

        is_passed = execution_success and table_recall >= 0.5 and column_recall >= 0.5
        failure_reason = None
        if not is_passed:
            if not sql_valid:
                failure_reason = "sql_error"
            elif not execution_success:
                failure_reason = "execution_error"
            else:
                failure_reason = "low_recall"

        # 获取该 run 之前的结果，计算新的汇总
        old_results = await self.eval_repo.get_results_by_run(run_id)
        old_passed = sum(1 for r in old_results if r.is_passed and r.question_id != question_id)
        old_failed = sum(1 for r in old_results if not r.is_passed and r.question_id != question_id)
        new_passed = old_passed + (1 if is_passed else 0)
        new_failed = old_failed + (0 if is_passed else 1)
        total = len(old_results)
        pass_rate = round((new_passed / total * 100), 2) if total else 0

        # 保存新结果（覆盖旧记录）
        async with self._tx_context():
            # 先删除旧的同 question_id 记录
            from sqlalchemy import delete
            from app.models.eval_result_mysql import EvalResultMySQL
            await self.eval_repo.session.execute(
                delete(EvalResultMySQL).where(
                    EvalResultMySQL.run_id == run_id,
                    EvalResultMySQL.question_id == question_id,
                )
            )
            saved = await self.eval_repo.save_result(
                run_id=run_id,
                question_id=q.question_id,
                question=q.question,
                generated_sql=generated_sql,
                reference_sql=q.reference_sql,
                execution_success=execution_success,
                sql_valid=sql_valid,
                table_recall=table_recall,
                column_recall=column_recall,
                keyword_match=keyword_match,
                execution_error=execution_error,
                result_data=result_data,
                elapsed_seconds=elapsed,
                is_passed=is_passed,
                failure_reason=failure_reason,
            )
            # 更新汇总
            await self.eval_repo.update_run(
                run_id,
                passed=new_passed,
                failed=new_failed,
                pass_rate=pass_rate,
            )
            await self._commit_if_needed()

        logger.info(f"重试问题 [{question_id}]: {'通过' if is_passed else '失败'}, 耗时 {elapsed}s")
        return EvalResultResponse.model_validate(saved)

    # ============================================================
    # 执行评估（核心）
    # ============================================================

    async def run_evaluation(self, run_name: str | None = None) -> EvalRunTriggerResponse:
        """运行完整的 SQL 质量评估"""
        try:
            # 1. 加载所有标准问题
            questions = await self.eval_repo.list_questions()
            if not questions:
                return EvalRunTriggerResponse(status="error", message="标准问题集为空，请先添加标准问题")

            if not run_name:
                run_name = f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # 2. 创建运行记录
            async with self._tx_context():
                run = await self.eval_repo.create_run(run_name, len(questions))
                run_id = run.id
                await self._commit_if_needed()

            logger.info(f"开始评估运行 [{run_name}], 共 {len(questions)} 题")

            passed = 0
            failed = 0
            total_latency = 0.0

            # 3. 遍历每题
            for q in questions:
                q_start = time.perf_counter()
                generated_sql = ""
                execution_success = False
                execution_error = None
                result_data = None
                sql_valid = False

                try:
                    # 调用 query_service 收集 SSE chunks
                    async for raw_chunk in self.query_service.query(q.question):
                        line = raw_chunk.strip()
                        if not line.startswith("data:"):
                            continue
                        try:
                            data = json.loads(line[5:].strip())
                        except (json.JSONDecodeError, AttributeError):
                            continue

                        # 捕获生成的 SQL
                        if data.get("type") == "sql":
                            generated_sql = data.get("sql", "")

                        # 检测 SQL 验证状态
                        if data.get("type") == "progress" and data.get("step") == "验证SQL":
                            sql_valid = data.get("status") == "success"

                        # 执行结果
                        if data.get("type") == "result":
                            result_data = data.get("data")
                            execution_success = True

                        # 错误信息
                        if data.get("type") == "error":
                            execution_error = data.get("message")

                except Exception as e:
                    execution_error = str(e)
                    logger.error(f"评估问题 [{q.question_id}] 异常: {e}")

                elapsed = round(time.perf_counter() - q_start, 3)
                total_latency += elapsed

                # 4. 计算评估指标
                sql_lower = (generated_sql or "").lower()
                expected_tables = q.expected_tables or []
                expected_columns = q.expected_columns or []
                expected_keywords = q.expected_keywords or []

                table_recall = (
                    sum(1 for t in expected_tables if t.lower() in sql_lower) / len(expected_tables)
                    if expected_tables else 1.0
                )
                column_recall = (
                    sum(1 for c in expected_columns if c.lower() in sql_lower) / len(expected_columns)
                    if expected_columns else 1.0
                )
                keyword_match = (
                    sum(1 for k in expected_keywords if k.upper() in (generated_sql or "").upper()) / len(expected_keywords)
                    if expected_keywords else 1.0
                )

                # 5. 判定是否通过
                is_passed = execution_success and table_recall >= 0.5 and column_recall >= 0.5

                # 6. 分类失败原因
                failure_reason = None
                if not is_passed:
                    if not sql_valid:
                        failure_reason = "sql_error"
                    elif not execution_success:
                        failure_reason = "execution_error"
                    else:
                        failure_reason = "low_recall"

                if is_passed:
                    passed += 1
                else:
                    failed += 1

                # 7. 保存单题结果
                async with self._tx_context():
                    await self.eval_repo.save_result(
                        run_id=run_id,
                        question_id=q.question_id,
                        question=q.question,
                        generated_sql=generated_sql,
                        reference_sql=q.reference_sql,
                        execution_success=execution_success,
                        sql_valid=sql_valid,
                        table_recall=table_recall,
                        column_recall=column_recall,
                        keyword_match=keyword_match,
                        execution_error=execution_error,
                        result_data=result_data,
                        elapsed_seconds=elapsed,
                        is_passed=is_passed,
                        failure_reason=failure_reason,
                    )
                    await self._commit_if_needed()

            # 8. 更新运行汇总
            avg_latency = total_latency / len(questions) if questions else 0
            pass_rate = round((passed / len(questions) * 100), 2) if questions else 0

            async with self._tx_context():
                await self.eval_repo.update_run(
                    run_id,
                    passed=passed,
                    failed=failed,
                    pass_rate=pass_rate,
                    avg_latency=avg_latency,
                    status="completed",
                    finished_at=datetime.now(),
                )
                await self._commit_if_needed()

            logger.info(f"评估运行 [{run_name}] 完成: {passed}/{len(questions)} 通过 ({pass_rate}%)")
            return EvalRunTriggerResponse(
                status="success",
                message=f"评估完成: {passed}/{len(questions)} 通过 ({pass_rate}%)",
                run_id=run_id,
            )

        except Exception as e:
            logger.error(f"评估运行失败: {e}")
            return EvalRunTriggerResponse(status="error", message=str(e))
