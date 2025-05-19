from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class Assistant(BaseModel):
    name: str


class ChatSummary(BaseModel):
    id: str
    title: str
    last_updated: datetime


class SendMessageRequest(BaseModel):
    content: str
    id: str
    assistant: Optional[str] = None
