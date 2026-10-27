from uuid import UUID

from fastapi import HTTPException

from schemas.notificacao import NotificacaoTesteEntrada
from services.autorizacao import ServicoAutorizacaoCasa
from services.notificacao import ServicoNotificacao


_TITULOS = {
    "tarefa_atribuida": "Teste: nova tarefa",
    "tarefa_vence_hoje": "Teste: tarefa vence hoje",
    "tarefa_atrasada": "Teste: tarefa atrasada",
}


def enviar_notificacao_teste(supabase, id_usuario: UUID, dados: NotificacaoTesteEntrada) -> dict:
    tarefas = (
        supabase.table("tarefa").select("id,fk_casa_id")
        .eq("id", str(dados.tarefa_id)).execute()
    ).data or []
    if not tarefas:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    tarefa = tarefas[0]
    ServicoAutorizacaoCasa(supabase).garantir_acesso(tarefa["fk_casa_id"], id_usuario)
    atribuicoes = (
        supabase.table("atribuida").select("fk_usuario_id")
        .eq("fk_tarefa_id", str(dados.tarefa_id)).eq("fk_usuario_id", str(id_usuario))
        .limit(1).execute()
    ).data or []
    if not atribuicoes:
        raise HTTPException(status_code=403, detail="Escolha uma tarefa atribuída a você.")

    envio = ServicoNotificacao(supabase).enviar_push(
        [id_usuario], _TITULOS[dados.tipo],
        "Aviso de teste. Toque para abrir a tarefa."
        if dados.tipo == "tarefa_atribuida" else
        "Aviso de teste. A ação Concluir conclui a tarefa de verdade.",
        {
            "tipo": dados.tipo, "tarefa_id": str(dados.tarefa_id),
            "casa_id": str(tarefa["fk_casa_id"]),
        },
    )
    if not envio["aceitos"]:
        if envio["falhas"]:
            raise HTTPException(
                status_code=502, detail="O envio não foi confirmado. Tente novamente.",
            )
        raise HTTPException(
            status_code=409,
            detail=("Ative as notificações no perfil do aplicativo instalado no celular "
                    "e tente novamente."),
        )
    return {chave: len(envio[chave]) for chave in ("aceitos", "falhas", "invalidos")}
