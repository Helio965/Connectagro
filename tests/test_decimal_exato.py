"""Exatidão decimal operacional sem arredondamento implícito em SQLite/PG."""
from decimal import Decimal, localcontext

import pytest
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.exc import StatementError

from app.utils.decimal_exato import DecimalExato


@pytest.mark.parametrize("value,expected", [
    (None, None), (0, "0.000000"), ("-0", "0.000000"),
    ("0.000001", "0.000001"), ("2.5000000", "2.500000"),
    (Decimal("999999999999.999999"), "999999999999.999999"),
    (Decimal("-999999999999.999999"), "-999999999999.999999"),
])
def test_bind_sqlite_preserva_valor_canonicamente(value, expected):
    assert DecimalExato().process_bind_param(value, sqlite.dialect()) == expected


@pytest.mark.parametrize("value", [
    True, False, 0.1, float("nan"), [], {}, "", "abc", "1,2",
    Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity"),
    "1000000000000", "-1000000000000", "0.0000001", "1e99999999",
    "1e-99999999", "1" * 1000,
])
def test_bind_rejeita_invalido_excesso_ou_arredondamento(value):
    with pytest.raises(ValueError):
        DecimalExato().process_bind_param(value, sqlite.dialect())


def test_sqlite_roundtrip_mantem_digitos_acima_da_precisao_binaria():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    tabela = sa.Table("decimais", metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("quantidade", DecimalExato(18, 6)),
        sa.Column("total", DecimalExato(18, 2)))
    metadata.create_all(engine)
    quantidade = Decimal("999999999999.999999")
    total = Decimal("9999999999999999.99")
    try:
        with engine.begin() as connection:
            connection.execute(tabela.insert(), {"id": 1, "quantidade": quantidade, "total": total})
            row = connection.execute(sa.select(tabela.c.quantidade, tabela.c.total)).one()
            assert row == (quantidade, total)
            assert all(isinstance(value, Decimal) for value in row)
            assert connection.execute(sa.text(
                "SELECT quantidade,total,typeof(quantidade),typeof(total) FROM decimais"
            )).one() == (str(quantidade), str(total), "text", "text")
            with pytest.raises(StatementError):
                connection.execute(tabela.insert(), {"id": 2, "quantidade": Decimal("0.0000001")})
    finally:
        engine.dispose()


def test_postgres_compila_numeric_e_bind_nao_converte_para_float():
    tipo = DecimalExato(18, 2)
    dialect = postgresql.dialect()
    valor = Decimal("9999999999999999.99")
    assert str(tipo.compile(dialect=dialect)) == "NUMERIC(18, 2)"
    assert tipo.process_bind_param(valor, dialect) == valor
    assert isinstance(tipo.process_bind_param(valor, dialect), Decimal)
    assert tipo.process_result_value(valor, dialect) == valor


def test_decimal_exato_independe_do_contexto_global():
    with localcontext() as context:
        context.prec = 3
        assert DecimalExato().process_bind_param(
            Decimal("999999999999.999999"), sqlite.dialect()) == "999999999999.999999"


@pytest.mark.parametrize("precision,scale", [(0, 0), (3, -1), (3, 4), (True, 0), (4, False), (4.5, 2)])
def test_parametros_invalidos(precision, scale):
    with pytest.raises(ValueError):
        DecimalExato(precision, scale)
