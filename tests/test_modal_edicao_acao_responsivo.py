import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ModalEdicaoAcaoResponsivoTests(unittest.TestCase):
    def test_regras_responsivas_estao_centralizadas_no_layout(self):
        css = (ROOT / "app" / "static" / "css" / "layout.css").read_text(
            encoding="utf-8"
        )

        self.assertIn("#modalEditarAcao .modal-content", css)
        self.assertIn("#modalEditarAcao #formEditarAcaoModal", css)
        self.assertIn("max-height: calc(100dvh - 2rem)", css)
        self.assertIn("overflow-y: auto", css)
        self.assertIn("#modalEditarAcao .modal-footer", css)

    def test_os_dois_modais_usam_a_estrutura_responsiva(self):
        for nome_template in ("minhas_acoes.html", "acoes_criadas.html"):
            with self.subTest(template=nome_template):
                template = (
                    ROOT / "app" / "templates" / nome_template
                ).read_text(encoding="utf-8")
                self.assertIn('id="modalEditarAcao"', template)
                self.assertIn('id="formEditarAcaoModal"', template)
                self.assertIn('class="modal-footer"', template)
                self.assertIn("modal-dialog-scrollable", template)


if __name__ == "__main__":
    unittest.main()
