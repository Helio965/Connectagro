"""Ponto de entrada da aplicação ConnectAgro (MVP).

Executar a partir da **raiz do projeto**::

    python src/run.py

Ou, se estiver dentro da pasta ``src/``::

    python run.py
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
