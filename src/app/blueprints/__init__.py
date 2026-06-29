"""Registro central dos blueprints do ConnectAgro (MVP)."""
from .dashboard import dashboard_bp
from .auth import auth_bp
from .culturas import culturas_bp
from .glebas import glebas_bp
from .defensivos import defensivos_bp
from .fertilizantes import fertilizantes_bp
from .aplicacoes import aplicacoes_bp
from .financeiro import financeiro_bp
from .upload import upload_bp
from .equipe import equipe_bp
from .colheita import colheita_bp
from .mapa import mapa_bp
from .ia import ia_bp
from .relatorios import relatorios_bp
from .usuarios import usuarios_bp
from .auditoria import auditoria_bp

ALL_BLUEPRINTS = [
    dashboard_bp,
    auth_bp,
    culturas_bp,
    glebas_bp,
    defensivos_bp,
    fertilizantes_bp,
    aplicacoes_bp,
    financeiro_bp,
    upload_bp,
    equipe_bp,
    colheita_bp,
    mapa_bp,
    ia_bp,
    relatorios_bp,
    usuarios_bp,
    auditoria_bp,
]


def register_blueprints(app):
    """Registra todos os blueprints dos módulos do MVP."""
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
