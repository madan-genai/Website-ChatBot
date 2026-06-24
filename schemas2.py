from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# ── Index ──────────────────────────────────────────────────────────────────
class IndexRequest(BaseModel):
    url: str


class ReindexRequest(BaseModel):
    url: str


# ── Chat ───────────────────────────────────────────────────────────────────
class QueryRequest(BaseModel):
    index_id:   str
    question:   str
    session_id: Optional[str] = "default"


# ── Chat History ───────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role:       str
    content:    str
    created_at: Optional[datetime] = None


class ChatHistoryResponse(BaseModel):
    index_id:   str
    session_id: str
    messages:   list[ChatMessage]
