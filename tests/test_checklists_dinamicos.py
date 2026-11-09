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

    def test_sidebar_keeps_builder_under_administration(self):
        sidebar = (
            ROOT / "app" / "templates" / "components" / "sidebar.html"
        ).read_text(encoding="utf-8")
        self.assertIn("endpoints_admin_checklists", sidebar)
        self.assertIn("'main.editar_checklist_dinamico'", sidebar)
        self.assertIn("checklist_em_uso and checklist_aberto_id == checklist.id", sidebar)

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
        self.assertIn(">Salvar</button>", template)
        self.assertIn("btn btn-cinza", template)
        self.assertIn("negative-details", template)

    def test_completed_execution_returns_to_checklist_listing(self):
        source = (
            ROOT / "app" / "views" / "checklists_dinamicos.py"
        ).read_text(encoding="utf-8")
        success_flow = source.split(
            'flash("Checklist concluído com sucesso.", "success")', 1
        )[1].split("@blueprint.get", 1)[0]
        self.assertIn('"main.abrir_checklist_dinamico"', success_flow)
        self.assertIn("checklist_id=checklist_id", success_flow)
        self.assertNotIn('"main.visualizar_execucao_checklist"', success_flow)

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

    def test_listing_has_standard_server_side_sorting_controls(self):
        template = (
            ROOT / "app" / "templates" / "checklist_dinamico_esboco.html"
        ).read_text(encoding="utf-8")
        source = (
            ROOT / "app" / "views" / "checklists_dinamicos.py"
        ).read_text(encoding="utf-8")
        for field in ("id", "data", "responsavel", "centro"):
            self.assertIn(f"'{field}'", template)
        self.assertIn("bi-caret-up-fill", template)
        self.assertIn("bi-caret-down-fill", template)
        self.assertIn('"responsavel": "u.nome"', source)
        self.assertIn('"centro": "cc.codigo"', source)
        self.assertIn("ORDER BY {coluna_ordenacao} {direcao_ordenacao}", source)

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

    def test_nfc_tag_field_uses_scoped_catalog_and_keeps_a_snapshot(self):
        from werkzeug.datastructures import MultiDict
        from app.views.checklists_dinamicos import _validar_respostas, validar_estrutura

        definition = [{
            "title": "Identificação", "layout": "header",
            "questions": [{
                "text": "Ponto verificado", "type": "nfc_tag", "required": True,
                "negative_comment": False, "negative_evidence": False, "options": [],
            }],
        }]
        clean = validar_estrutura(json.dumps(definition))
        answers, errors = _validar_respostas(
            clean, MultiDict([
                ("q_0_0", "12"), ("q_0_0_nfc_method", "physical"),
                ("q_0_0_nfc_channel", "usb"),
                ("q_0_0_nfc_read_at", "2026-11-07T18:30:00.000Z"),
            ]),
            etiquetas_nfc=[{
                "id": 12, "numero": "NFC-001", "descricao": "Extintor da recepção"
            }],
        )
        self.assertEqual(errors, [])
        self.assertEqual(answers["q_0_0"]["value"], {
            "id": 12, "number": "NFC-001", "description": "Extintor da recepção",
            "read_method": "physical", "read_at": answers["q_0_0"]["value"]["read_at"],
            "read_channel": "usb",
        })
        self.assertRegex(answers["q_0_0"]["value"]["read_at"], r"^\d{4}-\d{2}-\d{2}T")

        source = (ROOT / "app" / "views" / "checklists_dinamicos.py").read_text(encoding="utf-8")
        builder = (ROOT / "app" / "static" / "js" / "checklist-builder.js").read_text(encoding="utf-8")
        execution = (ROOT / "app" / "templates" / "checklist_dinamico_aplicar.html").read_text(encoding="utf-8")
        self.assertIn("Etiqueta NFC", builder)
        self.assertIn("nfc_etiquetas_centros", source)
        self.assertIn("e.abrangencia = 'global'", source)
        self.assertNotIn("Selecione a etiqueta NFC", execution)
        self.assertIn("data-nfc-read", execution)
        self.assertIn("data-nfc-usb-input", execution)
        self.assertIn("Bloquear os itens e etapas seguintes", builder)
        self.assertIn("exclusivamente pela leitura física", builder)
        runner = (ROOT / "app" / "static" / "js" / "checklist-run.js").read_text(encoding="utf-8")
        self.assertIn("compareDocumentPosition", runner)
        self.assertIn("DOCUMENT_POSITION_FOLLOWING", runner)

    def test_nfc_signature_validates_active_scoped_user_and_keeps_identity_snapshot(self):
        from werkzeug.datastructures import MultiDict
        from app.views.checklists_dinamicos import _validar_respostas, validar_estrutura

        definition = [{
            "title": "Assinaturas", "layout": "header",
            "questions": [{
                "text": "Assinatura do responsável", "type": "nfc_signature",
                "required": True, "negative_comment": False,
                "negative_evidence": False, "options": [],
            }],
        }]
        clean = validar_estrutura(json.dumps(definition))
        form = MultiDict([
            ("q_0_0_nfc_signatures", json.dumps([
                {"user_id": 15, "uid": "0001234567", "channel": "usb"},
            ])),
        ])
        signers = [{
            "id": 15, "nome": "Maria Auditora", "matricula": "0015",
            "uid_rfid": "0001234567",
        }]
        answers, errors = _validar_respostas(clean, form, assinantes_nfc=signers)
        self.assertEqual(errors, [])
        self.assertEqual(answers["q_0_0"]["value"][0]["id"], 15)
        self.assertEqual(answers["q_0_0"]["value"][0]["name"], "Maria Auditora")
        self.assertEqual(answers["q_0_0"]["value"][0]["registration"], "0015")
        self.assertNotIn("uid_rfid", answers["q_0_0"]["value"][0])

        forged = MultiDict([
            ("q_0_0_nfc_signatures", json.dumps([
                {"user_id": 99, "uid": "0001234567", "channel": "usb"},
            ])),
        ])
        answers, errors = _validar_respostas(clean, forged, assinantes_nfc=signers)
        self.assertTrue(errors)
        self.assertEqual(answers["q_0_0"]["value"], [])

        builder = (ROOT / "app" / "static" / "js" / "checklist-builder.js").read_text(encoding="utf-8")
        execution = (ROOT / "app" / "templates" / "checklist_dinamico_aplicar.html").read_text(encoding="utf-8")
        runner = (ROOT / "app" / "static" / "js" / "checklist-run.js").read_text(encoding="utf-8")
        source = (ROOT / "app" / "views" / "checklists_dinamicos.py").read_text(encoding="utf-8")
        self.assertIn("Assinatura por crachá NFC", builder)
        self.assertIn("data-nfc-signature", execution)
        self.assertIn("data-signature-url", execution)
        self.assertIn("Crachá NFC não localizado", runner)
        self.assertIn("def validar_assinatura_nfc", source)
        self.assertIn("uid_rfid", source)

    def test_nfc_signature_can_require_every_person_selected_in_linked_field(self):
        from werkzeug.datastructures import MultiDict
        from app.views.checklists_dinamicos import _ler_estrutura, _validar_respostas, validar_estrutura

        definition = [{"title": "Equipe", "layout": "header", "questions": [
            {"ref": "participants", "text": "Participantes", "type": "people",
             "required": True, "negative_comment": False, "negative_evidence": False,
             "options": [], "minimum_selections": 1, "maximum_selections": 10},
            {"ref": "signatures", "text": "Assinaturas", "type": "nfc_signature",
             "signature_source_ref": "participants", "required": True,
             "negative_comment": False, "negative_evidence": False, "options": []},
        ]}]
        clean = _ler_estrutura(validar_estrutura(json.dumps(definition)))
        people = [
            {"id": 15, "nome": "Maria", "matricula": "0015"},
            {"id": 16, "nome": "João", "matricula": "0016"},
        ]
        signers = [
            {**people[0], "uid_rfid": "UID15"},
            {**people[1], "uid_rfid": "UID16"},
        ]
        signatures = [
            {"user_id": 15, "uid": "UID15", "channel": "usb"},
            {"user_id": 16, "uid": "UID16", "channel": "web_nfc"},
        ]
        form = MultiDict([
            ("q_0_0", "15"), ("q_0_0", "16"),
            ("q_0_1_nfc_signatures", json.dumps(signatures)),
        ])
        answers, errors = _validar_respostas(clean, form, pessoas=people, assinantes_nfc=signers)
        self.assertEqual(errors, [])
        self.assertEqual({item["id"] for item in answers["q_0_1"]["value"]}, {15, 16})

        incomplete = MultiDict([
            ("q_0_0", "15"), ("q_0_0", "16"),
            ("q_0_1_nfc_signatures", json.dumps(signatures[:1])),
        ])
        _, errors = _validar_respostas(clean, incomplete, pessoas=people, assinantes_nfc=signers)
        self.assertTrue(any("todas as assinaturas" in error.lower() for error in errors))

    def test_field_specific_validation_rules_are_preserved(self):
        from app.views.checklists_dinamicos import validar_estrutura

        definition = [{"title": "Dados", "questions": [
            {"text": "Resumo", "type": "text", "required": False,
             "negative_comment": False, "negative_evidence": False, "options": [],
             "max_length": 80},
            {"text": "Horário", "type": "time", "required": False,
             "negative_comment": False, "negative_evidence": False, "options": [],
             "minimum_value": "07:00", "maximum_value": "18:00"},
            {"text": "Equipe", "type": "people", "required": False,
             "negative_comment": False, "negative_evidence": False, "options": [],
             "minimum_selections": 1, "maximum_selections": 4},
        ]}]
        clean = validar_estrutura(json.dumps(definition))[0]["questions"]
        self.assertEqual(clean[0]["max_length"], 80)
        self.assertEqual(clean[1]["minimum_value"], "07:00")
        self.assertEqual(clean[2]["maximum_selections"], 4)

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
        self.assertIn("Cabeçalho / grade de campos", builder)
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
        css = (ROOT / "app" / "static" / "css" / "checklist-run.css").read_text(encoding="utf-8")
        self.assertIn(".verification-result-column { width: 14%; }", css)
        self.assertIn(".verification-deviation-column { width: 42%; }", css)

    def test_nfc_checkpoint_keeps_conformity_items_in_standard_table(self):
        template = (ROOT / "app" / "templates" / "checklist_dinamico_aplicar.html").read_text(encoding="utf-8")
        self.assertIn("render_nfc_checkpoint", template)
        self.assertIn("conformity_items|length + nfc_items|length", template)
        self.assertIn("{% if item.type == 'conformity' %}", template)

    def test_builder_offers_all_section_layouts(self):
        from app.views.checklists_dinamicos import LAYOUTS_SECAO, validar_estrutura

        self.assertEqual(set(LAYOUTS_SECAO), {
            "header", "verification", "narrative", "grouped", "repeatable", "evidence",
        })
        builder = (ROOT / "app" / "static" / "js" / "checklist-builder.js").read_text(encoding="utf-8")
        for label in (
            "Cabeçalho / grade de campos", "Itens de verificação", "Texto / conclusão",
            "Verificação agrupada", "Lista repetível", "Evidências / galeria",
        ):
            self.assertIn(label, builder)

        definition = [{
            "title": "Conclusão", "layout": "narrative",
            "questions": [{"text": "Parecer", "type": "textarea", "required": True,
                           "negative_comment": False, "negative_evidence": False,
                           "negative_action": False, "options": []}],
        }]
        self.assertEqual(validar_estrutura(json.dumps(definition))[0]["layout"], "narrative")

    def test_repeatable_layout_preserves_multiple_rows(self):
        from werkzeug.datastructures import MultiDict
        from app.views.checklists_dinamicos import _validar_respostas, validar_estrutura

        definition = [{
            "title": "Ocorrências", "layout": "repeatable",
            "questions": [{"text": "Descrição", "type": "text", "required": True,
                           "negative_comment": False, "negative_evidence": False,
                           "negative_action": False, "options": [], "max_length": 255}],
        }]
        clean = validar_estrutura(definition)
        answers, errors = _validar_respostas(
            clean, MultiDict([("q_0_0", "Primeira"), ("q_0_0", "Segunda")])
        )
        self.assertEqual(errors, [])
        self.assertEqual(answers["q_0_0"]["value"], ["Primeira", "Segunda"])

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

    def test_runtime_structure_enrichment_does_not_mutate_saved_definition(self):
        from app.views.checklists_dinamicos import _ler_estrutura

        original = [{"title": "Dados", "questions": [{
            "text": "Resumo", "type": "text", "required": False,
        }]}]
        runtime = _ler_estrutura(original)
        self.assertNotIn("layout", original[0])
        self.assertNotIn("max_length", original[0]["questions"][0])
        self.assertEqual(runtime[0]["questions"][0]["max_length"], 255)

    def test_oversized_free_text_and_signature_payloads_are_rejected(self):
        from werkzeug.datastructures import MultiDict
        from app.views.checklists_dinamicos import _validar_respostas, validar_estrutura

        definition = [{"title": "Teste", "questions": [
            {"text": "Condição", "type": "conformity", "required": True,
             "negative_comment": True, "negative_evidence": True, "options": []},
            {"text": "Assinatura", "type": "nfc_signature", "required": False,
             "negative_comment": False, "negative_evidence": False, "options": []},
        ]}]
        clean = validar_estrutura(definition)
        signatures = [
            {"user_id": index, "uid": f"UID{index}", "channel": "usb"}
            for index in range(201)
        ]
        form = MultiDict([
            ("q_0_0", "nao_conforme"),
            ("q_0_0_comment", "x" * 3001),
            ("q_0_0_evidence", "x" * 1001),
            ("q_0_1_nfc_signatures", json.dumps(signatures)),
        ])
        _, errors = _validar_respostas(clean, form)
        self.assertTrue(any("comentário" in error for error in errors))
        self.assertTrue(any("evidência" in error for error in errors))
        self.assertTrue(any("limite de assinaturas" in error for error in errors))

    def test_execution_form_prevents_accidental_double_submission(self):
        template = (ROOT / "app" / "templates" / "checklist_dinamico_aplicar.html").read_text(
            encoding="utf-8"
        )
        runner = (ROOT / "app" / "static" / "js" / "checklist-run.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("data-checklist-form", template)
        self.assertIn("form.dataset.submitting", runner)
        self.assertIn("Salvando…", runner)


if __name__ == "__main__":
    unittest.main()
