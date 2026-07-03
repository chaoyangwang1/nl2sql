from pydantic import BaseModel, Field, field_validator


class QuerySchema(BaseModel):
    query: str = Field(min_length=1, max_length=500)

    @field_validator('query', mode='after')
    @classmethod
    def validate_query_not_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError('查询内容不能为空或仅包含空白字符')
        return stripped
