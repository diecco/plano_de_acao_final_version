import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RelatosOcorrenciasModuleTest(unittest.TestCase):
    def test_probability_and_risk_match_existing_matrix(self):
        from app.views.relatos_ocorrencias import (
            _calculate_probability,
            _calculate_risk,
        )

        self.assertEqual(_calculate_probability("baixa", "baixa", "media"), "baixa")
        self.assertEqual(_calculate_probability("alta", "media", "alta"), "alta")
        self.assertEqual(_calculate_risk("A", "baixa"), "medio")
        self.assertEqual(_calculate_risk("B", "alta"), "alto")
        self.assertEqual(_calculate_risk("C", "media"), "medio")

    def test_templates_compile(self):
        from app import create_app

        app = create_app()
        for template in (
            "relatos_ocorrencias.html",
            "importar_relatos_ocorrencias.html",
            "detalhe_relato_ocorrencia.html",
        ):
            app.jinja_env.get_template(template)

    def test_module_uses_ssma_permission_and_cost_center_scope(self):
        source = (ROOT / "app" / "views" / "relatos_ocorrencias.py").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(source.count('@module_required("acesso_ssma")'), 3)
        self.assertIn('session.get("centro_custos_id")', source)
        self.assertIn('{"administrador", "avancado"}', source)
        self.assertIn('session.get("gestor_ssma")', source)

    def test_sidebar_exposes_read_only_module(self):
        sidebar = (ROOT / "app" / "templates" / "components" / "sidebar.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("main.relatos_ocorrencias", sidebar)
        self.assertIn("Relatos de Ocorrências", sidebar)

    def test_listing_prioritizes_occurrence_description(self):
        template = (ROOT / "app" / "templates" / "relatos_ocorrencias.html").read_text(
            encoding="utf-8"
        )
        headers = [
            '>Solicitação {{', '>Data {{', '>Tipo {{',
            "<th>Responsável pelo registro",
            "<th>Descrição da ocorrência", "<th>Classificação",
            '>Condição/Comportamento', '<th class="text-center">Potencial',
            '>Situação {{', '<th class="text-center">Ações',
        ]
        positions = [template.index(header) for header in headers]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("<th>Local", template)
        self.assertNotIn("<th>Requisitante", template)

    def test_listing_exposes_and_searches_record_owner(self):
        template = (ROOT / "app" / "templates" / "relatos_ocorrencias.html").read_text(
            encoding="utf-8"
        )
        source = (ROOT / "app" / "views" / "relatos_ocorrencias.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("Responsável pelo registro", template)
        self.assertIn("item.responsavel_registro", template)
        self.assertIn("r.responsavel_registro = %s", source)
        self.assertIn('id="responsavelResultados"', template)
        self.assertIn('id="responsaveis-data"', template)

    def test_listing_filters_pending_classification_and_uses_minimal_actions(self):
        template = (ROOT / "app" / "templates" / "relatos_ocorrencias.html").read_text(
            encoding="utf-8"
        )
        source = (ROOT / "app" / "views" / "relatos_ocorrencias.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('name="potencial"', template)
        self.assertIn("Pendentes de classificação", template)
        self.assertIn("btn-acao-icon abrir-classificacao", template)
        self.assertIn('filters["potencial"] == "pendente"', source)
        self.assertIn("NOT EXISTS (SELECT 1 FROM relatos_ocorrencias_classificacoes", source)

    def test_migration_keeps_import_and_classification_separate(self):
        migration = (ROOT / "docs" / "criar_importacao_relatos_ocorrencias.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("relatos_ocorrencias_importacoes", migration)
        self.assertIn("relatos_ocorrencias_envolvidos", migration)
        self.assertIn("relatos_ocorrencias_importacao_erros", migration)
        self.assertNotIn("potencial_severidade", migration)

        classification_migration = (
            ROOT / "docs" / "criar_classificacao_relatos_ocorrencias.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("relatos_ocorrencias_classificacoes", classification_migration)
        self.assertIn("relatos_ocorrencias_classificacoes_historico", classification_migration)

    def test_classification_uses_modal_and_preserves_history(self):
        template = (ROOT / "app" / "templates" / "relatos_ocorrencias.html").read_text(
            encoding="utf-8"
        )
        source = (ROOT / "app" / "views" / "relatos_ocorrencias.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('id="modalClassificacao"', template)
        self.assertIn("modal-xl", template)
        self.assertIn("Classificar potencial de severidade", template)
        self.assertIn("#modalClassificacao .modal-title", template)
        self.assertIn("background: var(--cor-laranja", template)
        self.assertIn("text-align: left", template)
        self.assertIn("modal-dialog-centered", template)
        self.assertIn("relatos_ocorrencias_classificacoes_historico", source)
        self.assertIn("justificativa", source)


if __name__ == "__main__":
    unittest.main()
