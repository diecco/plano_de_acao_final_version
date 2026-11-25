import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class IfsClienteTests(unittest.TestCase):
    def test_peso_c_segue_revisao_13_do_formulario(self):
        view = (ROOT / "app" / "views" / "ifs_cliente.py").read_text(
            encoding="utf-8"
        )
        cliente = (
            ROOT / "app" / "templates" / "nova_ifs_cliente.html"
        ).read_text(encoding="utf-8")
        lancar = (ROOT / "app" / "templates" / "lancar_ifs.html").read_text(
            encoding="utf-8"
        )
        editar = (ROOT / "app" / "templates" / "editar_ifs.html").read_text(
            encoding="utf-8"
        )

        self.assertIn('"C": 0.5', view)
        self.assertIn("p==='C'?0.5:(p==='B'?1:0)", cliente)
        self.assertIn('potencial === "C"', lancar)
        self.assertIn("potencial === 'C' ? 0.5 : (potencial === 'B' ? 1 : 0)", editar)

    def test_migracao_rev13_substitui_catalogo_sem_apagar_historico(self):
        migration = (
            ROOT / "docs" / "atualizar_catalogo_ifs_rev13.sql"
        ).read_text(encoding="utf-8")

        self.assertEqual(migration.count("INSERT INTO ifs_blocos ("), 28)
        self.assertEqual(migration.count("INSERT INTO ifs_itens ("), 328)
        self.assertIn(
            "UPDATE ifs_itens SET ativo = 0 WHERE id > 0 AND ativo = 1",
            migration,
        )
        self.assertIn(
            "UPDATE ifs_blocos SET ativo = 0 WHERE id > 0 AND ativo = 1",
            migration,
        )
        self.assertNotIn("DELETE FROM ifs_", migration)
        self.assertIn("'REV13-2026-04'", migration)

        ifs_view = (ROOT / "app" / "views" / "ifs.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("if respostas_lista:", ifs_view)
        self.assertIn("JOIN ifs_respostas r ON r.item_id = i.id", ifs_view)

    def test_catalogo_comportamento_e_alinhado_ao_formulario_cliente(self):
        migration = (
            ROOT / "docs" / "alinhar_itens_comportamento_ifs.sql"
        ).read_text(encoding="utf-8")

        for numero in range(1, 15):
            self.assertIn(f"'25.{numero}'", migration)
        self.assertIn("SET ativo = 0", migration)
        self.assertIn("codigo NOT IN", migration)
        self.assertIn("COUNT(*) AS total_itens_ativos", migration)

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
