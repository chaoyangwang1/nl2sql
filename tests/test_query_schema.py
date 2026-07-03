"""查询接口 Schema 验证测试"""
import pytest
from pydantic import ValidationError

from app.api.schemas.query_schema import QuerySchema


class TestQuerySchema:
    """测试查询请求体校验"""

    def test_valid_query_passes(self):
        """正常查询应通过校验"""
        schema = QuerySchema(query="统计去年的销售额")
        assert schema.query == "统计去年的销售额"

    def test_empty_query_blocked(self):
        """空查询应被拒绝"""
        with pytest.raises(ValidationError):
            QuerySchema(query="")

    def test_whitespace_only_blocked(self):
        """纯空格查询应被拒绝"""
        with pytest.raises(ValidationError):
            QuerySchema(query="   ")

    def test_too_long_query_blocked(self):
        """超过 500 字符的查询应被拒绝"""
        with pytest.raises(ValidationError):
            QuerySchema(query="长" * 501)

    def test_exactly_500_chars_passes(self):
        """刚好 500 字符应通过"""
        query = "查" * 500
        schema = QuerySchema(query=query)
        assert len(schema.query) == 500

    def test_whitespace_stripped(self):
        """前后空格应被自动去除"""
        schema = QuerySchema(query="  统计销售额  ")
        assert schema.query == "统计销售额"

    def test_special_chars_allowed(self):
        """SQL 相关的特殊字符应允许（校验不应过度限制）"""
        schema = QuerySchema(query="查询金额>100的订单")
        assert ">" in schema.query

    def test_english_query_passes(self):
        """英文查询应通过"""
        schema = QuerySchema(query="Show me total sales by region")
        assert schema.query == "Show me total sales by region"
