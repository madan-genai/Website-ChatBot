from pydantic import BaseModel

class IndexRequest(BaseModel):
    url: str


class QueryRequest(BaseModel):
    index_id: str
    question: str