r"""Reset controlado dos dados operacionais do ConnectAgro.

Uso recomendado a partir da raiz do projeto:

    .\.venv\Scripts\python.exe scripts\reset_operational_data.py --yes

O script faz backup antes de limpar, preserva o catálogo técnico pré-cadastrado
e mantém os usuários-base do MVP ativos.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    Propriedade,
    Usuario,
    UsuarioPropriedade,
)
from app.utils.auth import gerar_hash_senha  # noqa: E402


BASE_USERS = (
    ("Administrador ConnectAgro", "admin@connectagro.com", "admin123", "admin"),
    ("Técnico ConnectAgro", "tecnico@connectagro.com", "tecnico123", "tecnico"),
    ("Trabalhador ConnectAgro", "trabalhador@connectagro.com", "trabalhador123", "trabalhador"),
)

DELETE_TABLES = (
    "log_auditoria",
    "senha_reset_token",
    "produto_preco",
    "produto_imagem",
    "ia_interacao",
    "upload_arquivo",
    "aplicacao_insumo",
    "colheita_registro",
    "financeiro_lancamento",
    "cultura_gleba",
    "cultura",
    "gleba",
    "equipe_membro",
    "usuario_propriedade",
    "propriedade",
)

PRESERVED_TABLES = (
    "alembic_version",
    "produto_base",
    "produto_tecnico",
    "usuario",
)

GENERATED_DIR_CANDIDATES = (
    "reports",
    "exports",
    "generated",
    "tmp",
    "temp",
    "instance/reports",
    "instance/exports",
    "instance/generated",
    "instance/tmp",
    "instance/temp",
    "src/instance/reports",
    "src/instance/exports",
    "src/instance/generated",
    "src/instance/tmp",
    "src/instance/temp",
)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _resolve_under_project(path: str | Path) -> Path:
    raw = Path(path)
    resolved = raw if raw.is_absolute() else PROJECT_ROOT / raw
    resolved = resolved.resolve()
    if os.path.commonpath([str(PROJECT_ROOT), str(resolved)]) != str(PROJECT_ROOT):
        raise ValueError(f"Caminho fora do projeto: {resolved}")
    return resolved


def _zip_directory(source: Path, destination: Path) -> int:
    count = 0
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        if source.exists():
            for item in source.rglob("*"):
                rel = item.relative_to(source.parent)
                if item.is_dir():
                    archive.writestr(f"{rel.as_posix()}/", "")
                else:
                    archive.write(item, rel)
                    count += 1
    return count


def _clear_directory_contents(path: Path) -> int:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
        return 0

    removed = 0
    for item in path.iterdir():
        if item.is_dir():
            for child in item.rglob("*"):
                if child.is_file():
                    removed += 1
            shutil.rmtree(item)
            removed += 1
        else:
            item.unlink()
            removed += 1
    return removed


def _count_tables(session) -> dict[str, int]:
    rows = session.execute(db.text(
        "select name from sqlite_master "
        "where type='table' and name not like 'sqlite_%' order by name"
    )).fetchall()
    counts = {}
    for (table,) in rows:
        counts[table] = session.execute(db.text(f"select count(*) from {table}")).scalar_one()
    return counts


def _backup_database(db_path: Path, backup_dir: Path, stamp: str) -> Path:
    backup_path = backup_dir / f"connectagro_db_backup_{stamp}.sqlite"
    shutil.copy2(db_path, backup_path)
    return backup_path


def _backup_directory(source: Path, backup_dir: Path, prefix: str, stamp: str) -> tuple[Path, int]:
    backup_path = backup_dir / f"{prefix}_{stamp}.zip"
    count = _zip_directory(source, backup_path)
    return backup_path, count


def _ensure_base_users(session) -> dict[str, Usuario]:
    users = {}
    base_emails = {email for _, email, _, _ in BASE_USERS}

    removed = Usuario.query.filter(~Usuario.email.in_(base_emails)).delete(
        synchronize_session=False
    )

    for nome, email, senha, perfil in BASE_USERS:
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario is None:
            usuario = Usuario(
                nome=nome,
                email=email,
                perfil=perfil,
                ativo=True,
                senha_hash=gerar_hash_senha(senha),
            )
            session.add(usuario)
            session.flush()
        else:
            usuario.nome = nome
            usuario.perfil = perfil
            usuario.ativo = True
            if not usuario.senha_hash:
                usuario.senha_hash = gerar_hash_senha(senha)
        users[email] = usuario

    return users, removed or 0


def _create_clean_property(session, users: dict[str, Usuario]) -> Propriedade:
    admin = users["admin@connectagro.com"]
    propriedade = Propriedade(
        usuario_id=admin.id,
        nome="Minha propriedade",
    )
    session.add(propriedade)
    session.flush()

    for usuario in users.values():
        session.add(UsuarioPropriedade(
            usuario_id=usuario.id,
            propriedade_id=propriedade.id,
            ativo=True,
            criado_por_id=admin.id,
        ))
    return propriedade


def analyze(app) -> dict:
    with app.app_context():
        db_path = Path(db.engine.url.database).resolve()
        upload_folder = _resolve_under_project(app.config["UPLOAD_FOLDER"])
        counts = _count_tables(db.session)
        users = [
            {
                "id": user.id,
                "nome": user.nome,
                "email": user.email,
                "perfil": user.perfil,
                "ativo": bool(user.ativo),
            }
            for user in Usuario.query.order_by(Usuario.id).all()
        ]
        return {
            "db_path": db_path,
            "upload_folder": upload_folder,
            "counts": counts,
            "users": users,
        }


def reset(app, dry_run: bool = False) -> dict:
    stamp = _timestamp()
    backup_dir = PROJECT_ROOT / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    with app.app_context():
        db_path = Path(db.engine.url.database).resolve()
        upload_folder = _resolve_under_project(app.config["UPLOAD_FOLDER"])
        generated_dirs = [
            _resolve_under_project(path)
            for path in GENERATED_DIR_CANDIDATES
            if _resolve_under_project(path).exists()
        ]

        before = _count_tables(db.session)
        result = {
            "db_path": str(db_path),
            "upload_folder": str(upload_folder),
            "before": before,
            "backups": {},
            "deleted": {},
            "files_removed": {},
            "preserved": list(PRESERVED_TABLES),
            "dry_run": dry_run,
        }

        if dry_run:
            return result

        result["backups"]["database"] = str(_backup_database(db_path, backup_dir, stamp))
        uploads_backup, upload_file_count = _backup_directory(
            upload_folder, backup_dir, "uploads_backup", stamp
        )
        result["backups"]["uploads"] = str(uploads_backup)
        result["backups"]["uploads_file_count"] = upload_file_count

        generated_backups = []
        for directory in generated_dirs:
            prefix = f"generated_files_backup_{directory.name}"
            backup_path, file_count = _backup_directory(directory, backup_dir, prefix, stamp)
            generated_backups.append({
                "source": str(directory),
                "backup": str(backup_path),
                "file_count": file_count,
            })
        result["backups"]["generated"] = generated_backups

        try:
            for table in DELETE_TABLES:
                result["deleted"][table] = db.session.execute(
                    db.text(f"delete from {table}")
                ).rowcount or 0

            users, removed_users = _ensure_base_users(db.session)
            result["deleted"]["usuario_nao_base"] = removed_users
            propriedade = _create_clean_property(db.session, users)
            db.session.commit()

            result["clean_property"] = {
                "id": propriedade.id,
                "nome": propriedade.nome,
            }
        except Exception:
            db.session.rollback()
            raise

        result["files_removed"]["uploads"] = _clear_directory_contents(upload_folder)
        for directory in generated_dirs:
            result["files_removed"][str(directory)] = _clear_directory_contents(directory)

        with app.app_context():
            result["after"] = _count_tables(db.session)
        return result


def print_analysis(info: dict) -> None:
    print(f"Banco SQLite: {info['db_path']}")
    print(f"Pasta de uploads: {info['upload_folder']}")
    print("Tabelas e registros:")
    for table, count in info["counts"].items():
        print(f"  {table}: {count}")
    print("Usuários:")
    for user in info["users"]:
        ativo = "ativo" if user["ativo"] else "inativo"
        print(f"  #{user['id']} {user['nome']} <{user['email']}> {user['perfil']} {ativo}")


def print_result(result: dict) -> None:
    print(f"Banco SQLite: {result['db_path']}")
    print(f"Pasta de uploads: {result['upload_folder']}")
    if result["dry_run"]:
        print("Modo dry-run: nenhuma alteração executada.")
        return

    print("Backups:")
    print(f"  banco: {result['backups']['database']}")
    print(f"  uploads: {result['backups']['uploads']} ({result['backups']['uploads_file_count']} arquivos)")
    if result["backups"]["generated"]:
        for item in result["backups"]["generated"]:
            print(f"  gerados: {item['backup']} ({item['file_count']} arquivos de {item['source']})")
    else:
        print("  gerados: nenhuma pasta encontrada")

    print("Registros removidos:")
    for table, count in result["deleted"].items():
        print(f"  {table}: {count}")

    print("Arquivos removidos:")
    for area, count in result["files_removed"].items():
        print(f"  {area}: {count}")

    print("Contagem final:")
    for table, count in result["after"].items():
        print(f"  {table}: {count}")

    prop = result.get("clean_property", {})
    print(f"Propriedade limpa de contexto: #{prop.get('id')} {prop.get('nome')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze", action="store_true", help="mostra inventário sem alterar dados")
    parser.add_argument("--dry-run", action="store_true", help="simula o reset sem alterar dados")
    parser.add_argument("--yes", action="store_true", help="confirma a limpeza operacional")
    args = parser.parse_args()

    app = create_app()
    if args.analyze:
        print_analysis(analyze(app))
        return 0

    if not args.yes and not args.dry_run:
        print("Use --yes para executar a limpeza ou --dry-run para simular.")
        return 2

    result = reset(app, dry_run=args.dry_run)
    print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
