import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IfsClienteTests(unittest.TestCase):
    def test_rotas_exigem_gestor_ssma(self):
        source = (ROOT / "app" / "views" / "ifs_cliente.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("@gestor_ssma_required"), 4)
        self.assertIn('ORIGEM_IFS_CLIENTE = "IFS do Cliente"', source)

    def test_sidebar_fica_em_gestao_ssma(self):
        sidebar = (ROOT / "app" / "templates" / "components" / "sidebar.html").read_text(encoding="utf-8")
        trecho = sidebar[sidebar.index('id="menuGestaoSsma"'):]
        self.assertIn("main.listar_ifs_cliente", trecho)
        self.assertIn("IFS do Cliente", trecho)
        self.assertIn("session.get('gestor_ssma')", trecho)

    def test_na_e_multiplas_acoes(self):
        template = (ROOT / "app" / "templates" / "nova_ifs_cliente.html").read_text(encoding="utf-8")
        migration = (ROOT / "docs" / "criar_ifs_cliente.sql").read_text(encoding="utf-8")
        self.assertIn('<option value="NA" selected>NA</option>', template)
        self.assertIn("adicionarAcao", template)
        self.assertIn("if(s.value==='N')abrirTratativa(s)", template)
        self.assertNotIn("const modal=bootstrap", template)
        self.assertIn("ifs_cliente_desvio_acoes", migration)


if __name__ == "__main__":
    unittest.main()
