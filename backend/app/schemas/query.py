from pydantic import BaseModel, ConfigDict, Field


class QueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(..., min_length=3, max_length=1000, examples=["What is this document about?"])


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
