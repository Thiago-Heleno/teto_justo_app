from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class TaskCreate(BaseModel):
    title: str
    description: str
    status: int
    due_date: datetime
    house_id: UUID
    assigned_to: UUID
    created_by: UUID


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[int] = None
    due_date: Optional[datetime] = None
    house_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: str
    status: int
    due_date: datetime
    house_id: UUID
    assigned_to: Optional[UUID] = None
    created_by: UUID
