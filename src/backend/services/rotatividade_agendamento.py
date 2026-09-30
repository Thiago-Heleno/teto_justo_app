from datetime import date, datetime, time, timedelta, timezone
from threading import Lock
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from postgrest.exceptions import APIError

from schemas.rotatividade import RotatividadeCriar
from services.autorizacao import ServicoAutorizacaoCasa
from services.rotatividade import TarefaDistribuicao, distribuir_tarefas
from services.score import ServicoScore

_TAMANHO_PAGINA = 500
_LOCK_PROCESSAMENTO = Lock()


def datas_ocorrencias(configuracao: dict, ate: date) -> list[date]:
    ancora = date.fromisoformat(str(configuracao["semana_ancora"])[:10])
    inicio_semana = ancora - timedelta(days=ancora.weekday())
    dias_semana = set(configuracao["dias_semana"])
    intervalo = configuracao["intervalo_semanas"]
    datas = []

    dia = ancora
    while dia <= ate:
        semanas_desde_ancora = (dia - inicio_semana).days // 7
        if (
            dia.isoweekday() in dias_semana
            and semanas_desde_ancora % intervalo == 0
        ):
            datas.append(dia)
        dia += timedelta(days=1)
    return datas


def data_local_ocorrencia(valor: str, fuso: ZoneInfo) -> date:
    instante = datetime.fromisoformat(valor)
    if instante.tzinfo is None or instante.utcoffset() is None:
        instante = instante.replace(tzinfo=timezone.utc)
    return instante.astimezone(fuso).date()


class ServicoAgendamentoRotatividade:
    def __init__(self, supabase):
        self.supabase = supabase

    def criar_rotatividade(
        self,
        dados: RotatividadeCriar,
        id_usuario_atual: UUID,
    ) -> dict:
        autorizacao = ServicoAutorizacaoCasa(self.supabase)
        id_administrador = autorizacao.garantir_administrador_da_casa(
            dados.fk_casa_id,
            id_usuario_atual,
        )
        autorizacao.garantir_responsaveis_da_casa(
            dados.fk_casa_id,
            dados.participantes,
        )
        resposta_casa = (
            self.supabase.table("casa")
            .select("timezone")
            .eq("id", str(dados.fk_casa_id))
            .execute()
        )
        if not resposta_casa.data:
            raise HTTPException(status_code=404, detail="Casa não encontrada.")

        fuso = ZoneInfo(resposta_casa.data[0]["timezone"])
        agora_local = datetime.now(fuso)
        payload = {
            "fk_casa_id": str(dados.fk_casa_id),
            "fk_usuario_id": str(id_administrador),
            "timezone": fuso.key,
            "nome": dados.nome,
            "descricao": dados.descricao,
            "dificuldade": dados.peso,
            "pontuacao": ServicoScore.pontos_por_peso(dados.peso),
            "prazo_dias": dados.prazo_dias,
            "atraso_maximo": dados.atraso_maximo,
            "modo_prazo": dados.modo_prazo,
            "dias_semana": dados.dias_semana,
            "intervalo_semanas": dados.intervalo_semanas,
            "semana_ancora": agora_local.date().isoformat(),
        }
        resposta = self.supabase.table("rotatividade").insert(payload).execute()
        if not resposta.data:
            raise HTTPException(
                status_code=500,
                detail="Erro ao criar a configuração do rodízio.",
            )
        configuracao = resposta.data[0]
        participantes = [
            {
                "fk_rotatividade_id": str(configuracao["id"]),
                "fk_usuario_id": str(usuario_id),
                "ordem": ordem,
            }
            for ordem, usuario_id in enumerate(dados.participantes, start=1)
        ]
        try:
            resposta_participantes = (
                self.supabase.table("rotatividade_participante")
                .insert(participantes)
                .execute()
            )
        except APIError:
            self._remover_configuracao_incompleta(str(configuracao["id"]))
            raise
        if len(resposta_participantes.data or []) != len(participantes):
            self._remover_configuracao_incompleta(str(configuracao["id"]))
            raise HTTPException(
                status_code=500,
                detail="Não foi possível salvar todos os participantes do rodízio.",
            )
        return configuracao

    def _remover_configuracao_incompleta(self, id_rotatividade: str) -> None:
        (
            self.supabase.table("rotatividade_participante")
            .delete()
            .eq("fk_rotatividade_id", id_rotatividade)
            .execute()
        )
        (
            self.supabase.table("rotatividade")
            .delete()
            .eq("id", id_rotatividade)
            .execute()
        )

    def _listar(self, tabela: str, selecao: str, filtros: tuple | None = None) -> list[dict]:
        registros = []
        inicio = 0
        while True:
            consulta = (
                self.supabase.table(tabela)
                .select(selecao)
            )
            if filtros:
                for metodo, campo, valor in filtros:
                    consulta = getattr(consulta, metodo)(campo, valor)
            pagina = (
                consulta.order("id")
                .range(inicio, inicio + _TAMANHO_PAGINA - 1)
                .execute()
            ).data
            registros.extend(pagina)
            if len(pagina) < _TAMANHO_PAGINA:
                return registros
            inicio += _TAMANHO_PAGINA

    def _pontuacao_anterior(
        self,
        id_rotatividade: str,
        membros: tuple[UUID, ...],
    ) -> dict[UUID, int]:
        totais = dict.fromkeys(membros, 0)
        tarefas = self._listar(
            "tarefa",
            "id,pontuacao",
            (("eq", "rotatividade_id", id_rotatividade),),
        )
        ids_tarefas = [str(tarefa["id"]) for tarefa in tarefas]
        for inicio in range(0, len(ids_tarefas), _TAMANHO_PAGINA):
            lote = ids_tarefas[inicio : inicio + _TAMANHO_PAGINA]
            atribuicoes = (
                self.supabase.table("atribuida")
                .select("fk_usuario_id,fk_tarefa_id")
                .in_("fk_tarefa_id", lote)
                .execute()
            ).data
            pontuacoes = {
                str(tarefa["id"]): tarefa["pontuacao"]
                for tarefa in tarefas
                if str(tarefa["id"]) in lote
            }
            for atribuicao in atribuicoes:
                usuario_id = UUID(str(atribuicao["fk_usuario_id"]))
                if usuario_id in totais:
                    totais[usuario_id] += pontuacoes[str(atribuicao["fk_tarefa_id"])]
        return totais

    def _buscar_tarefa_ocorrencia(
        self,
        id_rotatividade: str,
        ocorrencia_em: str,
    ) -> dict | None:
        tarefas = (
            self.supabase.table("tarefa")
            .select("*")
            .eq("rotatividade_id", id_rotatividade)
            .eq("ocorrencia_em", ocorrencia_em)
            .execute()
        ).data
        return tarefas[0] if tarefas else None

    def _garantir_atribuicao(
        self,
        tarefa: dict,
        configuracao: dict,
        membros: tuple[UUID, ...],
    ) -> None:
        atribuicoes_existentes = (
            self.supabase.table("atribuida")
            .select("fk_usuario_id")
            .eq("fk_tarefa_id", str(tarefa["id"]))
            .execute()
        ).data
        if atribuicoes_existentes:
            return

        totais = self._pontuacao_anterior(str(configuracao["id"]), membros)
        distribuicao = distribuir_tarefas(
            [
                TarefaDistribuicao(
                    id=UUID(str(tarefa["id"])),
                    pontuacao_potencial=tarefa["pontuacao"],
                    usuarios_elegiveis=membros,
                )
            ],
            membros,
            totais,
        )
        usuario_id = distribuicao.atribuicoes[0].usuario_id
        try:
            self.supabase.table("atribuida").insert(
                {
                    "fk_usuario_id": str(usuario_id),
                    "fk_tarefa_id": str(tarefa["id"]),
                }
            ).execute()
        except APIError as erro:
            if erro.code != "23505":
                raise
            atribuicoes_existentes = (
                self.supabase.table("atribuida")
                .select("fk_usuario_id")
                .eq("fk_tarefa_id", str(tarefa["id"]))
                .execute()
            ).data
            if not atribuicoes_existentes:
                raise

    def _membros_elegiveis(self, configuracao: dict) -> tuple[UUID, ...]:
        participantes = (
            self.supabase.table("rotatividade_participante")
            .select("fk_usuario_id,ordem")
            .eq("fk_rotatividade_id", str(configuracao["id"]))
            .order("ordem")
            .execute()
        ).data
        vinculos = (
            self.supabase.table("pertencer")
            .select("fk_usuario_id")
            .eq("fk_casa_id", str(configuracao["fk_casa_id"]))
            .execute()
        ).data
        membros_da_casa = {str(vinculo["fk_usuario_id"]) for vinculo in vinculos}
        membros = tuple(
            UUID(str(participante["fk_usuario_id"]))
            for participante in participantes
            if str(participante["fk_usuario_id"]) in membros_da_casa
        )
        if not membros:
            raise HTTPException(
                status_code=409,
                detail="O rodízio não possui participantes vinculados à casa.",
            )
        return membros

    def _registrar_ocorrencia(
        self,
        configuracao: dict,
        dia: date,
        membros: tuple[UUID, ...],
    ) -> None:
        id_rotatividade = str(configuracao["id"])
        id_casa = str(configuracao["fk_casa_id"])
        fuso = ZoneInfo(configuracao["timezone"])
        ocorrencia_local = datetime.combine(dia, time.min, tzinfo=fuso)

        if configuracao["modo_prazo"] == "dia_fixo":
            data_fim = datetime.combine(dia, time.max, tzinfo=fuso).astimezone(
                timezone.utc
            )
            data_inicio = data_fim - timedelta(days=configuracao["prazo_dias"])
        else:
            data_inicio = ocorrencia_local.astimezone(timezone.utc)
            data_fim = data_inicio + timedelta(days=configuracao["prazo_dias"])

        ocorrencia_em = ocorrencia_local.astimezone(timezone.utc).isoformat()
        tarefa = self._buscar_tarefa_ocorrencia(id_rotatividade, ocorrencia_em)
        if tarefa is None:
            registro = {
                "nome": configuracao["nome"],
                "descricao": configuracao.get("descricao"),
                "estado_atual": "pendente",
                "dificuldade": configuracao["dificuldade"],
                "pontuacao": configuracao["pontuacao"],
                "prazo_dias": configuracao["prazo_dias"],
                "atraso_maximo": configuracao["atraso_maximo"],
                "modo_prazo": configuracao["modo_prazo"],
                "tipo": "rotativa",
                "referencia_inicio": "ocorrencia",
                "data_inicio": data_inicio.isoformat(),
                "data_fim": data_fim.isoformat(),
                "fk_casa_id": id_casa,
                "fk_usuario_id": str(configuracao["fk_usuario_id"]),
                "rotatividade_id": id_rotatividade,
                "ocorrencia_em": ocorrencia_em,
                "timezone": configuracao["timezone"],
            }
            try:
                resposta = self.supabase.table("tarefa").insert(registro).execute()
            except APIError as erro:
                if erro.code != "23505":
                    raise
                tarefa = self._buscar_tarefa_ocorrencia(id_rotatividade, ocorrencia_em)
                if tarefa is None:
                    raise
            else:
                if not resposta.data:
                    tarefa = self._buscar_tarefa_ocorrencia(
                        id_rotatividade,
                        ocorrencia_em,
                    )
                    if tarefa is None:
                        raise HTTPException(
                            status_code=500,
                            detail="Erro ao criar a ocorrência do rodízio.",
                        )
                else:
                    tarefa = resposta.data[0]

            if tarefa is None:
                raise HTTPException(
                    status_code=500,
                    detail="Não foi possível localizar a ocorrência criada.",
                )
        self._garantir_atribuicao(tarefa, configuracao, membros)

    def processar_ocorrencias(self, agora: datetime | None = None) -> dict[str, int]:
        if not _LOCK_PROCESSAMENTO.acquire(blocking=False):
            raise HTTPException(
                status_code=409,
                detail="O processamento de rodízios já está em andamento.",
            )
        try:
            return self._processar_ocorrencias(agora)
        finally:
            _LOCK_PROCESSAMENTO.release()

    def _processar_ocorrencias(self, agora: datetime | None = None) -> dict[str, int]:
        instante = agora or datetime.now(timezone.utc)
        if instante.tzinfo is None or instante.utcoffset() is None:
            raise ValueError("O instante do processamento deve conter fuso horário.")
        instante = instante.astimezone(timezone.utc)
        configuracoes = self._listar(
            "rotatividade",
            "*",
            (("eq", "ativa", True),),
        )
        processadas = 0

        for configuracao in configuracoes:
            fuso = ZoneInfo(configuracao["timezone"])
            datas_previstas = datas_ocorrencias(
                configuracao,
                instante.astimezone(fuso).date(),
            )
            if not datas_previstas:
                continue

            tarefas_existentes = self._listar(
                "tarefa",
                "id,ocorrencia_em,pontuacao",
                (("eq", "rotatividade_id", str(configuracao["id"])),),
            )
            datas_existentes = {
                data_local_ocorrencia(str(tarefa["ocorrencia_em"]), fuso)
                for tarefa in tarefas_existentes
            }
            membros = self._membros_elegiveis(configuracao)

            for dia in datas_previstas:
                self._registrar_ocorrencia(configuracao, dia, membros)
                if dia not in datas_existentes:
                    processadas += 1

        return {
            "rotatividades_analisadas": len(configuracoes),
            "ocorrencias_processadas": processadas,
        }
