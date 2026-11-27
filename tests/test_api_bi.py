import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ApiBiStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.view = (ROOT / "app" / "views" / "api_bi.py").read_text(
            encoding="utf-8"
        )
        cls.routes = (ROOT / "app" / "routes.py").read_text(encoding="utf-8")
        cls.docs = (ROOT / "docs" / "API_POWER_BI.md").read_text(encoding="utf-8")

    def test_registra_recursos_somente_get(self):
        for recurso in (
            "ocorrencias", "observacoes-comportamentais",
            "observacoes-comportamentais-itens",
            "auditorias-padrao", "ifs",
        ):
            self.assertIn(f'/api/bi/v1/{recurso}', self.view)
        self.assertNotIn('methods=["POST"]', self.view)
        self.assertIn("register_api_bi_routes(main_routes)", self.routes)

    def test_itens_observacao_expoem_estratificacao_para_o_bi(self):
        inicio = self.view.index(
            '@blueprint.route("/api/bi/v1/observacoes-comportamentais-itens")'
        )
        fim = self.view.index(
            '@blueprint.route("/api/bi/v1/auditorias-padrao")', inicio
        )
        endpoint = self.view[inicio:fim]
        for campo in (
            "registro_id", "categoria_codigo", "categoria_nome",
            "item_codigo", "item_descricao", "descricao_estratificacao",
            "fr.quantidade", "pessoas_observadas",
        ):
            self.assertIn(campo, endpoint)
        self.assertIn("fr.quantidade > 0", endpoint)
        self.assertIn("oc_fluig_respostas", endpoint)

    def test_exige_credencial_tecnica_sem_segredo_no_codigo(self):
        self.assertIn('os.getenv("POWER_BI_API_KEY")', self.view)
        self.assertIn('os.getenv("POWER_BI_API_USER")', self.view)
        self.assertIn("hmac.compare_digest", self.view)
        self.assertIn("basic ", self.view.lower())
        self.assertNotIn("POWER_BI_API_KEY =", self.view)

    def test_paginacao_e_filtros_tem_limites(self):
        self.assertIn("TAMANHO_PAGINA_MAXIMO = 2000", self.view)
        for filtro in (
            "data_inicio", "data_fim", "centro_custos", "atualizado_apos",
            "pagina", "tamanho_pagina",
        ):
            self.assertIn(filtro, self.view)
        self.assertIn("LIMIT %s OFFSET %s", self.view)

    def test_ifs_unifica_as_duas_origens(self):
        self.assertIn("'IFS Tradimaq' origem_ifs", self.view)
        self.assertIn("'IFS do Cliente'", self.view)
        self.assertIn("UNION ALL", self.view)
        for campo in ("nota", "potencial_a", "potencial_b", "potencial_c"):
            self.assertIn(campo, self.view)

    def test_documentacao_nao_inclui_segredo(self):
        self.assertIn("POWER_BI_API_KEY", self.docs)
        self.assertIn("Web.Contents", self.docs)
        self.assertIn("Não salve o segredo", self.docs)

    def test_serializa_time_do_mysql_como_horario(self):
        self.assertIn("isinstance(valor, timedelta)", self.view)
        self.assertIn("valor.total_seconds()", self.view)
        self.assertIn('f"{sinal}{horas:02d}:{minutos:02d}:{segundos:02d}"', self.view)


if __name__ == "__main__":
    unittest.main()
