"""Upload de arquivos — escopo: propriedade do usuário logado."""
import os
from uuid import uuid4

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from ...extensions import db
from ...models import UploadArquivo
from ...utils.auth import login_required
from ...services.auditoria_service import registrar_sucesso
from ...utils.contexto import propriedade_atual, vazio_para_none
from ...utils.permissions import require_permission
from . import upload_bp

EXTENSOES_PERMITIDAS = {"pdf", "png", "jpg", "jpeg", "csv", "xlsx", "txt", "docx"}


def extensao_permitida(nome_arquivo):
    """Confere a extensão por allowlist, bloqueando todo o restante."""
    if not nome_arquivo or "." not in nome_arquivo:
        return False
    ext = nome_arquivo.rsplit(".", 1)[1].lower()
    return ext in EXTENSOES_PERMITIDAS


def gerar_nome_arquivo_seguro(nome_original):
    """Gera nome único preservando extensão e usando `secure_filename`."""
    nome_seguro = secure_filename(nome_original or "")
    if not nome_seguro or not extensao_permitida(nome_seguro):
        return None
    return f"{uuid4().hex}_{nome_seguro}"


def _nome_original_visivel(nome_arquivo):
    """Remove componentes de caminho do nome recebido pelo navegador."""
    normalizado = (nome_arquivo or "").replace("\\", "/")
    return normalizado.rsplit("/", 1)[-1]


def _pasta_base_upload():
    pasta = current_app.config["UPLOAD_FOLDER"]
    if not os.path.isabs(pasta):
        pasta = os.path.abspath(pasta)
    os.makedirs(pasta, exist_ok=True)
    return pasta


def obter_pasta_upload_propriedade(propriedade_id):
    """Retorna (pasta_absoluta, pasta_relativa) da propriedade atual."""
    pasta_base = _pasta_base_upload()
    pasta_relativa = f"propriedade_{propriedade_id}"
    pasta_absoluta = os.path.abspath(os.path.join(pasta_base, pasta_relativa))
    if os.path.commonpath([pasta_base, pasta_absoluta]) != pasta_base:
        abort(400)
    os.makedirs(pasta_absoluta, exist_ok=True)
    return pasta_absoluta, pasta_relativa


def _caminho_absoluto_upload(caminho_relativo):
    pasta_base = _pasta_base_upload()
    partes = str(caminho_relativo or "").replace("\\", "/").split("/")
    caminho = os.path.abspath(os.path.join(pasta_base, *partes))
    if os.path.commonpath([pasta_base, caminho]) != pasta_base:
        abort(404)
    return caminho


def tamanho_arquivo(file_storage):
    """Calcula o tamanho do arquivo sem consumir o stream."""
    stream = file_storage.stream
    posicao = stream.tell()
    stream.seek(0, os.SEEK_END)
    tamanho = stream.tell()
    stream.seek(posicao)
    return tamanho


def formatar_tamanho(bytes_):
    if bytes_ is None:
        return "—"
    unidades = ("B", "KB", "MB", "GB")
    valor = float(bytes_)
    for unidade in unidades:
        if valor < 1024 or unidade == unidades[-1]:
            return f"{valor:.1f} {unidade}" if unidade != "B" else f"{int(valor)} B"
        valor /= 1024
    return f"{bytes_} B"


def _arquivo_da_propriedade_ou_404(arquivo_id, propriedade):
    arquivo = UploadArquivo.query.filter_by(
        id=arquivo_id, propriedade_id=propriedade.id).first()
    if arquivo is None:
        abort(404)
    return arquivo


def _max_upload_mb():
    limite = current_app.config.get("MAX_CONTENT_LENGTH")
    if not limite:
        return None
    return round(limite / (1024 * 1024), 1)


def _validar_upload(file_storage):
    if file_storage is None or not file_storage.filename:
        return None, "Selecione um arquivo para enviar."

    nome_original = _nome_original_visivel(file_storage.filename)
    if not nome_original:
        return None, "O nome original do arquivo não pode ser vazio."
    if not extensao_permitida(nome_original):
        permitidas = ", ".join(sorted(EXTENSOES_PERMITIDAS))
        return None, f"Extensão não permitida. Use apenas: {permitidas}."

    nome_salvo = gerar_nome_arquivo_seguro(nome_original)
    if not nome_salvo:
        return None, "Nome de arquivo inválido."

    tamanho = tamanho_arquivo(file_storage)
    limite = current_app.config.get("MAX_CONTENT_LENGTH")
    if limite and tamanho > limite:
        return None, "Arquivo maior que o limite permitido."

    file_storage.stream.seek(0)
    return {"nome_original": nome_original, "nome_salvo": nome_salvo, "tamanho": tamanho}, None


@upload_bp.route("/")
@login_required
@require_permission("upload.view")
def index():
    propriedade = propriedade_atual()
    arquivos = (UploadArquivo.query
                .filter_by(propriedade_id=propriedade.id)
                .order_by(UploadArquivo.enviado_em.desc(), UploadArquivo.id.desc())
                .all())
    return render_template("upload/list.html", arquivos=arquivos,
                           formatar_tamanho=formatar_tamanho)


@upload_bp.route("/novo", methods=["GET", "POST"])
@login_required
@require_permission("upload.create")
def novo():
    propriedade = propriedade_atual()
    if request.method == "POST":
        file_storage = request.files.get("arquivo")
        dados_upload, erro = _validar_upload(file_storage)
        if erro:
            flash(erro, "error")
            return render_template("upload/form.html", form=request.form,
                                   extensoes=sorted(EXTENSOES_PERMITIDAS),
                                   max_upload_mb=_max_upload_mb()), 400

        pasta_absoluta, pasta_relativa = obter_pasta_upload_propriedade(propriedade.id)
        caminho_absoluto = os.path.abspath(os.path.join(pasta_absoluta, dados_upload["nome_salvo"]))
        if os.path.commonpath([pasta_absoluta, caminho_absoluto]) != pasta_absoluta:
            abort(400)
        file_storage.save(caminho_absoluto)

        caminho_relativo = f"{pasta_relativa}/{dados_upload['nome_salvo']}"
        arquivo = UploadArquivo(
            propriedade_id=propriedade.id,
            nome_original=dados_upload["nome_original"],
            caminho=caminho_relativo,
            tipo_mime=file_storage.mimetype,
            tamanho=dados_upload["tamanho"],
            descricao=vazio_para_none(request.form.get("descricao")),
        )
        db.session.add(arquivo)
        db.session.commit()
        registrar_sucesso("upload.create", entidade="upload_arquivo",
                          entidade_id=arquivo.id, descricao="Arquivo enviado",
                          propriedade_id=propriedade.id, request=request)
        flash("Arquivo enviado com sucesso.", "success")
        return redirect(url_for("upload.index"))

    return render_template("upload/form.html", form={},
                           extensoes=sorted(EXTENSOES_PERMITIDAS),
                           max_upload_mb=_max_upload_mb())


@upload_bp.route("/<int:arquivo_id>/download")
@login_required
@require_permission("upload.download")
def download(arquivo_id):
    propriedade = propriedade_atual()
    arquivo = _arquivo_da_propriedade_ou_404(arquivo_id, propriedade)
    caminho_absoluto = _caminho_absoluto_upload(arquivo.caminho)
    if not os.path.isfile(caminho_absoluto):
        abort(404)
    registrar_sucesso("upload.download", entidade="upload_arquivo",
                      entidade_id=arquivo.id, descricao="Download de arquivo",
                      propriedade_id=propriedade.id, request=request)
    return send_from_directory(
        _pasta_base_upload(),
        arquivo.caminho,
        as_attachment=True,
        download_name=arquivo.nome_original,
    )


@upload_bp.route("/<int:arquivo_id>/remover", methods=["POST"])
@login_required
@require_permission("upload.delete")
def remover(arquivo_id):
    propriedade = propriedade_atual()
    arquivo = _arquivo_da_propriedade_ou_404(arquivo_id, propriedade)
    caminho_absoluto = _caminho_absoluto_upload(arquivo.caminho)
    arquivo_existia = os.path.isfile(caminho_absoluto)
    if arquivo_existia:
        os.remove(caminho_absoluto)
    db.session.delete(arquivo)
    db.session.commit()
    registrar_sucesso("upload.delete", entidade="upload_arquivo",
                      entidade_id=arquivo_id, descricao="Arquivo removido",
                      propriedade_id=propriedade.id, request=request)
    if arquivo_existia:
        flash("Arquivo removido.", "success")
    else:
        flash("Registro removido. O arquivo físico já não existia.", "warning")
    return redirect(url_for("upload.index"))
