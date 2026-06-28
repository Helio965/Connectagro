"""Formatadores simples usados em telas do MVP."""


def formatar_numero(valor, casas=2):
    """Formata número no padrão brasileiro simples."""
    if valor is None:
        valor = 0
    texto = f"{float(valor):,.{casas}f}"
    return texto.replace(",", "_").replace(".", ",").replace("_", ".")


def formatar_moeda(valor):
    """Formata valor monetário em Real para leitura operacional."""
    return f"R$ {formatar_numero(valor)}"


def formatar_area(valor):
    """Formata área em hectares."""
    return f"{formatar_numero(valor)} ha"


def formatar_tamanho(bytes_):
    """Formata tamanho de arquivo em unidades legíveis."""
    if bytes_ is None:
        return "0 B"
    unidades = ("B", "KB", "MB", "GB")
    valor = float(bytes_)
    for unidade in unidades:
        if valor < 1024 or unidade == unidades[-1]:
            if unidade == "B":
                return f"{int(valor)} B"
            return f"{formatar_numero(valor, 1)} {unidade}"
        valor /= 1024
    return f"{bytes_} B"
