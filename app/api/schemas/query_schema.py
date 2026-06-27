from pydantic import BaseModel, Field


class QuerySchema(BaseModel):
    query: str = Field(min_length=1, max_length=500, strip_whitespace=True)
from pydantic import BaseModel


class QuerySchema(BaseModel):
    query: str
