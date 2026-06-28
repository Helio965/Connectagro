"""Testes do Upload de Arquivos (Etapa 5.7)."""
import io
import os

import pytest

from app.extensions import db
from app.utils.auth import gerar_hash_senha


def _criar_usuario_com_propriedade(email):
    from app.models import Propriedade, Usuario

    usuario = Usuario(nome=email, email=email, perfil="tecnico", ativo=True,
                      senha_hash=gerar_hash_senha("senha123"))
    db.session.add(usuario)
    db.session.commit()
    propriedade = Propriedade(usuario_id=usuario.id, nome="Fazenda " + email)
    db.session.add(propriedade)
    db.session.commit()
    return {"usuario_id": usuario.id, "propriedade_id": propriedade.id}


@pytest.fixture
def app_db(app, tmp_path):
    app.config["UPLOAD_FOLDER"] = str(tmp_path)
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    with app.app_context():
        db.create_all()
        _criar_usuario_com_propriedade("a@connectagro.com")
        _criar_usuario_com_propriedade("b@connectagro.com")
    return app


def _login(app_db, email):
    client = app_db.test_client()
    client.post("/auth/login", data={"email": email, "senha": "senha123"})
    return client


def _upload(client, nome="relatorio.pdf", conteudo=b"conteudo", descricao="Documento da safra"):
    return client.post(
        "/upload/novo",
        data={"arquivo": (io.BytesIO(conteudo), nome), "descricao": descricao},
        content_type="multipart/form-data",
    )


def _primeiro_upload(app_db):
    from app.models import UploadArquivo

    with app_db.app_context():
        return UploadArquivo.query.first()


def test_index_exige_login(app_db):
    resp = app_db.test_client().get("/upload/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_novo_exige_login(app_db):
    resp = app_db.test_client().get("/upload/novo")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["Location"]


def test_index_com_login_200(app_db):
    assert _login(app_db, "a@connectagro.com").get("/upload/").status_code == 200


def test_upload_valido_cria_registro_e_arquivo_fisico(app_db):
    from app.models import UploadArquivo

    client = _login(app_db, "a@connectagro.com")
    assert _upload(client).status_code == 302
    with app_db.app_context():
        arquivo = UploadArquivo.query.first()
        assert arquivo is not None
        assert arquivo.nome_original == "relatorio.pdf"
        assert arquivo.descricao == "Documento da safra"
        assert arquivo.tipo_mime == "application/pdf"
        assert arquivo.tamanho == len(b"conteudo")
        assert not os.path.isabs(arquivo.caminho)
        assert arquivo.caminho.startswith("propriedade_")
        assert os.path.exists(os.path.join(app_db.config["UPLOAD_FOLDER"], *arquivo.caminho.split("/")))


def test_nome_salvo_usa_secure_filename_e_nome_unico(app_db):
    client = _login(app_db, "a@connectagro.com")
    assert _upload(client, nome="meu relatório 2026.pdf").status_code == 302
    with app_db.app_context():
        arquivo = _primeiro_upload(app_db)
        nome_salvo = arquivo.caminho.split("/")[-1]
        assert nome_salvo.endswith("meu_relatorio_2026.pdf")
        assert nome_salvo != arquivo.nome_original
        assert " " not in nome_salvo


def test_upload_sem_arquivo_400(app_db):
    client = _login(app_db, "a@connectagro.com")
    resp = client.post("/upload/novo", data={"descricao": "x"}, content_type="multipart/form-data")
    assert resp.status_code == 400


@pytest.mark.parametrize("nome", ["malware.exe", "script.py", "pagina.html", "compactado.zip"])
def test_upload_extensao_proibida_400(app_db, nome):
    client = _login(app_db, "a@connectagro.com")
    assert _upload(client, nome=nome).status_code == 400


@pytest.mark.parametrize("nome", ["arquivo.pdf", "imagem.png", "foto.jpg", "dados.csv", "planilha.xlsx", "nota.txt", "doc.docx"])
def test_upload_extensao_permitida_funciona(app_db, nome):
    client = _login(app_db, "a@connectagro.com")
    assert _upload(client, nome=nome).status_code == 302


def test_nome_malicioso_nao_sai_da_pasta_upload(app_db):
    client = _login(app_db, "a@connectagro.com")
    assert _upload(client, nome="../../teste.pdf").status_code == 302
    with app_db.app_context():
        arquivo = _primeiro_upload(app_db)
        assert not os.path.isabs(arquivo.caminho)
        assert ".." not in arquivo.caminho
        caminho_fisico = os.path.abspath(os.path.join(app_db.config["UPLOAD_FOLDER"], *arquivo.caminho.split("/")))
        assert os.path.commonpath([os.path.abspath(app_db.config["UPLOAD_FOLDER"]), caminho_fisico]) == os.path.abspath(app_db.config["UPLOAD_FOLDER"])
        assert os.path.exists(caminho_fisico)


def test_listagem_exibe_nome_descricao_e_download(app_db):
    client = _login(app_db, "a@connectagro.com")
    _upload(client, nome="contrato.pdf", descricao="Contrato de arrendamento")
    corpo = client.get("/upload/").data.decode("utf-8")
    assert "contrato.pdf" in corpo
    assert "Contrato de arrendamento" in corpo
    assert "/upload/" in corpo and "/download" in corpo


def test_download_arquivo_proprio_funciona(app_db):
    client = _login(app_db, "a@connectagro.com")
    _upload(client, nome="relatorio.txt", conteudo=b"abc")
    arquivo = _primeiro_upload(app_db)
    resp = client.get(f"/upload/{arquivo.id}/download")
    assert resp.status_code == 200
    assert resp.data == b"abc"
    assert "attachment" in resp.headers.get("Content-Disposition", "")
    assert "relatorio.txt" in resp.headers.get("Content-Disposition", "")


def test_download_arquivo_de_outra_propriedade_404(app_db):
    client_a = _login(app_db, "a@connectagro.com")
    _upload(client_a)
    arquivo = _primeiro_upload(app_db)
    client_b = _login(app_db, "b@connectagro.com")
    assert client_b.get(f"/upload/{arquivo.id}/download").status_code == 404


def test_remover_arquivo_proprio_remove_registro_e_arquivo_fisico(app_db):
    from app.models import UploadArquivo

    client = _login(app_db, "a@connectagro.com")
    _upload(client)
    arquivo = _primeiro_upload(app_db)
    caminho_fisico = os.path.join(app_db.config["UPLOAD_FOLDER"], *arquivo.caminho.split("/"))
    assert os.path.exists(caminho_fisico)
    assert client.post(f"/upload/{arquivo.id}/remover").status_code == 302
    with app_db.app_context():
        assert db.session.get(UploadArquivo, arquivo.id) is None
    assert not os.path.exists(caminho_fisico)


def test_remover_arquivo_de_outra_propriedade_404(app_db):
    client_a = _login(app_db, "a@connectagro.com")
    _upload(client_a)
    arquivo = _primeiro_upload(app_db)
    client_b = _login(app_db, "b@connectagro.com")
    assert client_b.post(f"/upload/{arquivo.id}/remover").status_code == 404


def test_remover_registro_sem_arquivo_fisico_nao_quebra(app_db):
    from app.models import UploadArquivo

    client = _login(app_db, "a@connectagro.com")
    _upload(client)
    arquivo = _primeiro_upload(app_db)
    caminho_fisico = os.path.join(app_db.config["UPLOAD_FOLDER"], *arquivo.caminho.split("/"))
    os.remove(caminho_fisico)
    assert client.post(f"/upload/{arquivo.id}/remover").status_code == 302
    with app_db.app_context():
        assert db.session.get(UploadArquivo, arquivo.id) is None


def test_upload_nao_cria_preco_nem_imagem(app_db):
    from app.models import ProdutoImagem, ProdutoPreco

    client = _login(app_db, "a@connectagro.com")
    _upload(client)
    with app_db.app_context():
        assert ProdutoPreco.query.count() == 0
        assert ProdutoImagem.query.count() == 0
