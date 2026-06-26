"""Helpers compartilhados pelos modelos do ConnectAgro."""
from datetime import datetime, timezone


def iso_now():
    """Retorna o instante atual (UTC) em ISO 8601, sem microssegundos.

    Datas/horas são armazenadas como ``TEXT`` (db.String), conforme o
    dicionário de dados.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
