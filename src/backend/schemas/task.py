from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: int
    due_date: datetime
    house_id: UUID
    assigned_to: Optional[list[UUID]] = None
    created_by: UUID


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None
    due_date: Optional[datetime] = None
    house_id: Optional[UUID] = None
    assigned_to: Optional[list[UUID]] = None


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str] = None
    status: int
    due_date: datetime
    house_id: UUID
    assigned_to: list[UUID] = Field(default_factory=list)
    created_by: UUID
