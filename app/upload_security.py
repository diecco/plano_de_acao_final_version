import os
import shutil
from pathlib import Path
from uuid import uuid4

from flask import current_app


DIRETORIOS_PERSISTENTES = (
    "evidencias",
    "evidencias_treinamentos",
    "aprs",
    "pcpm_movimentacoes",
)


class UploadValidationError(ValueError):
    pass


_SIGNATURES = {
    "pdf": (b"%PDF-",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "jpeg": (b"\xff\xd8\xff",),
    "doc": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    "xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1",),
    "docx": (b"PK\x03\x04",),
    "xlsx": (b"PK\x03\x04",),
}


def _copiar_arquivos_ausentes(origem, destino):
    """Copia o conteúdo empacotado sem substituir arquivos já persistidos."""
    if not origem.is_dir():
        return

    for item in origem.rglob("*"):
        relativo = item.relative_to(origem)
        alvo = destino / relativo
        if item.is_dir():
            alvo.mkdir(parents=True, exist_ok=True)
        elif item.is_file() and not alvo.exists():
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, alvo)


def configurar_uploads_persistentes(app, raiz_uploads=None):
    """Liga os diretórios públicos de upload ao disco persistente do servidor."""
    valor_raiz = (
        raiz_uploads if raiz_uploads is not None else os.getenv("UPLOAD_ROOT", "")
    )
    valor_raiz = str(valor_raiz).strip()
    if not valor_raiz:
        return False

    raiz = Path(valor_raiz)
    if not raiz.is_absolute():
        raise RuntimeError("UPLOAD_ROOT deve apontar para um caminho absoluto.")

    raiz.mkdir(parents=True, exist_ok=True)
    raiz = raiz.resolve()
    static_root = Path(app.static_folder).resolve()

    for nome in DIRETORIOS_PERSISTENTES:
        origem = static_root / nome
        destino = raiz / nome
        destino.mkdir(parents=True, exist_ok=True)

        if origem.is_symlink():
            origem.unlink()
        elif origem.exists():
            _copiar_arquivos_ausentes(origem, destino)
            shutil.rmtree(origem)

        origem.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(str(destino), str(origem), target_is_directory=True)

    app.config["UPLOAD_ROOT"] = str(raiz)
    app.config["UPLOAD_FOLDER"] = str(raiz / "evidencias")
    app.logger.info("Uploads persistentes configurados em %s", raiz)
    return True


def validar_conteudo_upload(arquivo, extensoes_permitidas):
    """Confere extensão e assinatura binária sem consumir o stream do upload."""
    nome = getattr(arquivo, "filename", "") or ""
    extensao = Path(nome).suffix.lower().lstrip(".")
    permitidas = {item.lower().lstrip(".") for item in extensoes_permitidas}

    if not extensao or extensao not in permitidas:
        raise UploadValidationError("Tipo de arquivo não permitido.")

    posicao = arquivo.stream.tell()
    cabecalho = arquivo.stream.read(16)
    arquivo.stream.seek(posicao)

    assinaturas = _SIGNATURES.get(extensao)
    if not assinaturas or not any(cabecalho.startswith(item) for item in assinaturas):
        raise UploadValidationError(
            "O conteúdo do arquivo não corresponde à extensão informada."
        )

    return extensao


class UploadService:
    """Ponto único para validação, nomenclatura, gravação e exclusão de uploads."""

    @staticmethod
    def resolver_diretorio(diretorio=None):
        if diretorio is None:
            diretorio = current_app.config.get(
                "UPLOAD_FOLDER", os.path.join("static", "evidencias")
            )

        if not os.path.isabs(diretorio):
            partes = list(Path(os.path.normpath(diretorio)).parts)
            if partes and partes[0].lower() == "app":
                partes = partes[1:]
            diretorio = os.path.join(current_app.root_path, *partes)

        caminho = os.path.abspath(diretorio)
        os.makedirs(caminho, exist_ok=True)
        return caminho

    @classmethod
    def salvar(cls, arquivo, extensoes_permitidas, prefixo, diretorio=None):
        if not arquivo or not getattr(arquivo, "filename", ""):
            return None

        extensao = validar_conteudo_upload(arquivo, extensoes_permitidas)
        nome = f"{prefixo}_{uuid4().hex}.{extensao}"
        destino = cls.resolver_diretorio(diretorio)
        arquivo.save(os.path.join(destino, nome))
        return nome

    @classmethod
    def excluir(cls, nome, diretorio=None):
        if not nome or os.path.basename(nome) != nome:
            return False

        destino = cls.resolver_diretorio(diretorio)
        caminho = os.path.abspath(os.path.join(destino, nome))
        if os.path.commonpath((destino, caminho)) != destino:
            return False
        if not os.path.isfile(caminho):
            return False

        os.remove(caminho)
        return True
