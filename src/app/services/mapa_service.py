"""Validação e persistência das delimitações operacionais em GeoJSON.

GEOS/Shapely verifica a topologia sem reparar ou converter geometrias salvas.
A comparação de limites é informativa; não calcula hectares nem representa
georreferenciamento oficial. Leitura de dados legados nunca escreve no banco.
"""
import json
import math

from shapely.errors import ShapelyError
from shapely.geometry import GeometryCollection, shape

from ..models._helpers import iso_now

_TIPOS_ACEITOS = {"Polygon", "MultiPolygon", "Feature"}
MAX_GEOJSON_BYTES = 100 * 1024
_MAX_GEOJSON_BYTES = MAX_GEOJSON_BYTES  # Compatibilidade com o limite anterior.
_MAX_JSON_DEPTH = 32
_MAX_JSON_NODES = 20_000
_MAX_POSICOES = 5_000
_MAX_ANEIS = 256
_MAX_PARTES = 128
_ERRO_COMPLEXIDADE = "GeoJSON excede os limites de complexidade permitidos."
_ERRO_TOPOLOGIA = "Geometria inválida: verifique vértices, autointerseções e anéis internos."


def _recusar_constante(valor):
    raise ValueError("Constante numérica não permitida em JSON.")


def _validar_estrutura_json(payload):
    """Limita o trabalho antes de serializar ou entregar coordenadas ao GEOS."""
    pilha = [(payload, 0, False)]
    ancestrais = set()
    nos = 0
    bytes_texto = 0
    while pilha:
        valor, profundidade, saindo = pilha.pop()
        if saindo:
            ancestrais.remove(id(valor))
            continue
        nos += 1
        if nos > _MAX_JSON_NODES or profundidade > _MAX_JSON_DEPTH:
            return _ERRO_COMPLEXIDADE
        if isinstance(valor, (dict, list)):
            if len(valor) > _MAX_JSON_NODES - nos:
                return _ERRO_COMPLEXIDADE
            if id(valor) in ancestrais:
                return "JSON inválido: estrutura circular."
            ancestrais.add(id(valor))
            pilha.append((valor, profundidade, True))
            if isinstance(valor, dict):
                for chave in valor:
                    if not isinstance(chave, str):
                        return "As chaves do JSON devem ser textos."
                    try:
                        if len(chave) > MAX_GEOJSON_BYTES:
                            return _ERRO_COMPLEXIDADE
                        bytes_texto += len(chave.encode("utf-8"))
                        if bytes_texto > MAX_GEOJSON_BYTES:
                            return _ERRO_COMPLEXIDADE
                    except UnicodeError:
                        return "JSON contém texto inválido."
                nos += len(valor)
                if nos > _MAX_JSON_NODES:
                    return _ERRO_COMPLEXIDADE
                filhos = valor.values()
            else:
                filhos = valor
            pilha.extend((filho, profundidade + 1, False) for filho in filhos)
        elif isinstance(valor, str):
            try:
                if len(valor) > MAX_GEOJSON_BYTES:
                    return _ERRO_COMPLEXIDADE
                bytes_texto += len(valor.encode("utf-8"))
                if bytes_texto > MAX_GEOJSON_BYTES:
                    return _ERRO_COMPLEXIDADE
            except UnicodeError:
                return "JSON contém texto inválido."
        elif isinstance(valor, float):
            if not math.isfinite(valor):
                return "JSON não permite números não finitos."
        elif isinstance(valor, int) and valor.bit_length() > MAX_GEOJSON_BYTES * 4:
            return _ERRO_COMPLEXIDADE
        elif valor is not None and not isinstance(valor, (int, bool)):
            return "O payload contém um valor não permitido em JSON."
    return None


def _carregar_json(payload):
    if isinstance(payload, (str, bytes)):
        try:
            if len(payload) > MAX_GEOJSON_BYTES:
                return None, f"GeoJSON excede o tamanho máximo ({MAX_GEOJSON_BYTES} bytes)."
            bruto = payload.encode("utf-8") if isinstance(payload, str) else payload
            if len(bruto) > MAX_GEOJSON_BYTES:
                return None, f"GeoJSON excede o tamanho máximo ({MAX_GEOJSON_BYTES} bytes)."
            payload = json.loads(bruto.decode("utf-8"), parse_constant=_recusar_constante)
        except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError):
            return None, "JSON inválido."
    if not isinstance(payload, dict):
        return None, "O payload deve ser um objeto JSON."
    erro = _validar_estrutura_json(payload)
    return (None, erro) if erro else (payload, None)


def _novo_orcamento():
    return {"partes": 0, "aneis": 0, "posicoes": 0}


def _validar_geometria(tipo, coords, orcamento=None):
    """Valida estrutura e limites de um Polygon/MultiPolygon antes do GEOS."""
    if not isinstance(tipo, str) or tipo not in {"Polygon", "MultiPolygon"}:
        return "A geometria deve ser Polygon ou MultiPolygon."
    if not isinstance(coords, list) or not coords:
        return "Coordenadas ausentes ou inválidas."
    orcamento = orcamento if orcamento is not None else _novo_orcamento()
    poligonos = [coords] if tipo == "Polygon" else coords
    for poligono in poligonos:
        erro = _validar_poligono(poligono, orcamento)
        if erro:
            return erro
    return None


def _validar_poligono(aneis, orcamento=None):
    if not isinstance(aneis, list) or not aneis:
        return "O polígono deve conter ao menos um anel de coordenadas."
    orcamento = orcamento if orcamento is not None else _novo_orcamento()
    orcamento["partes"] += 1
    orcamento["aneis"] += len(aneis)
    if orcamento["partes"] > _MAX_PARTES or orcamento["aneis"] > _MAX_ANEIS:
        return _ERRO_COMPLEXIDADE
    for anel in aneis:
        erro = _validar_anel(anel, orcamento)
        if erro:
            return erro
    return None


def _validar_anel(anel, orcamento=None):
    if not isinstance(anel, list) or len(anel) < 4:
        return "Cada anel do polígono precisa de ao menos 4 pontos."
    orcamento = orcamento if orcamento is not None else _novo_orcamento()
    orcamento["posicoes"] += len(anel)
    if orcamento["posicoes"] > _MAX_POSICOES:
        return _ERRO_COMPLEXIDADE
    for posicao in anel:
        if not _posicao_valida(posicao):
            return ("Coordenadas inválidas: use [lng, lat] com altitude opcional, "
                    "números finitos, longitude entre -180 e 180 e latitude entre -90 e 90.")
    if anel[0] != anel[-1]:
        return "Cada anel do polígono deve ser fechado (último ponto igual ao primeiro)."
    if len({tuple(posicao[:2]) for posicao in anel[:-1]}) < 3:
        return "Cada anel precisa de ao menos 3 vértices distintos."
    return None


def _posicao_valida(posicao):
    if not isinstance(posicao, list) or len(posicao) not in (2, 3):
        return False
    for indice, valor in enumerate(posicao):
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            return False
        # Comparações de inteiros não passam pela conversão potencialmente
        # explosiva de math.isfinite(10**1000) para double.
        if indice < 2:
            limite = 180 if indice == 0 else 90
            if not -limite <= valor <= limite:
                return False
        try:
            if not math.isfinite(valor):
                return False
        except OverflowError:
            return False
    return True


def _validar_objeto(dados, orcamento, aceitar_colecao=False):
    tipo = dados.get("type")
    if not isinstance(tipo, str):
        return "O tipo GeoJSON deve ser um texto."
    if tipo == "FeatureCollection" and aceitar_colecao:
        features = dados.get("features")
        if not isinstance(features, list) or len(features) > _MAX_PARTES:
            return "Coleção legada inválida ou excessivamente complexa."
        for feature in features:
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                return "Coleção legada deve conter apenas Features poligonais."
            erro = _validar_objeto(feature, orcamento)
            if erro:
                return erro
        return None
    if tipo not in _TIPOS_ACEITOS:
        return "Tipo GeoJSON não suportado. Use Polygon, MultiPolygon ou Feature."
    geometria = dados
    if tipo == "Feature":
        if dados.get("properties") is not None and not isinstance(dados["properties"], dict):
            return "As propriedades de uma Feature devem ser um objeto ou nulas."
        geometria = dados.get("geometry")
        if not isinstance(geometria, dict):
            return "Feature sem geometria válida."
    erro = _validar_geometria(geometria.get("type"), geometria.get("coordinates"), orcamento)
    if erro:
        return erro
    try:
        objeto = shape(geometria)
        if objeto.is_empty or not objeto.is_valid or objeto.area <= 0:
            return _ERRO_TOPOLOGIA
    except (TypeError, ValueError, IndexError, OverflowError, ShapelyError):
        return _ERRO_TOPOLOGIA
    return None


def _validar_payload(payload, aceitar_colecao=False):
    if payload is None:
        return None, None, "Payload vazio."
    dados, erro = _carregar_json(payload)
    if erro:
        return None, None, erro
    try:
        serializado = json.dumps(dados, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        if len(serializado.encode("utf-8")) > MAX_GEOJSON_BYTES:
            return None, None, f"GeoJSON excede o tamanho máximo ({MAX_GEOJSON_BYTES} bytes)."
    except (TypeError, ValueError, UnicodeError, RecursionError, OverflowError):
        return None, None, "JSON inválido."
    erro = _validar_objeto(dados, _novo_orcamento(), aceitar_colecao)
    return (None, None, erro) if erro else (dados, serializado, None)


def validar_poligono_geojson(payload):
    """Retorna ``(texto, None)`` ou ``(None, erro)`` sem reparar a entrada."""
    _, serializado, erro = _validar_payload(payload)
    return serializado, erro


def ler_poligono_geojson(valor):
    """Lê geometria legada segura; aceita coleções poligonais sem gravar nada."""
    dados, _, erro = _validar_payload(valor, aceitar_colecao=True)
    return None if erro else dados


def _geometrias(dados):
    if dados["type"] == "FeatureCollection":
        return [feature["geometry"] for feature in dados["features"]]
    return [dados["geometry"] if dados["type"] == "Feature" else dados]


def _cruza_antimeridiano(dados):
    for geometria in _geometrias(dados):
        poligonos = ([geometria["coordinates"]] if geometria["type"] == "Polygon"
                     else geometria["coordinates"])
        for poligono in poligonos:
            for anel in poligono:
                longitudes = [posicao[0] for posicao in anel]
                if max(longitudes) - min(longitudes) > 180:
                    return True
    return False


def comparar_limites(contornoRaw, areaRaw):
    """Detecção topológica informativa, sem bloqueio ou cálculo geodésico.

    Anéis que atravessam o antimeridiano exigem representação apropriada;
    a comparação deles não é declarada verificável pelo plano longitude/latitude.
    """
    if contornoRaw in (None, "", b"") or areaRaw in (None, "", b""):
        return {"status": "sem_delimitacao", "mensagem": "Comparação indisponível: falta delimitar a Propriedade ou a Área de Plantio."}
    contorno = ler_poligono_geojson(contornoRaw)
    area = ler_poligono_geojson(areaRaw)
    if contorno is None or area is None:
        return {"status": "nao_verificavel", "mensagem": "Comparação indisponível: uma delimitação é inválida ou excede os limites suportados."}
    if _cruza_antimeridiano(contorno) or _cruza_antimeridiano(area):
        return {"status": "nao_verificavel", "mensagem": "A comparação de delimitações que cruzam o antimeridiano exige tratamento geográfico específico."}
    try:
        geometrias_contorno = [shape(g) for g in _geometrias(contorno)]
        geometrias_area = [shape(g) for g in _geometrias(area)]
        limite = GeometryCollection(geometrias_contorno)
        terreno = GeometryCollection(geometrias_area)
        if limite.is_empty or terreno.is_empty:
            return {"status": "nao_verificavel", "mensagem": "Comparação indisponível: uma delimitação não contém polígonos."}
        contida = limite.covers(terreno)
    except (TypeError, ValueError, IndexError, OverflowError, ShapelyError):
        return {"status": "nao_verificavel", "mensagem": "Não foi possível comparar as delimitações informadas."}
    if contida:
        return {"status": "contida", "mensagem": "A Área de Plantio está dentro ou no limite do contorno informado."}
    return {"status": "fora_do_limite", "mensagem": "A Área de Plantio ultrapassa o contorno informado da Propriedade. Verificação informativa; nenhum ajuste automático foi realizado."}


def atualizar_poligono_gleba(gleba, geojson_str):
    """Atualiza somente a geometria e a data de uma Área de Plantio."""
    gleba.poligono_geojson = geojson_str
    gleba.atualizado_em = iso_now()


def limpar_poligono_gleba(gleba):
    gleba.poligono_geojson = None
    gleba.atualizado_em = iso_now()


def atualizar_poligono_propriedade(propriedade, geojson_str):
    propriedade.poligono_geojson = geojson_str
    propriedade.atualizado_em = iso_now()


def limpar_poligono_propriedade(propriedade):
    propriedade.poligono_geojson = None
    propriedade.atualizado_em = iso_now()
