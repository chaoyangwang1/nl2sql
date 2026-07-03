"""SQL 安全校验与数据访问层测试"""
import pytest
import re

# 直接复制生产代码中的正则和函数，避免导入异步依赖
SQL_DANGEROUS_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|TRUNCATE|GRANT|REVOKE|LOAD_FILE|INTO\s+OUTFILE|INTO\s+DUMPFILE)\b",
    re.IGNORECASE
)


def _ensure_select_only(sql: str) -> None:
    stripped = sql.strip().rstrip(";").strip()
    if not stripped.upper().startswith("SELECT"):
        raise ValueError("仅允许执行 SELECT 查询语句")
    if SQL_DANGEROUS_PATTERN.search(stripped):
        raise ValueError("SQL 包含禁止的危险操作关键词")


class TestEnsureSelectOnly:
    """测试 SQL 安全校验函数"""

    def test_simple_select_passes(self):
        _ensure_select_only("SELECT * FROM users")

    def test_select_with_join_passes(self):
        _ensure_select_only("SELECT a.*, b.name FROM fact_order a JOIN dim_region b ON a.region_id = b.region_id")

    def test_select_with_subquery_passes(self):
        _ensure_select_only("SELECT * FROM (SELECT region_id, SUM(amount) FROM orders GROUP BY region_id) t")

    def test_select_with_where_passes(self):
        _ensure_select_only("SELECT * FROM orders WHERE date >= '2025-01-01'")

    def test_trailing_semicolon_handled(self):
        _ensure_select_only("SELECT * FROM users;")

    def test_insert_blocked(self):
        """INSERT 应以非 SELECT 语句被拦截（第一道防线）"""
        with pytest.raises(ValueError, match="仅允许执行 SELECT"):
            _ensure_select_only("INSERT INTO users VALUES (1, 'test')")

    def test_update_blocked(self):
        with pytest.raises(ValueError, match="仅允许执行 SELECT"):
            _ensure_select_only("UPDATE users SET name = 'hack' WHERE id = 1")

    def test_delete_blocked(self):
        with pytest.raises(ValueError, match="仅允许执行 SELECT"):
            _ensure_select_only("DELETE FROM users WHERE id = 1")

    def test_drop_blocked(self):
        with pytest.raises(ValueError, match="仅允许执行 SELECT"):
            _ensure_select_only("DROP TABLE users")

    def test_create_blocked(self):
        with pytest.raises(ValueError, match="仅允许执行 SELECT"):
            _ensure_select_only("CREATE TABLE hack (id INT)")

    def test_alter_blocked(self):
        with pytest.raises(ValueError, match="仅允许执行 SELECT"):
            _ensure_select_only("ALTER TABLE users ADD COLUMN hack VARCHAR(255)")

    def test_truncate_blocked(self):
        with pytest.raises(ValueError, match="仅允许执行 SELECT"):
            _ensure_select_only("TRUNCATE TABLE users")

    def test_grant_blocked(self):
        with pytest.raises(ValueError, match="仅允许执行 SELECT"):
            _ensure_select_only("GRANT ALL ON *.* TO 'hacker'")

    def test_into_outfile_blocked(self):
        """INTO OUTFILE 即使以 SELECT 开头也应被拦截（第二道防线）"""
        with pytest.raises(ValueError, match="危险操作"):
            _ensure_select_only("SELECT * FROM users INTO OUTFILE '/tmp/hack.txt'")

    def test_upper_case_attack(self):
        """SELECT 后拼接 DROP — 第二道防线拦截"""
        with pytest.raises(ValueError, match="危险操作"):
            _ensure_select_only("SELECT * FROM users; DROP TABLE users")

    def test_mixed_case_attack(self):
        """混合大小写 — IGNORECASE 正则生效"""
        with pytest.raises(ValueError, match="危险操作"):
            _ensure_select_only("SELECT * FROM users; drop TABLE users")

    def test_not_starting_with_select(self):
        """不以 SELECT 开头的语句"""
        with pytest.raises(ValueError, match="仅允许执行 SELECT"):
            _ensure_select_only("SHOW TABLES")

    def test_empty_string(self):
        with pytest.raises(ValueError, match="仅允许执行 SELECT"):
            _ensure_select_only("")

    def test_select_with_comment_attack(self):
        """SELECT 中嵌入攻击语句"""
        with pytest.raises(ValueError, match="危险操作"):
            _ensure_select_only("SELECT * FROM users; /* comment */ DROP TABLE users")


class TestDangerousPatternCoverage:
    """测试正则表达式覆盖所有危险关键词"""

    def test_all_keywords_covered(self):
        keywords = [
            "INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "ALTER",
            "TRUNCATE", "GRANT", "REVOKE", "LOAD_FILE",
        ]
        for kw in keywords:
            sql = f"SELECT * FROM users; {kw} something"
            assert SQL_DANGEROUS_PATTERN.search(sql) is not None, f"关键词 {kw} 未被正则匹配"

    def test_into_outfile_covered(self):
        assert SQL_DANGEROUS_PATTERN.search("SELECT * INTO OUTFILE '/tmp/x'") is not None

    def test_into_dumpfile_covered(self):
        assert SQL_DANGEROUS_PATTERN.search("SELECT * INTO DUMPFILE '/tmp/x'") is not None

    def test_safe_sql_not_falsely_matched(self):
        """验证语义安全的 SQL 不被误杀"""
        safe_sqls = [
            "SELECT COUNT(*) FROM updates",           # updates 包含 UPDATE 但 \b 边界防止误匹配
            "SELECT id, grant_amount FROM grants",     # grant_amount 包含 GRANT 但 \b 边界防止误匹配
            "SELECT * FROM create_history",            # create_history 包含 CREATE 但 \b 边界防止误匹配
        ]
        for sql in safe_sqls:
            assert SQL_DANGEROUS_PATTERN.search(sql) is None, f"安全SQL被误匹配: {sql}"
