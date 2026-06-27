from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.eval_golden_question_mysql import EvalGoldenQuestionMySQL
from app.models.eval_result_mysql import EvalResultMySQL
from app.models.eval_run_mysql import EvalRunMySQL


class EvaluationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    # ============================================================
    # 标准问题集 CRUD
    # ============================================================

    async def list_questions(self) -> list[EvalGoldenQuestionMySQL]:
        result = await self.session.execute(
            select(EvalGoldenQuestionMySQL).order_by(EvalGoldenQuestionMySQL.id)
        )
        return list(result.scalars().all())

    async def get_question(self, question_id: str) -> EvalGoldenQuestionMySQL | None:
        result = await self.session.execute(
            select(EvalGoldenQuestionMySQL).where(EvalGoldenQuestionMySQL.question_id == question_id)
        )
        return result.scalar_one_or_none()

    async def create_question(self, **kwargs) -> EvalGoldenQuestionMySQL:
        model = EvalGoldenQuestionMySQL(**kwargs)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_question(self, question_id: str, **kwargs) -> EvalGoldenQuestionMySQL | None:
        model = await self.get_question(question_id)
        if not model:
            return None
        for k, v in kwargs.items():
            if v is not None:
                setattr(model, k, v)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def delete_question(self, question_id: str) -> bool:
        model = await self.get_question(question_id)
        if not model:
            return False
        await self.session.delete(model)
        await self.session.flush()
        return True

    # ============================================================
    # 评估运行
    # ============================================================

    async def create_run(self, run_name: str, total: int) -> EvalRunMySQL:
        model = EvalRunMySQL(run_name=run_name, total_questions=total, status="running")
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def update_run(self, run_id: int, **kwargs) -> EvalRunMySQL | None:
        model = await self.session.get(EvalRunMySQL, run_id)
        if not model:
            return None
        for k, v in kwargs.items():
            if v is not None:
                setattr(model, k, v)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def list_runs(self) -> list[EvalRunMySQL]:
        result = await self.session.execute(
            select(EvalRunMySQL).order_by(EvalRunMySQL.id.desc())
        )
        return list(result.scalars().all())

    async def get_run(self, run_id: int) -> EvalRunMySQL | None:
        return await self.session.get(EvalRunMySQL, run_id)

    # ============================================================
    # 评估结果
    # ============================================================

    async def save_result(self, **kwargs) -> EvalResultMySQL:
        model = EvalResultMySQL(**kwargs)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return model

    async def get_results_by_run(self, run_id: int) -> list[EvalResultMySQL]:
        result = await self.session.execute(
            select(EvalResultMySQL)
            .where(EvalResultMySQL.run_id == run_id)
            .order_by(EvalResultMySQL.id)
        )
        return list(result.scalars().all())

    async def get_failed_results(self, run_id: int) -> list[EvalResultMySQL]:
        result = await self.session.execute(
            select(EvalResultMySQL)
            .where(EvalResultMySQL.run_id == run_id, EvalResultMySQL.is_passed == 0)
            .order_by(EvalResultMySQL.id)
        )
        return list(result.scalars().all())
