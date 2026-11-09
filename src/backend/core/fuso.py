from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

FUSO_UTC = ZoneInfo("UTC")


def fuso_armazenado(nome: str | None) -> ZoneInfo | None:
    if not nome:
        return None
    try:
        return ZoneInfo(nome)
    except (ZoneInfoNotFoundError, ValueError):
        return None
