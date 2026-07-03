r"""Atualiza com segurança as credenciais do administrador principal.

Uso a partir da raiz do projeto:

    ADMIN_EMAIL="admin@example.com" ADMIN_PASSWORD="senha" python scripts/update_admin_credentials.py

No PowerShell:

    $env:ADMIN_EMAIL="admin@example.com"
    $env:ADMIN_PASSWORD="senha"
    .\.venv\Scripts\python.exe scripts\update_admin_credentials.py

O script faz backup do SQLite antes da alteração e nunca imprime a senha.
"""
from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Usuario  # noqa: E402
from app.models._helpers import iso_now  # noqa: E402
from app.utils.auth import gerar_hash_senha, verificar_senha  # noqa: E402


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _backup_database(db_path: Path) -> Path:
    backup_dir = PROJECT_ROOT / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"connectagro_db_before_admin_update_{_timestamp()}.sqlite"
    shutil.copy2(db_path, backup_path)
    return backup_path


def _admin_principal() -> Usuario:
    admins = Usuario.query.filter_by(perfil="admin").order_by(Usuario.id).all()
    if admins:
        ativos = [admin for admin in admins if admin.ativo]
        return ativos[0] if ativos else admins[0]

    usuario = Usuario.query.filter(Usuario.nome.ilike("%Administrador%")).order_by(Usuario.id).first()
    if usuario:
        return usuario

    raise RuntimeError("Nenhum usuário administrador encontrado para atualização.")


def main() -> int:
    novo_email = (os.environ.get("ADMIN_EMAIL") or "").strip().lower()
    nova_senha = os.environ.get("ADMIN_PASSWORD") or ""
    if not novo_email or "@" not in novo_email:
        print("ADMIN_EMAIL inválido ou ausente.")
        return 2
    if not nova_senha:
        print("ADMIN_PASSWORD ausente.")
        return 2

    app = create_app()
    with app.app_context():
        db_path = Path(db.engine.url.database).resolve()
        backup_path = _backup_database(db_path)

        admin = _admin_principal()
        conflito = Usuario.query.filter(Usuario.email == novo_email, Usuario.id != admin.id).first()
        if conflito:
            raise RuntimeError("Já existe outro usuário com o e-mail informado.")

        admin.email = novo_email
        admin.perfil = "admin"
        admin.ativo = True
        admin.senha_hash = gerar_hash_senha(nova_senha)
        admin.atualizado_em = iso_now()

        # A regra do MVP é um único admin ativo. Não apaga outros admins: apenas
        # evita múltiplos administradores ativos, caso algum dado legado exista.
        outros_admins = Usuario.query.filter(Usuario.perfil == "admin", Usuario.id != admin.id).all()
        for outro in outros_admins:
            outro.ativo = False
            outro.atualizado_em = iso_now()

        db.session.commit()

        admin_ok = (
            admin.email == novo_email
            and admin.perfil == "admin"
            and bool(admin.ativo)
            and verificar_senha(admin.senha_hash, nova_senha)
        )
        admins_ativos = Usuario.query.filter_by(perfil="admin", ativo=True).count()

        print(f"Banco SQLite: {db_path}")
        print(f"Backup criado: {backup_path}")
        print(f"Admin atualizado: #{admin.id} {admin.email}")
        print(f"Hash validado: {'sim' if admin_ok else 'nao'}")
        print(f"Admins ativos: {admins_ativos}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
