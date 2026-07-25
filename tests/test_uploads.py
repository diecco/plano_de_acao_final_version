import unittest
import importlib.util
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import patch

from flask import Flask


ROOT = Path(__file__).resolve().parents[1]
INIT_SOURCE = (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")
ROUTES_SOURCE = "\n".join(
    (
        (ROOT / "app" / "routes.py").read_text(encoding="utf-8"),
        (ROOT / "app" / "views" / "apr.py").read_text(encoding="utf-8"),
        (ROOT / "app" / "views" / "plano_acao.py").read_text(encoding="utf-8"),
    )
)
CONFIG_SOURCE = (ROOT / "app" / "config_local.py").read_text(encoding="utf-8")

spec = importlib.util.spec_from_file_location(
    "upload_security", ROOT / "app" / "upload_security.py"
)
upload_security = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upload_security)


class UploadRegressionTests(unittest.TestCase):
    @staticmethod
    def _arquivo(nome, conteudo):
        stream = BytesIO(conteudo)
        return SimpleNamespace(
            filename=nome,
            stream=stream,
            save=lambda destino: Path(destino).write_bytes(stream.getvalue()),
        )

    def test_pdf_valido_e_aceito_pela_assinatura(self):
        arquivo = SimpleNamespace(filename="documento.pdf", stream=BytesIO(b"%PDF-1.7\n"))
        self.assertEqual(
            upload_security.validar_conteudo_upload(arquivo, {"pdf"}),
            "pdf",
        )

    def test_executavel_renomeado_para_pdf_e_rejeitado(self):
        arquivo = SimpleNamespace(filename="documento.pdf", stream=BytesIO(b"MZ\x90\x00"))
        with self.assertRaises(upload_security.UploadValidationError):
            upload_security.validar_conteudo_upload(arquivo, {"pdf"})

    def test_validacao_preserva_posicao_do_stream(self):
        stream = BytesIO(b"%PDF-1.7\nconteudo")
        stream.seek(2)
        arquivo = SimpleNamespace(filename="documento.pdf", stream=stream)
        with self.assertRaises(upload_security.UploadValidationError):
            upload_security.validar_conteudo_upload(arquivo, {"pdf"})
        self.assertEqual(stream.tell(), 2)

    def test_aplicacao_limita_tamanho_da_requisicao(self):
        self.assertIn("app.config['MAX_CONTENT_LENGTH']", INIT_SOURCE)

    def test_erro_de_tamanho_tem_resposta_para_tela_e_api(self):
        self.assertIn("@main_routes.app_errorhandler(413)", ROUTES_SOURCE)
        self.assertIn("request.path.startswith('/api/')", ROUTES_SOURCE)

    def test_evidencia_de_acao_nao_usa_nome_original_como_chave(self):
        self.assertIn('prefixo=f"evidencia_acao_{acao_id}"', ROUTES_SOURCE)

    def test_apr_recebe_identificador_unico(self):
        self.assertIn('prefixo="apr"', ROUTES_SOURCE)
        self.assertIn('prefixo=f"apr_{id}"', ROUTES_SOURCE)

    def test_servico_salva_nomes_unicos_e_exclui_com_seguranca(self):
        app = Flask(__name__)
        with TemporaryDirectory() as pasta, app.app_context():
            primeiro = upload_security.UploadService.salvar(
                self._arquivo("mesmo.pdf", b"%PDF-1.7\nA"),
                {"pdf"},
                prefixo="teste",
                diretorio=pasta,
            )
            segundo = upload_security.UploadService.salvar(
                self._arquivo("mesmo.pdf", b"%PDF-1.7\nB"),
                {"pdf"},
                prefixo="teste",
                diretorio=pasta,
            )

            self.assertNotEqual(primeiro, segundo)
            self.assertTrue((Path(pasta) / primeiro).is_file())
            self.assertFalse(upload_security.UploadService.excluir("../fora.pdf", pasta))
            self.assertTrue(upload_security.UploadService.excluir(primeiro, pasta))
            self.assertFalse((Path(pasta) / primeiro).exists())

    def test_uploads_persistentes_migram_arquivos_sem_sobrescrever(self):
        with TemporaryDirectory() as pasta:
            base = Path(pasta)
            static = base / "static"
            persistente = base / "persistente"
            origem = static / "evidencias"
            destino = persistente / "evidencias"
            origem.mkdir(parents=True)
            destino.mkdir(parents=True)
            (origem / "novo.pdf").write_bytes(b"novo")
            (origem / "existente.pdf").write_bytes(b"versao-pacote")
            (destino / "existente.pdf").write_bytes(b"versao-disco")

            app = Flask(__name__, static_folder=str(static))
            with patch.object(upload_security.os, "symlink") as criar_link:
                configurado = upload_security.configurar_uploads_persistentes(
                    app, persistente
                )

            self.assertTrue(configurado)
            self.assertEqual((destino / "novo.pdf").read_bytes(), b"novo")
            self.assertEqual(
                (destino / "existente.pdf").read_bytes(), b"versao-disco"
            )
            self.assertFalse(origem.exists())
            self.assertEqual(criar_link.call_count, 4)
            self.assertEqual(app.config["UPLOAD_FOLDER"], str(destino.resolve()))

    def test_upload_root_relativo_e_rejeitado(self):
        app = Flask(__name__)
        with self.assertRaisesRegex(RuntimeError, "caminho absoluto"):
            upload_security.configurar_uploads_persistentes(
                app, "uploads-relativos"
            )

    def test_sem_upload_root_mantem_ambiente_local(self):
        app = Flask(__name__)
        with patch.dict(upload_security.os.environ, {}, clear=True):
            self.assertFalse(
                upload_security.configurar_uploads_persistentes(app)
            )

    def test_rotas_nao_salvam_uploads_diretamente(self):
        self.assertNotIn("arquivo.save(", ROUTES_SOURCE)
        self.assertNotIn("arquivo_foto.save(", ROUTES_SOURCE)
        self.assertNotIn("foto.save(", ROUTES_SOURCE)

    def test_configuracao_nao_contem_credenciais_literais(self):
        self.assertIn('os.getenv("DATABASE_URL")', CONFIG_SOURCE)
        self.assertIn('os.getenv("MAIL_PASSWORD")', CONFIG_SOURCE)


if __name__ == "__main__":
    unittest.main()
