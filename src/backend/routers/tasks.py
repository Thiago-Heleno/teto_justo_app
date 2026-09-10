from uuid import UUID
from fastapi import APIRouter, Depends
from core.database import get_supabase
from schemas.task import TaskCreate, TaskResponse, TaskUpdate
from services.tasks import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(task: TaskCreate, supabase=Depends(get_supabase)):
    return TaskService(supabase).create_task(task)


@router.get("/", response_model=list[TaskResponse])
def get_tasks(skip: int = 0, limit: int = 100, supabase=Depends(get_supabase)):
    return TaskService(supabase).get_tasks(skip, limit)


@router.get("/house/{house_id}", response_model=list[TaskResponse])
def get_tasks_by_house(house_id: UUID, supabase=Depends(get_supabase)):
    return TaskService(supabase).get_tasks_by_house(house_id)


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: UUID, supabase=Depends(get_supabase)):
    return TaskService(supabase).get_task(task_id)


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(task_id: UUID, task: TaskUpdate, supabase=Depends(get_supabase)):
    return TaskService(supabase).update_task(task_id, task)


@router.delete("/{task_id}", response_model=bool)
def delete_task(task_id: UUID, supabase=Depends(get_supabase)):
    return TaskService(supabase).delete_task(task_id)
