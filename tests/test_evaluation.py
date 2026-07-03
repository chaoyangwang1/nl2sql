"""SQL 质量评估逻辑单元测试"""
import pytest


def calc_table_recall(expected_tables: list[str], generated_sql: str) -> float:
    """计算表召回率"""
    if not expected_tables:
        return 1.0
    sql_lower = generated_sql.lower()
    return sum(1 for t in expected_tables if t.lower() in sql_lower) / len(expected_tables)


def calc_column_recall(expected_columns: list[str], generated_sql: str) -> float:
    """计算列召回率"""
    if not expected_columns:
        return 1.0
    sql_lower = generated_sql.lower()
    return sum(1 for c in expected_columns if c.lower() in sql_lower) / len(expected_columns)


def calc_keyword_match(expected_keywords: list[str], generated_sql: str) -> float:
    """计算关键字匹配率"""
    if not expected_keywords:
        return 1.0
    sql_upper = generated_sql.upper()
    return sum(1 for k in expected_keywords if k.upper() in sql_upper) / len(expected_keywords)


def is_evaluation_passed(execution_success: bool, table_recall: float, column_recall: float) -> bool:
    """判定评估是否通过"""
    return execution_success and table_recall >= 0.5 and column_recall >= 0.5


def classify_failure(is_passed: bool, sql_valid: bool, execution_success: bool) -> str | None:
    """分类失败原因"""
    if is_passed:
        return None
    if not sql_valid:
        return "sql_error"
    if not execution_success:
        return "execution_error"
    return "low_recall"


class TestRecallCalculation:
    """测试召回率计算逻辑"""

    def test_full_recall(self):
        sql = "SELECT region_name, SUM(order_amount) FROM fact_order JOIN dim_region ON fact_order.region_id = dim_region.region_id GROUP BY region_name"
        assert calc_table_recall(["fact_order", "dim_region"], sql) == 1.0
        assert calc_column_recall(["region_name", "order_amount"], sql) == 1.0

    def test_partial_table_recall(self):
        sql = "SELECT * FROM fact_order"
        assert calc_table_recall(["fact_order", "dim_region"], sql) == 0.5

    def test_partial_column_recall(self):
        sql = "SELECT region_name FROM dim_region"
        assert calc_column_recall(["region_name", "order_amount"], sql) == 0.5

    def test_zero_recall(self):
        sql = "SELECT * FROM other_table"
        assert calc_table_recall(["fact_order"], sql) == 0.0

    def test_empty_expected_defaults_to_one(self):
        """如果没有期望值，召回率默认为 1.0"""
        assert calc_table_recall([], "SELECT * FROM anything") == 1.0
        assert calc_column_recall([], "SELECT * FROM anything") == 1.0
        assert calc_keyword_match([], "SELECT * FROM anything") == 1.0

    def test_case_insensitive_match(self):
        """表名和列名匹配应不区分大小写"""
        sql = "select REGION_NAME from FACT_ORDER"
        assert calc_table_recall(["fact_order"], sql) == 1.0
        assert calc_column_recall(["region_name"], sql) == 1.0

    def test_keyword_match_case_insensitive(self):
        """关键字匹配应不区分大小写"""
        sql = "SELECT SUM(order_amount) FROM fact_order"
        assert calc_keyword_match(["SUM", "GROUP BY"], sql) == 0.5


class TestPassCriteria:
    """测试通过标准判定"""

    def test_all_conditions_met_passes(self):
        assert is_evaluation_passed(True, 1.0, 1.0) is True

    def test_execution_failed_fails(self):
        assert is_evaluation_passed(False, 1.0, 1.0) is False

    def test_low_table_recall_fails(self):
        assert is_evaluation_passed(True, 0.4, 1.0) is False

    def test_low_column_recall_fails(self):
        assert is_evaluation_passed(True, 1.0, 0.3) is False

    def test_boundary_table_recall_passes(self):
        """表召回率恰好 0.5 应通过"""
        assert is_evaluation_passed(True, 0.5, 1.0) is True

    def test_boundary_column_recall_passes(self):
        """列召回率恰好 0.5 应通过"""
        assert is_evaluation_passed(True, 1.0, 0.5) is True


class TestFailureClassification:
    """测试失败原因分类"""

    def test_passed_no_failure(self):
        assert classify_failure(True, True, True) is None

    def test_sql_error_classification(self):
        assert classify_failure(False, False, False) == "sql_error"

    def test_execution_error_classification(self):
        assert classify_failure(False, True, False) == "execution_error"

    def test_low_recall_classification(self):
        """SQL 有效、执行成功但不满足召回率——归因为召回不足"""
        assert classify_failure(False, True, True) == "low_recall"

    def test_sql_error_overrides_others(self):
        """sql_error 优先级最高（SQL 都不对，不用看执行和召回）"""
        assert classify_failure(False, False, True) == "sql_error"
