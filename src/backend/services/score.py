from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext
from uuid import UUID


_PONTOS_POR_PESO = {
    1: 10,
    2: 25,
    3: 50,
}


@dataclass(frozen=True, slots=True)
class ResultadoScore:
    usuario_id: UUID
    peso: int
    pontos_base: int
    atraso_maximo: int
    dias_atraso: int
    percentual_por_dia: Decimal
    desconto_por_dia: Decimal
    desconto_total: Decimal
    pontos_finais: int


class ServicoScore:
    @staticmethod
    def pontos_por_peso(peso: int) -> int:
        if isinstance(peso, bool) or not isinstance(peso, int) or peso not in _PONTOS_POR_PESO:
            raise ValueError("Peso deve ser 1, 2 ou 3.")
        return _PONTOS_POR_PESO[peso]

    @staticmethod
    def _normalizar_data(valor: datetime, nome_campo: str) -> datetime:
        if not isinstance(valor, datetime):
            raise ValueError(f"{nome_campo} deve ser uma data válida.")
        if valor.tzinfo is None or valor.utcoffset() is None:
            return valor.replace(tzinfo=timezone.utc)
        return valor.astimezone(timezone.utc)

    @staticmethod
    def _validar_responsavel(
        usuarios_atribuidos: Sequence[UUID],
    ) -> UUID:
        if isinstance(usuarios_atribuidos, (str, bytes)):
            raise ValueError("A tarefa deve possuir exatamente um responsável.")

        try:
            usuarios = tuple(usuarios_atribuidos)
        except TypeError as erro:
            raise ValueError(
                "A tarefa deve possuir exatamente um responsável."
            ) from erro

        if len(usuarios) != 1 or not isinstance(usuarios[0], UUID):
            raise ValueError("A tarefa deve possuir exatamente um responsável.")
        return usuarios[0]

    @staticmethod
    def calcular_dias_atraso(
        data_fim: datetime,
        concluida_em: datetime,
    ) -> int:
        if concluida_em <= data_fim:
            return 0

        diferenca = concluida_em - data_fim
        return diferenca.days + int(bool(diferenca.seconds or diferenca.microseconds))

    def calcular_score(
        self,
        peso: int,
        atraso_maximo: int,
        data_fim: datetime,
        concluida_em: datetime,
        usuarios_atribuidos: Sequence[UUID],
    ) -> ResultadoScore:
        pontos_base = self.pontos_por_peso(peso)
        if (
            isinstance(atraso_maximo, bool)
            or not isinstance(atraso_maximo, int)
            or atraso_maximo <= 0
        ):
            raise ValueError("Atraso máximo deve ser um inteiro positivo.")

        usuario_id = self._validar_responsavel(usuarios_atribuidos)
        data_fim_utc = self._normalizar_data(data_fim, "data_fim")
        concluida_em_utc = self._normalizar_data(
            concluida_em,
            "concluida_em",
        )
        dias_atraso = self.calcular_dias_atraso(
            data_fim_utc,
            concluida_em_utc,
        )
        divisor = atraso_maximo + 1

        with localcontext() as contexto:
            contexto.prec = 28
            percentual_por_dia = Decimal(100) / Decimal(divisor)
            desconto_por_dia = Decimal(pontos_base) / Decimal(divisor)
            dias_penalizados = min(dias_atraso, divisor)
            pontos_brutos = Decimal(pontos_base * (divisor - dias_penalizados)) / Decimal(divisor)
            desconto_total = Decimal(pontos_base) - pontos_brutos
            pontos_finais = int(pontos_brutos.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

        return ResultadoScore(
            usuario_id=usuario_id,
            peso=peso,
            pontos_base=pontos_base,
            atraso_maximo=atraso_maximo,
            dias_atraso=dias_atraso,
            percentual_por_dia=percentual_por_dia,
            desconto_por_dia=desconto_por_dia,
            desconto_total=desconto_total,
            pontos_finais=pontos_finais,
        )
