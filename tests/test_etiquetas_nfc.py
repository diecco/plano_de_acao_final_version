from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class EtiquetasNfcTest(unittest.TestCase):
    def test_migracao_cria_catalogo_e_abrangencia(self):
        sql = (ROOT / "docs" / "criar_cadastro_etiquetas_nfc.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS nfc_etiquetas", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS nfc_etiquetas_centros", sql)
        self.assertIn("UNIQUE KEY uk_nfc_etiquetas_numero", sql)
        self.assertIn("UNIQUE KEY uk_nfc_etiquetas_token", sql)

    def test_rotas_exigem_administrador_e_geram_token(self):
        source = (ROOT / "app" / "views" / "etiquetas_nfc.py").read_text(encoding="utf-8")
        self.assertEqual(source.count("@admin_required"), 2)
        self.assertIn('secrets.token_urlsafe(32)', source)
        self.assertIn('/administracao/etiquetas-nfc', source)

    def test_template_e_sidebar_expoem_cadastro(self):
        template = (ROOT / "app" / "templates" / "etiquetas_nfc.html").read_text(encoding="utf-8")
        sidebar = (ROOT / "app" / "templates" / "components" / "sidebar.html").read_text(encoding="utf-8")
        for campo in ('name="numero"', 'name="descricao"', 'name="abrangencia"', 'name="centro_custos_ids"'):
            self.assertIn(campo, template)
        self.assertIn("main.etiquetas_nfc", sidebar)
        self.assertIn("Etiquetas NFC", sidebar)

    def test_listagem_segue_padrao_administrativo(self):
        template = (ROOT / "app" / "templates" / "etiquetas_nfc.html").read_text(encoding="utf-8")
        source = (ROOT / "app" / "views" / "etiquetas_nfc.py").read_text(encoding="utf-8")
        self.assertIn("Etiquetas cadastradas", template)
        self.assertIn("Aplicar filtros", template)
        self.assertIn("Limpar filtros", template)
        self.assertIn("Nova etiqueta", template)
        self.assertIn("btn-acao-icon", template)
        self.assertIn("lista_url", template)
        self.assertIn("total_paginas", template)
        self.assertIn("colunas_ordenacao", source)
        self.assertIn("LIMIT %s OFFSET %s", source)
        self.assertIn("por_pagina = 30", source)
        self.assertNotIn("Por página", template)


if __name__ == "__main__":
    unittest.main()
