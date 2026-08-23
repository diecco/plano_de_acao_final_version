import pathlib
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]


class AgendamentoColaboradorOpcionalTests(unittest.TestCase):
    def test_backend_nao_exige_colaborador_previsto(self):
        view = (ROOT / "app" / "views" / "agenda_ssma.py").read_text(encoding="utf-8")
        self.assertNotIn(
            '"Selecione o colaborador previsto para "',
            view,
        )
        self.assertIn("if colaborador_previsto_id:", view)

    def test_template_identifica_campo_como_opcional(self):
        template = (
            ROOT / "app" / "templates" / "novo_agendamento_ssma.html"
        ).read_text(encoding="utf-8")
        self.assertIn("Colaborador previsto", template)
        self.assertIn("(opcional)", template)
        self.assertNotIn("alert('Selecione o colaborador na lista de resultados.')", template)

    def test_execucao_auditoria_continua_exigindo_auditado(self):
        auditoria = (
            ROOT / "app" / "views" / "auditoria_padrao.py"
        ).read_text(encoding="utf-8")
        self.assertIn("auditado_id", auditoria)
        self.assertIn('"Preencha todos os campos obrigatórios."', auditoria)


if __name__ == "__main__":
    unittest.main()
