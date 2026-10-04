import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class GlobalConfirmationModalTests(unittest.TestCase):
    def test_layout_includes_reusable_confirmation_modal(self):
        layout = (ROOT / "app" / "templates" / "layout.html").read_text(
            encoding="utf-8"
        )
        component = (
            ROOT / "app" / "templates" / "components" / "modal_confirmacao.html"
        ).read_text(encoding="utf-8")

        self.assertIn("components/modal_confirmacao.html", layout)
        self.assertIn('id="modalConfirmacaoSistema"', component)
        self.assertIn('class="modal-footer justify-content-between"', component)
        self.assertIn('class="btn btn-cinza"', component)
        self.assertIn('class="btn btn-laranja"', component)

    def test_global_script_migrates_legacy_confirmations(self):
        script = (ROOT / "app" / "static" / "js" / "layout.js").read_text(
            encoding="utf-8"
        )

        self.assertIn("window.confirmarAcaoSistema", script)
        self.assertIn('document.querySelectorAll("form[onsubmit]")', script)
        self.assertIn("form.removeAttribute(\"onsubmit\")", script)
        self.assertIn("trigger.removeAttribute(\"onclick\")", script)
        self.assertIn('form[data-confirmacao]', script)
        self.assertIn('a[data-confirmacao]', script)

    def test_programmatic_confirmation_uses_global_modal(self):
        template = (
            ROOT / "app" / "templates" / "investigacao_causa_raiz_detalhe.html"
        ).read_text(encoding="utf-8")

        self.assertNotIn("window.confirm(", template)
        self.assertIn("window.confirmarAcaoSistema", template)


if __name__ == "__main__":
    unittest.main()
