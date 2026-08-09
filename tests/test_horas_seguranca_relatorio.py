import unittest
from datetime import date, time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HorasSegurancaRelatorioTests(unittest.TestCase):
    def test_listagem_expoe_detalhes_e_pdf_sem_liberar_edicao(self):
        template = (ROOT / "app" / "templates" / "listar_hs.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('title="Ver detalhes"', template)
        self.assertIn("detalhes-hs-{{ hs.id }}", template)
        self.assertIn("main.relatorio_pdf_hs", template)
        self.assertIn("itens_por_registro.get(hs.id|string, [])", template)
        self.assertIn("{% if hs.id_auditor == session.get('usuario_id') %}", template)

    def test_pdf_usa_mesmo_escopo_de_acesso_da_listagem(self):
        view = (ROOT / "app" / "views" / "horas_seguranca.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("def _buscar_detalhes_hora_seguranca", view)
        self.assertIn('pode_acessar_ssma(cursor, "hs", registro_id)', view)
        self.assertIn("def relatorio_pdf_hs", view)
        self.assertIn('mimetype="application/pdf"', view)
        self.assertIn("FROM hs_respostas resp", view)

    def test_gerador_pdf_retorna_documento_valido(self):
        from app.utils.hs_pdf import gerar_pdf_hora_seguranca

        registro = {
            "id": 10,
            "data": date(2026, 8, 9),
            "hora": time(8, 30),
            "turno": "Manhã",
            "local": "Oficina",
            "nome_tema": "Pré uso",
            "nome_auditor": "Auditor de Teste",
            "matricula_auditor": "001234",
            "centro_codigo": "1.10.0052.13",
            "centro_descricao": "Gerdau - Ouro Branco",
            "nomes_participantes": "Participante de Teste",
        }
        itens = [
            {
                "texto": "Condições verificadas?",
                "resultado": "NC",
                "descricao_desvio": "Proteção ausente.",
                "descricao_acao": "Instalar proteção.",
                "prazo_acao": date(2026, 8, 15),
            }
        ]
        pdf = gerar_pdf_hora_seguranca(registro, itens)
        self.assertTrue(pdf.getvalue().startswith(b"%PDF"))
        self.assertGreater(len(pdf.getvalue()), 1000)


if __name__ == "__main__":
    unittest.main()
