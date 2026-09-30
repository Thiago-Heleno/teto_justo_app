from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TarefaDistribuicao:
    id: UUID
    pontuacao_potencial: int
    usuarios_elegiveis: tuple[UUID, ...]

    def __post_init__(self):
        if not isinstance(self.id, UUID):
            raise ValueError("O ID da tarefa deve ser um UUID.")
        if (
            isinstance(self.pontuacao_potencial, bool)
            or not isinstance(self.pontuacao_potencial, int)
            or self.pontuacao_potencial <= 0
        ):
            raise ValueError("A pontuação potencial deve ser um inteiro positivo.")

        elegiveis = tuple(self.usuarios_elegiveis)
        if not elegiveis or any(not isinstance(usuario_id, UUID) for usuario_id in elegiveis):
            raise ValueError("A tarefa deve possuir ao menos um usuário elegível.")
        if len(set(elegiveis)) != len(elegiveis):
            raise ValueError("A lista de usuários elegíveis não pode conter duplicados.")
        object.__setattr__(self, "usuarios_elegiveis", elegiveis)


@dataclass(frozen=True, slots=True)
class AtribuicaoRotatividade:
    tarefa_id: UUID
    usuario_id: UUID
    pontuacao_potencial: int


@dataclass(frozen=True, slots=True)
class ResultadoDistribuicao:
    atribuicoes: tuple[AtribuicaoRotatividade, ...]
    pontuacao_por_usuario: Mapping[UUID, int]

    def __post_init__(self):
        object.__setattr__(
            self,
            "pontuacao_por_usuario",
            MappingProxyType(dict(self.pontuacao_por_usuario)),
        )


class ServicoRotatividade:
    """Distribui ocorrências usando o menor total entre os usuários elegíveis."""

    def distribuir_tarefas(
        self,
        tarefas: Sequence[TarefaDistribuicao],
        usuarios: Sequence[UUID],
        pontuacao_inicial: Mapping[UUID, int] | None = None,
    ) -> ResultadoDistribuicao:
        membros = tuple(usuarios)
        if not membros or any(not isinstance(usuario_id, UUID) for usuario_id in membros):
            raise ValueError("A casa deve possuir ao menos um membro válido.")
        if len(set(membros)) != len(membros):
            raise ValueError("A lista de membros não pode conter duplicados.")

        totais = self._totais_iniciais(membros, pontuacao_inicial)
        tarefas_validadas = tuple(tarefas)
        for tarefa in tarefas_validadas:
            if not isinstance(tarefa, TarefaDistribuicao):
                raise ValueError("As tarefas devem usar TarefaDistribuicao.")
            if any(usuario_id not in totais for usuario_id in tarefa.usuarios_elegiveis):
                raise ValueError("Toda pessoa elegível deve ser membro da casa.")

        atribuicoes: list[AtribuicaoRotatividade | None] = [None] * len(tarefas_validadas)
        ordem_membros = {usuario_id: indice for indice, usuario_id in enumerate(membros)}

        # Alocar valores maiores primeiro reduz a diferença final sem retirar
        # a restrição de elegibilidade de cada ocorrência.
        ordem_tarefas = sorted(
            enumerate(tarefas_validadas),
            key=lambda item: (-item[1].pontuacao_potencial, item[0]),
        )
        for indice, tarefa in ordem_tarefas:
            usuario_id = min(
                tarefa.usuarios_elegiveis,
                key=lambda candidato: (totais[candidato], ordem_membros[candidato]),
            )
            totais[usuario_id] += tarefa.pontuacao_potencial
            atribuicoes[indice] = AtribuicaoRotatividade(
                tarefa_id=tarefa.id,
                usuario_id=usuario_id,
                pontuacao_potencial=tarefa.pontuacao_potencial,
            )

        return ResultadoDistribuicao(
            atribuicoes=tuple(atribuicao for atribuicao in atribuicoes if atribuicao is not None),
            pontuacao_por_usuario=totais,
        )

    @staticmethod
    def _totais_iniciais(
        membros: tuple[UUID, ...],
        pontuacao_inicial: Mapping[UUID, int] | None,
    ) -> dict[UUID, int]:
        iniciais = pontuacao_inicial or {}
        if any(usuario_id not in membros for usuario_id in iniciais):
            raise ValueError("A pontuação inicial só pode conter membros da casa.")
        totais = {usuario_id: iniciais.get(usuario_id, 0) for usuario_id in membros}
        if any(
            isinstance(pontos, bool) or not isinstance(pontos, int) or pontos < 0
            for pontos in totais.values()
        ):
            raise ValueError("A pontuação inicial deve conter inteiros não negativos.")
        return totais


def distribuir_tarefas(
    tarefas: Sequence[TarefaDistribuicao],
    usuarios: Sequence[UUID],
    pontuacao_inicial: Mapping[UUID, int] | None = None,
) -> ResultadoDistribuicao:
    return ServicoRotatividade().distribuir_tarefas(
        tarefas,
        usuarios,
        pontuacao_inicial,
    )
