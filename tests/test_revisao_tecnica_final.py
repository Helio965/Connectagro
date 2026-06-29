"""Testes da revisão Pós-MVP 0.1 — organização/manutenção.

Checagens simples e não frágeis: o documento de revisão existe, o README o
referencia, o template morto de placeholders foi removido e o JS base não tem
log de debug.
"""
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _ler(*partes):
    with open(os.path.join(RAIZ, *partes), encoding="utf-8") as arquivo:
        return arquivo.read()


def test_documento_revisao_tecnica_existe():
    caminho = os.path.join(RAIZ, "docs", "11-revisao-tecnica-final.md")
    assert os.path.isfile(caminho)
    assert "Revisão Técnica Final" in _ler("docs", "11-revisao-tecnica-final.md")


def test_readme_referencia_documento_revisao():
    assert "docs/11-revisao-tecnica-final.md" in _ler("README.md")


def test_template_placeholder_morto_removido():
    caminho = os.path.join(RAIZ, "src", "app", "templates", "placeholders")
    assert not os.path.exists(caminho)


def test_js_base_sem_console_log():
    assert "console.log" not in _ler("src", "app", "static", "js", "main.js")
