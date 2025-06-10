"""This module contains the Pydantic models for the API."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from id_generator import generate_message_id


class Assistant(BaseModel):
    name: str


class ChatSummary(BaseModel):
    id: str
    title: str
    last_updated: datetime


class SendMessageRequest(BaseModel):
    id: str = Field(default_factory=generate_message_id)
    content: str
    assistant: Optional[str] = None


class EditMessageRequest(BaseModel):
    content: str
