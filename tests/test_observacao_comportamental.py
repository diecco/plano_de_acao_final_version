import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ObservacaoComportamentalTests(unittest.TestCase):
    def test_valid_date_is_parsed_when_saving_observation(self):
        from flask import session

        from app import create_app
        from app.views.observacao_comportamental import _carregar_formulario

        class CursorStub:
            def execute(self, query, params=None):
                self.query = query

            def fetchone(self):
                return {"id": 1}

            def fetchall(self):
                return []

        app = create_app()
        dados_formulario = {
            "data_observacao": "2026-10-03",
            "hora_observacao": "12:00",
            "local_observado": "Oficina",
            "setor_observado": "Manutenção",
            "area": "Operação",
            "pessoas_observadas": "1",
        }

        with app.test_request_context(method="POST", data=dados_formulario):
            session["centro_custos_id"] = 1
            dados = _carregar_formulario(CursorStub())

        self.assertEqual(dados["data_observacao"], "2026-10-03")
        self.assertEqual(dados["status"], "concluida")

    def test_new_observation_redirects_to_listing_after_save(self):
        source = (
            ROOT / "app" / "views" / "observacao_comportamental.py"
        ).read_text(encoding="utf-8")
        trecho_nova = source.split(
            'def nova_observacao_comportamental():', 1
        )[1].split(
            '@blueprint.route("/observacoes_comportamentais/<int:registro_id>")', 1
        )[0]

        self.assertIn(
            'return redirect(url_for("main.observacoes_comportamentais"))',
            trecho_nova,
        )
        self.assertNotIn(
            'return redirect(url_for("main.detalhar_observacao_comportamental"',
            trecho_nova,
        )

    def test_templates_compile(self):
        from app import create_app

        app = create_app()
        for template in (
            "observacoes_comportamentais.html",
            "form_observacao_comportamental.html",
            "detalhe_observacao_comportamental.html",
        ):
            app.jinja_env.get_template(template)

    def test_module_has_exclusive_permission_and_cost_center_scope(self):
        source = (ROOT / "app" / "views" / "observacao_comportamental.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('@module_required("acesso_observacao_comportamental")', source)
        self.assertIn('session.get("centro_custos_id")', source)
        self.assertIn('session.get("perfil") == "administrador"', source)

    def test_form_uses_markings_instead_of_deviation_total(self):
        template = (
            ROOT / "app" / "templates" / "form_observacao_comportamental.html"
        ).read_text(encoding="utf-8")
        listing = (
            ROOT / "app" / "templates" / "observacoes_comportamentais.html"
        ).read_text(encoding="utf-8")
        self.assertIn("Comportamentos observados", template)
        self.assertIn("Marcações", listing)
        self.assertNotIn("Total de desvios", template + listing)

    def test_listing_matches_hs_filter_sort_and_pagination_pattern(self):
        template = (
            ROOT / "app" / "templates" / "observacoes_comportamentais.html"
        ).read_text(encoding="utf-8")
        source = (
            ROOT / "app" / "views" / "observacao_comportamental.py"
        ).read_text(encoding="utf-8")

        self.assertIn('list="listaObservadoresOc"', template)
        self.assertIn("Digite o nome ou a matrícula", template)
        self.assertIn("bi-caret-up-fill", template)
        self.assertIn("bi-caret-down-fill", template)
        self.assertIn('class="pagination pagination-sm mb-0"', template)
        self.assertNotIn('name="status"', template)
        self.assertNotIn(">Nova<", template)
        self.assertIn('request.args.get("observador_id", type=int)', source)
        self.assertIn('"marcacoes": "total_marcacoes"', source)

    def test_listing_has_view_edit_and_logical_delete_actions(self):
        template = (
            ROOT / "app" / "templates" / "observacoes_comportamentais.html"
        ).read_text(encoding="utf-8")
        source = (
            ROOT / "app" / "views" / "observacao_comportamental.py"
        ).read_text(encoding="utf-8")
        migration = (
            ROOT / "docs" / "criar_modulo_observacao_comportamental.sql"
        ).read_text(encoding="utf-8")

        self.assertIn('title="Ver detalhes"', template)
        self.assertIn('title="Editar"', template)
        self.assertIn('title="Excluir"', template)
        self.assertIn("main.excluir_observacao_comportamental", template)
        self.assertIn('id="modalExcluirOc"', template)
        self.assertIn('id="formExcluirOc"', template)
        self.assertIn("seus dados e histórico permanecerão preservados", template)
        self.assertNotIn("return confirm(", template)
        self.assertIn("r.excluido_em IS NULL", source)
        self.assertIn("SET excluido_em = NOW(), excluido_por = %s", source)
        self.assertIn('"excluida"', source)
        self.assertIn("excluido_em DATETIME NULL", migration)
        self.assertIn("excluido_por INT NULL", migration)

    def test_listing_expands_details_like_hs_without_n_plus_one_queries(self):
        template = (
            ROOT / "app" / "templates" / "observacoes_comportamentais.html"
        ).read_text(encoding="utf-8")
        source = (
            ROOT / "app" / "views" / "observacao_comportamental.py"
        ).read_text(encoding="utf-8")

        self.assertIn('data-bs-target="#detalhes-oc-', template)
        self.assertIn('class="collapse detalhe-oc-row"', template)
        self.assertIn('data-bs-parent="#tabelaObservacoesOc"', template)
        self.assertIn("Identificação", template)
        self.assertIn("Realização", template)
        self.assertIn("Comportamentos registrados", template)
        self.assertIn("Abordagem e observações", template)
        self.assertIn("Abrir registro completo", template)
        self.assertIn("marcacoes_por_registro.get(registro.id, [])", template)
        self.assertIn("WHERE resp.registro_id IN ({placeholders})", source)
        self.assertIn("marcacoes_por_registro=marcacoes_por_registro", source)

    def test_registration_form_uses_inherited_scope_and_guided_items(self):
        template = (
            ROOT / "app" / "templates" / "form_observacao_comportamental.html"
        ).read_text(encoding="utf-8")
        source = (
            ROOT / "app" / "views" / "observacao_comportamental.py"
        ).read_text(encoding="utf-8")

        self.assertIn("Registrar Observação Comportamental", template)
        self.assertIn("Centro de custos não vinculado", template)
        self.assertIn('name="setor_observado"', template)
        self.assertIn("{% for setor in setores %}", template)
        self.assertIn("item.ajuda", template)
        self.assertIn("position:absolute; right:3.5rem", template)
        self.assertIn("background-color:#f36c21", template)
        self.assertIn('class="btn btn-laranja" type="submit">Salvar</button>', template)
        self.assertNotIn("Salvar rascunho", template)
        self.assertNotIn("Concluir</button>", template)
        self.assertIn("EXPLICACOES_ITENS", source)
        self.assertIn("FROM setores", source)
        self.assertIn('session.get("centro_custos_id")', source)
        self.assertIn('"status": "concluida"', source)

    def test_schema_contains_original_six_categories_and_history(self):
        migration = (
            ROOT / "docs" / "criar_modulo_observacao_comportamental.sql"
        ).read_text(encoding="utf-8")
        for category in (
            "Reação das pessoas",
            "Posição das pessoas",
            "Parte do corpo exposta",
            "Ferramentas e equipamentos",
            "Procedimentos",
            "Ordem, limpeza e organização",
        ):
            self.assertIn(category, migration)
        self.assertIn("CREATE TABLE IF NOT EXISTS oc_historico", migration)
        self.assertIn("acesso_observacao_comportamental", migration)


if __name__ == "__main__":
    unittest.main()
