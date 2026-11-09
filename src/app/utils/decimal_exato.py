"""Decimal finito e exato nos dois bancos suportados.

SQLite converte NUMERIC em REAL em vários caminhos. Para preservar todos os
dígitos, os novos valores operacionais usam texto decimal canônico nesse banco;
PostgreSQL utiliza NUMERIC(precision, scale). Somar/calcular deve ser feito com
Decimal em Python, nunca com SUM/CAST numérico sobre a coluna textual SQLite.
"""
from decimal import Decimal, InvalidOperation, localcontext

from sqlalchemy import Numeric, String
from sqlalchemy.types import TypeDecorator


class DecimalExato(TypeDecorator):
    """Persistência decimal sem aceitar arredondamento implícito ou floats."""

    impl = Numeric
    cache_ok = True

    def __init__(self, precision=18, scale=6, **kwargs):
        if (isinstance(precision, bool) or isinstance(scale, bool)
                or not isinstance(precision, int) or not isinstance(scale, int)
                or precision < 1 or scale < 0 or scale > precision):
            raise ValueError("Precisão e escala decimais inválidas.")
        self.precision = precision
        self.scale = scale
        super().__init__(precision=precision, scale=scale, asdecimal=True, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(self.precision + 2))
        return dialect.type_descriptor(Numeric(self.precision, self.scale, asdecimal=True))

    def _decimal(self, value):
        if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
            raise ValueError("Informe um Decimal, inteiro ou texto decimal; float não é aceito.")
        # Limita texto antes de construir Decimal. Expoentes compactos extremos
        # também são recusados pelos limites ajustados, antes de quantize/format.
        if isinstance(value, str) and (not value or len(value) > self.precision + self.scale + 20):
            raise ValueError("Valor decimal fora do limite.")
        try:
            number = value if isinstance(value, Decimal) else Decimal(value)
        except (InvalidOperation, ValueError, OverflowError) as exc:
            raise ValueError("Valor decimal inválido.") from exc
        if not number.is_finite():
            raise ValueError("O valor decimal deve ser finito.")
        if number and number.adjusted() >= self.precision - self.scale:
            raise ValueError("Valor decimal fora da precisão permitida.")
        # normalize() depende do contexto corrente; a comparação com quantize
        # usa contexto próprio e recusa qualquer alteração dos dígitos.
        with localcontext() as context:
            context.prec = self.precision + self.scale + 4
            try:
                quantized = number.quantize(Decimal(1).scaleb(-self.scale))
            except InvalidOperation as exc:
                raise ValueError("Valor decimal fora da precisão permitida.") from exc
        if quantized != number:
            raise ValueError("Valor decimal possui mais casas que a escala permitida.")
        return quantized.copy_abs() if not quantized else quantized

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        number = self._decimal(value)
        return format(number, "f") if dialect.name == "sqlite" else number

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self._decimal(value)
