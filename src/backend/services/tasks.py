from uuid import UUID

from fastapi import HTTPException

from schemas.task import TaskCreate, TaskUpdate


FIELD_MAP = {
    "title": "nome",
    "description": "descricao",
    "status": "estado_atual",
    "due_date": "data_fim",
    "house_id": "fk_casa_id",
    "created_by": "fk_usuario_id",
}


class TaskService:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    @staticmethod
    def _to_database(data: dict) -> dict:
        return {
            FIELD_MAP[field]: value
            for field, value in data.items()
            if field in FIELD_MAP
        }

    def _get_raw_task(self, task_id: UUID):
        response = (
            self.supabase.table("tarefa")
            .select("*")
            .eq("id", str(task_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Tarefa nao encontrada.")
        return response.data[0]

    def _get_assigned_to(self, task_id: UUID | str):
        response = (
            self.supabase.table("atribuida")
            .select("fk_usuario_id")
            .eq("fk_tarefa_id", str(task_id))
            .execute()
        )
        return [row["fk_usuario_id"] for row in response.data]

    def _assign_to(
        self, task_id: UUID | str, user_ids: list[UUID | str]
    ):
        unique_user_ids = list(dict.fromkeys(str(user_id) for user_id in user_ids))
        if not unique_user_ids:
            return

        assignments = [
            {
                "fk_usuario_id": user_id,
                "fk_tarefa_id": str(task_id),
            }
            for user_id in unique_user_ids
        ]
        response = (
            self.supabase.table("atribuida")
            .insert(assignments)
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Erro ao atribuir responsaveis pela tarefa."
            )

    def _to_response(self, task: dict) -> dict:
        response = {
            "id": task["id"],
            **{field: task[column] for field, column in FIELD_MAP.items()},
        }
        response["assigned_to"] = self._get_assigned_to(task["id"])
        return response

    def create_task(self, task_data: TaskCreate):
        data = task_data.model_dump(mode="json")
        assigned_to = data.pop("assigned_to", None)
        response = (
            self.supabase.table("tarefa")
            .insert(self._to_database(data))
            .execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=500, detail="Erro ao criar tarefa no banco."
            )

        task = response.data[0]
        if assigned_to:
            self._assign_to(task["id"], assigned_to)
        return self._to_response(task)

    def get_task(self, task_id: UUID):
        return self._to_response(self._get_raw_task(task_id))

    def get_tasks(self, skip: int = 0, limit: int = 100):
        response = (
            self.supabase.table("tarefa")
            .select("*")
            .range(skip, skip + limit - 1)
            .execute()
        )
        return [self._to_response(task) for task in response.data]

    def get_tasks_by_house(self, house_id: UUID):
        response = (
            self.supabase.table("tarefa")
            .select("*")
            .eq("fk_casa_id", str(house_id))
            .execute()
        )
        return [self._to_response(task) for task in response.data]

    def update_task(self, task_id: UUID, task_data: TaskUpdate):
        self._get_raw_task(task_id)
        assigned_to_was_set = "assigned_to" in task_data.model_fields_set
        data = task_data.model_dump(
            mode="json", exclude_unset=True, exclude_none=True
        )
        assigned_to = data.pop("assigned_to", None)
        if not data and not assigned_to_was_set:
            raise HTTPException(
                status_code=400, detail="Nenhum dado para atualizacao."
            )

        if data:
            response = (
                self.supabase.table("tarefa")
                .update(self._to_database(data))
                .eq("id", str(task_id))
                .execute()
            )
            if not response.data:
                raise HTTPException(status_code=404, detail="Tarefa nao encontrada.")
        if assigned_to_was_set:
            (
                self.supabase.table("atribuida")
                .delete()
                .eq("fk_tarefa_id", str(task_id))
                .execute()
            )
            if assigned_to:
                self._assign_to(task_id, assigned_to)

        return self.get_task(task_id)

    def delete_task(self, task_id: UUID):
        self._get_raw_task(task_id)
        (
            self.supabase.table("atribuida")
            .delete()
            .eq("fk_tarefa_id", str(task_id))
            .execute()
        )
        response = (
            self.supabase.table("tarefa")
            .delete()
            .eq("id", str(task_id))
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Tarefa nao encontrada.")
        return True
