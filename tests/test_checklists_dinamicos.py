import json
import unittest
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ConfigurableChecklistSketchTests(unittest.TestCase):
    def test_migration_is_additive_and_scoped_by_cost_center(self):
        sql = (ROOT / "docs" / "criar_catalogo_checklists_dinamicos.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("CREATE TABLE IF NOT EXISTS checklist_modelos", sql)
        self.assertIn("CREATE TABLE IF NOT EXISTS checklist_modelos_centros", sql)
        self.assertIn("REFERENCES centros_custos(id)", sql)

    def test_sidebar_contains_dynamic_slots_and_administration_link(self):
        sidebar = (
            ROOT / "app" / "templates" / "components" / "sidebar.html"
        ).read_text(encoding="utf-8")
        self.assertIn("checklists_sidebar_ssma", sidebar)
        self.assertIn("checklists_sidebar_gestao", sidebar)
        self.assertIn("main.checklists_dinamicos", sidebar)
        self.assertIn("main.abrir_checklist_dinamico", sidebar)

    def test_scope_query_accepts_global_or_selected_cost_center(self):
        source = (
            ROOT / "app" / "views" / "checklists_dinamicos.py"
        ).read_text(encoding="utf-8")
        self.assertIn("cm.abrangencia = 'global'", source)
        self.assertIn("checklist_modelos_centros", source)
        self.assertIn("cm.status = 'publicado'", source)
        self.assertIn("cm.exibir_menu = 1", source)

    def test_sidebar_configuration_is_conditional_and_uses_orange_switch(self):
        template = (
            ROOT / "app" / "templates" / "checklists_dinamicos.html"
        ).read_text(encoding="utf-8")
        self.assertNotIn("Primeiro esboço", template)
        self.assertIn('id="blocoSidebar" hidden', template)
        self.assertIn("atualizarSidebar", template)
        self.assertIn("background-color: #f26722", template)

    def test_verification_item_builder_has_server_side_validation(self):
        source = (
            ROOT / "app" / "views" / "checklists_dinamicos.py"
        ).read_text(encoding="utf-8")
        self.assertIn("def validar_estrutura", source)
        self.assertIn("O limite é de 200 itens por checklist", source)
        self.assertIn("negative_comment", source)
        self.assertIn("estrutura_json", source)

        javascript = (
            ROOT / "app" / "static" / "js" / "checklist-builder.js"
        ).read_text(encoding="utf-8")
        editor = (
            ROOT / "app" / "templates" / "checklist_dinamico_editar.html"
        ).read_text(encoding="utf-8")
        self.assertIn("Adicionar seção", editor)
        self.assertIn("Matriz de avaliação", javascript)
        self.assertIn("Exigir descrição do desvio", javascript)

    def test_items_migration_is_reexecutable(self):
        sql = (
            ROOT / "docs" / "adicionar_itens_checklists_dinamicos.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("information_schema.COLUMNS", sql)
        self.assertIn("ADD COLUMN estrutura_json JSON", sql)

    def test_server_accepts_a_valid_definition_and_rejects_empty_sections(self):
        from app.views.checklists_dinamicos import validar_estrutura

        valid = [{
            "title": "Condições do local",
            "questions": [{
                "text": "O local está sinalizado?",
                "type": "conformity",
                "required": True,
                "negative_comment": True,
                "negative_evidence": False,
                "options": [],
            }],
        }]
        clean = validar_estrutura(json.dumps(valid))
        self.assertEqual(clean[0]["questions"][0]["text"], "O local está sinalizado?")

        invalid = [{"title": "Sem itens", "questions": []}]
        with self.assertRaisesRegex(ValueError, "ao menos um item"):
            validar_estrutura(json.dumps(invalid))

    def test_execution_is_stored_with_snapshot_and_server_validation(self):
        source = (
            ROOT / "app" / "views" / "checklists_dinamicos.py"
        ).read_text(encoding="utf-8")
        self.assertIn("def _validar_respostas", source)
        self.assertIn("estrutura_snapshot_json", source)
        self.assertIn("INSERT INTO checklist_execucoes", source)

        migration = (
            ROOT / "docs" / "criar_execucoes_checklists_dinamicos.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS checklist_execucoes", migration)
        self.assertIn("respostas_json JSON NOT NULL", migration)

        template = (
            ROOT / "app" / "templates" / "checklist_dinamico_aplicar.html"
        ).read_text(encoding="utf-8")
        self.assertIn("Concluir checklist", template)
        self.assertIn("negative-details", template)

    def test_listing_uses_the_standard_filter_and_new_record_toolbar(self):
        template = (
            ROOT / "app" / "templates" / "checklist_dinamico_esboco.html"
        ).read_text(encoding="utf-8")
        self.assertIn('name="executor_id"', template)
        self.assertIn('name="data_inicio"', template)
        self.assertIn('name="data_fim"', template)
        self.assertIn('name="periodo"', template)
        self.assertIn('name="mes_referencia"', template)
        self.assertIn('id="executor_busca"', template)
        self.assertIn("autocomplete-list", template)
        self.assertIn("bi-funnel", template)
        self.assertIn("bi-arrow-clockwise", template)
        self.assertIn("bi-plus-circle", template)
        self.assertNotIn("Novo preenchimento", template)
        self.assertIn("col-xl-auto ms-xl-auto", template)

    def test_period_filter_matches_adherence_report_options(self):
        from datetime import date
        from app.views.checklists_dinamicos import _resolver_periodo_listagem

        inicio, fim, referencia = _resolver_periodo_listagem(
            "mes_anterior", hoje=date(2026, 1, 15)
        )
        self.assertEqual(inicio, date(2025, 12, 1))
        self.assertEqual(fim, date(2025, 12, 31))
        self.assertEqual(referencia, "2025-12")
        with self.assertRaisesRegex(ValueError, "mesmo mês"):
            _resolver_periodo_listagem(
                "personalizado", data_inicio="2026-01-31", data_fim="2026-02-01"
            )

    def test_listing_has_period_statistics_without_deviation_metrics(self):
        source = (
            ROOT / "app" / "views" / "checklists_dinamicos.py"
        ).read_text(encoding="utf-8")
        self.assertIn("COUNT(*) AS total_preenchimentos", source)
        self.assertIn("COUNT(DISTINCT ce.executor_id) AS total_responsaveis", source)
        template = (
            ROOT / "app" / "templates" / "checklist_dinamico_esboco.html"
        ).read_text(encoding="utf-8")
        self.assertIn("Preenchimentos", template)
        self.assertIn("Responsáveis", template)
        self.assertIn("Dias com atividade", template)
        self.assertIn("Último preenchimento", template)
        self.assertNotIn("Total de desvios", template)

    def test_published_checklist_can_be_edited_without_changing_history(self):
        source = (
            ROOT / "app" / "views" / "checklists_dinamicos.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("A versão publicada é somente leitura", source)
        self.assertIn("DELETE FROM checklist_modelos_centros", source)
        self.assertIn("Checklist atualizado com sucesso", source)

        listing = (
            ROOT / "app" / "templates" / "checklists_dinamicos.html"
        ).read_text(encoding="utf-8")
        published_branch = listing.split("{% else %}", 1)[1]
        self.assertIn("main.editar_checklist_dinamico", published_branch)
        self.assertIn('title="Editar"', published_branch)

        editor = (
            ROOT / "app" / "templates" / "checklist_dinamico_editar.html"
        ).read_text(encoding="utf-8")
        self.assertIn('name="nome"', editor)
        self.assertIn('name="abrangencia"', editor)
        self.assertIn("Salvar alterações", editor)

    def test_section_reordering_controls_are_visible_in_the_section_header(self):
        javascript = (
            ROOT / "app" / "static" / "js" / "checklist-builder.js"
        ).read_text(encoding="utf-8")
        self.assertIn("checklist-section-summary-actions", javascript)
        self.assertIn("actions(sections, sectionIndex, 'seção')", javascript)
        self.assertIn("event.stopPropagation()", javascript)
        css = (
            ROOT / "app" / "static" / "css" / "checklist-builder.css"
        ).read_text(encoding="utf-8")
        self.assertIn(".checklist-section-summary-actions", css)

    def test_additional_field_types_work_from_builder_to_execution(self):
        from werkzeug.datastructures import MultiDict
        from app.views.checklists_dinamicos import _validar_respostas, validar_estrutura

        kinds = ["time", "text", "textarea", "person", "people", "sector"]
        definition = [{
            "title": "Identificação",
            "questions": [{
                "text": f"Campo {kind}", "type": kind, "required": True,
                "negative_comment": False, "negative_evidence": False, "options": [],
            } for kind in kinds],
        }]
        clean = validar_estrutura(json.dumps(definition))
        form = MultiDict([
            ("q_0_0", "08:30"), ("q_0_1", "Texto curto"),
            ("q_0_2", "Texto longo"), ("q_0_3", "1"),
            ("q_0_4", "1"), ("q_0_4", "2"), ("q_0_5", "7"),
        ])
        people = [
            {"id": 1, "nome": "Pessoa A", "matricula": "001"},
            {"id": 2, "nome": "Pessoa B", "matricula": "002"},
        ]
        answers, errors = _validar_respostas(
            clean, form, pessoas=people, setores=[{"id": 7, "nome": "Operação"}]
        )
        self.assertEqual(errors, [])
        self.assertEqual(answers["q_0_3"]["value"]["name"], "Pessoa A")
        self.assertEqual(len(answers["q_0_4"]["value"]), 2)
        self.assertEqual(answers["q_0_5"]["value"]["name"], "Operação")

        javascript = (ROOT / "app" / "static" / "js" / "checklist-builder.js").read_text(encoding="utf-8")
        for label in ("Hora", "Texto curto", "Texto longo", "Uma pessoa", "Várias pessoas", "Setor / Área"):
            self.assertIn(label, javascript)

    def test_header_layout_is_compact_and_people_use_scoped_autocomplete(self):
        from app.views.checklists_dinamicos import validar_estrutura

        definition = [{
            "title": "Dados Gerais",
            "questions": [{
                "text": "Auditados", "type": "people", "required": True,
                "negative_comment": False, "negative_evidence": False, "options": [],
            }],
        }]
        clean = validar_estrutura(json.dumps(definition))
        self.assertEqual(clean[0]["layout"], "header")
        self.assertEqual(clean[0]["questions"][0]["type"], "people")

        builder = (ROOT / "app" / "static" / "js" / "checklist-builder.js").read_text(encoding="utf-8")
        template = (ROOT / "app" / "templates" / "checklist_dinamico_aplicar.html").read_text(encoding="utf-8")
        runner = (ROOT / "app" / "static" / "js" / "checklist-run.js").read_text(encoding="utf-8")
        self.assertIn("Cabeçalho · campos compactos", builder)
        self.assertIn("checklist-header-card", template)
        self.assertIn("data-person-picker", template)
        self.assertIn("checklist-people-data", template)
        self.assertIn("person-selected", runner)
        source = (ROOT / "app" / "views" / "checklists_dinamicos.py").read_text(encoding="utf-8")
        self.assertIn("cmc.centro_custos_id = u.centro_custos_id", source)
        self.assertIn("AND u.ativo = 1", source)

    def test_conformity_items_use_dropdown_table_layout(self):
        template = (ROOT / "app" / "templates" / "checklist_dinamico_aplicar.html").read_text(encoding="utf-8")
        runner = (ROOT / "app" / "static" / "js" / "checklist-run.js").read_text(encoding="utf-8")
        self.assertIn("checklist-verification-table", template)
        self.assertIn("Desvio / evidência", template)
        self.assertIn("data-result-select", template)
        self.assertIn('select[name="${name}"]', runner)

    def test_execution_does_not_add_a_fixed_general_observations_field(self):
        template = (ROOT / "app" / "templates" / "checklist_dinamico_aplicar.html").read_text(encoding="utf-8")
        self.assertNotIn('name="observacoes"', template)

    def test_negative_items_can_require_a_linked_action(self):
        from app import create_app
        from app.views.checklists_dinamicos import (
            _validar_acoes_checklist,
            validar_estrutura,
        )

        definition = [{
            "title": "Verificação", "layout": "standard",
            "questions": [{
                "text": "A condição está adequada?", "type": "conformity",
                "required": True, "negative_comment": True,
                "negative_evidence": False, "negative_action": True, "options": [],
            }],
        }]
        clean = validar_estrutura(json.dumps(definition))
        self.assertTrue(clean[0]["questions"][0]["negative_action"])

        due = (date.today() + timedelta(days=5)).isoformat()
        app = create_app()
        with app.test_request_context("/", method="POST", data={
            "q_0_0": "nao_conforme",
            "q_0_0_action_description": "Corrigir a proteção do equipamento.",
            "q_0_0_action_responsible": "7",
            "q_0_0_action_due": due,
        }):
            from flask import session
            session["usuario_id"] = 1
            session["acesso_plano_acao"] = 1
            proposals, errors = _validar_acoes_checklist(
                clean, __import__("flask").request.form,
                responsaveis=[{"id": 7, "nome": "Responsável", "matricula": "007"}],
            )
        self.assertEqual(errors, [])
        self.assertEqual(proposals["q_0_0"]["responsible_id"], 7)

        builder = (ROOT / "app" / "static" / "js" / "checklist-builder.js").read_text(encoding="utf-8")
        execution = (ROOT / "app" / "templates" / "checklist_dinamico_aplicar.html").read_text(encoding="utf-8")
        self.assertIn("Gerar ação para resposta negativa", builder)
        self.assertIn("Ação vinculada ao desvio", execution)

    def test_action_link_migration_is_reexecutable_and_auditable(self):
        sql = (ROOT / "docs" / "integrar_checklists_plano_acao.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS checklist_execucao_acoes", sql)
        self.assertIn("UNIQUE KEY uk_checklist_execucao_item_acao", sql)
        source = (ROOT / "app" / "views" / "checklists_dinamicos.py").read_text(encoding="utf-8")
        self.assertIn("INSERT INTO checklist_execucao_acoes", source)
        self.assertIn("INSERT INTO acoes", source)


if __name__ == "__main__":
    unittest.main()
