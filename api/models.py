import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Assistant(BaseModel):
    name: str


class ChatSummary(BaseModel):
    id: str
    title: str
    last_updated: datetime


class SendMessageRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()).replace("-", ""))
    content: str
    assistant: Optional[str] = None
