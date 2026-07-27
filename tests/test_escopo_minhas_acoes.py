import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW_SOURCE = (
    ROOT / "app" / "views" / "plano_acao.py"
).read_text(encoding="utf-8")
TEMPLATE_SOURCE = (
    ROOT / "app" / "templates" / "minhas_acoes.html"
).read_text(encoding="utf-8")


class EscopoMinhasAcoesTests(unittest.TestCase):
    def test_basico_permanece_restrito_as_proprias_acoes(self):
        self.assertIn("if perfil == 'basico':", VIEW_SOURCE)
        self.assertIn(
            'filtros.append("a.responsavel_id = %s")',
            VIEW_SOURCE,
        )

    def test_intermediario_usa_centro_de_custos_do_responsavel(self):
        self.assertIn("elif perfil == 'intermediario':", VIEW_SOURCE)
        self.assertIn(
            'filtros.append("ur.centro_custos_id = %s")',
            VIEW_SOURCE,
        )
        self.assertIn(
            "JOIN usuarios ur ON a.responsavel_id = ur.id",
            VIEW_SOURCE,
        )

    def test_filtro_de_responsavel_e_aplicado_no_backend(self):
        self.assertIn("'responsavel_id': ''", VIEW_SOURCE)
        self.assertIn(
            "and perfil != 'basico'",
            VIEW_SOURCE,
        )
        self.assertIn(
            'filtros.append("a.responsavel_id = %s")',
            VIEW_SOURCE,
        )

    def test_template_habilita_responsavel_fora_do_perfil_basico(self):
        self.assertIn('name="responsavel_id"', TEMPLATE_SOURCE)
        self.assertIn(
            "session.get('perfil') == 'basico'",
            TEMPLATE_SOURCE,
        )
        self.assertIn("acao.nome_responsavel", TEMPLATE_SOURCE)

    def test_exportacao_preserva_filtro_de_responsavel(self):
        self.assertIn(
            "responsavel_id=filtros.get('responsavel_id','')",
            TEMPLATE_SOURCE,
        )
        self.assertIn(
            'query += " AND ur.centro_custos_id = %s"',
            VIEW_SOURCE,
        )


if __name__ == "__main__":
    unittest.main()
