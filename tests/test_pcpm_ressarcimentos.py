import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PcpmRessarcimentosStructureTests(unittest.TestCase):
    def setUp(self):
        self.view = (ROOT / "app" / "views" / "pcpm_ressarcimentos.py").read_text(encoding="utf-8")
        self.usuarios = (ROOT / "app" / "views" / "usuarios.py").read_text(encoding="utf-8")
        self.auth = (ROOT / "app" / "views" / "autenticacao.py").read_text(encoding="utf-8")
        self.sidebar = (ROOT / "app" / "templates" / "components" / "sidebar.html").read_text(encoding="utf-8")
        self.migration = (ROOT / "docs" / "criar_modulo_pcpm_ressarcimentos.sql").read_text(encoding="utf-8")

    def test_templates_compile(self):
        from app import create_app
        app = create_app()
        for template in ("pcpm_ressarcimentos.html", "novo_pcpm_ressarcimento.html", "pcpm_ressarcimento_detalhe.html"):
            app.jinja_env.get_template(template)

    def test_permission_is_exclusive_and_nested_under_pcpm(self):
        self.assertGreaterEqual(self.view.count('@module_required("acesso_pcpm_ressarcimentos")'), 6)
        self.assertGreaterEqual(self.view.count('@module_required("acesso_pcpm")'), 6)
        self.assertIn("session['acesso_pcpm_ressarcimentos']", self.auth)
        self.assertIn("acesso_pcpm_ressarcimentos", self.usuarios)
        self.assertIn("session.get('acesso_pcpm_ressarcimentos') or is_admin", self.sidebar)

    def test_cost_center_scope_is_enforced_server_side(self):
        self.assertIn('AND r.centro_custos_id = %s', self.view)
        self.assertIn('AND e.ativo = 1 AND e.centro_custo_id = %s', self.view)
        self.assertIn('AND centro_custos_id = %s', self.view)

    def test_billed_process_cannot_be_cancelled(self):
        self.assertIn('processo["status_faturamento"] == "Realizado"', self.view)
        self.assertIn("Um processo com faturamento realizado não pode ser cancelado", self.view)

    def test_listing_follows_standard_filters_sorting_and_pagination(self):
        template = (ROOT / "app" / "templates" / "pcpm_ressarcimentos.html").read_text(encoding="utf-8")
        self.assertIn("ORDENACOES_RESSARCIMENTOS", self.view)
        self.assertIn("LIMIT %s OFFSET %s", self.view)
        self.assertIn("DATE(r.ocorrencia_em) >= %s", self.view)
        self.assertIn('name="data_inicio"', template)
        self.assertIn('name="data_fim"', template)
        self.assertIn("btn btn-laranja", template)
        self.assertIn("btn btn-cinza", template)
        self.assertIn("bi-caret-up-fill", template)
        self.assertIn("pagination pagination-sm", template)

    def test_schema_preserves_budget_versions_and_history(self):
        self.assertIn("CREATE TABLE IF NOT EXISTS pcpm_ressarcimentos_orcamentos", self.migration)
        self.assertIn("UNIQUE KEY uq_ressarcimento_orcamento_versao", self.migration)
        self.assertIn("CREATE TABLE IF NOT EXISTS pcpm_ressarcimentos_anexos", self.migration)
        self.assertIn("CREATE TABLE IF NOT EXISTS pcpm_ressarcimentos_historico", self.migration)
        self.assertIn("dados_anteriores JSON", self.migration)
        self.assertIn("dados_posteriores JSON", self.migration)

    def test_migration_is_reexecutable_and_uses_atomic_number_sequence(self):
        self.assertIn("information_schema.COLUMNS", self.migration)
        self.assertGreaterEqual(self.migration.count("CREATE TABLE IF NOT EXISTS"), 5)
        self.assertIn("CREATE TABLE IF NOT EXISTS pcpm_ressarcimentos_sequencias", self.migration)
        self.assertIn("ON DUPLICATE KEY UPDATE ultimo=LAST_INSERT_ID(ultimo + 1)", self.view)

    def test_completed_or_billed_process_is_read_only(self):
        from app.views.pcpm_ressarcimentos import _garantir_processo_editavel

        _garantir_processo_editavel(
            {"status_processo": "Em andamento", "status_faturamento": "Pendente"}
        )
        for processo in (
            {"status_processo": "Cancelado", "status_faturamento": "Cancelado"},
            {"status_processo": "Concluído", "status_faturamento": "Realizado"},
            {"status_processo": "Em andamento", "status_faturamento": "Realizado"},
        ):
            with self.subTest(processo=processo):
                with self.assertRaises(ValueError):
                    _garantir_processo_editavel(processo)

        self.assertGreaterEqual(self.view.count("_garantir_processo_editavel(processo)"), 6)

    def test_completed_process_hides_all_mutation_controls(self):
        template = (ROOT / "app" / "templates" / "pcpm_ressarcimento_detalhe.html").read_text(encoding="utf-8")
        self.assertIn("{% set processo_editavel =", template)
        self.assertGreaterEqual(template.count("processo_editavel"), 8)

    def test_detail_uses_six_step_navigable_workflow_with_history(self):
        template = (ROOT / "app" / "templates" / "pcpm_ressarcimento_detalhe.html").read_text(encoding="utf-8")
        self.assertIn('class="ress-workflow', template)
        self.assertIn("data-etapa-atual", template)
        self.assertEqual(template.count('class="ress-step-panel"'), 6)
        for titulo in ("Ocorrência", "Cliente", "Orçamento", "Documentação", "Faturamento", "Histórico"):
            self.assertIn(titulo, template)
        self.assertIn("abrirEtapaRessarcimento", template)
        self.assertIn("#etapa-", template)
        self.assertNotIn('Faturamento: {{ processo.status_faturamento }}', template)

    def test_internal_database_errors_are_not_exposed_to_the_user(self):
        self.assertIn("current_app.logger.exception", self.view)
        self.assertNotIn('flash(f"Erro ao cadastrar o ressarcimento: {exc}"', self.view)
        self.assertNotIn('flash(f"Erro ao atualizar a ocorrência: {exc}"', self.view)

    def test_occurrence_can_be_edited_with_audit_trail(self):
        template = (ROOT / "app" / "templates" / "pcpm_ressarcimento_detalhe.html").read_text(encoding="utf-8")
        self.assertIn("atualizar_ocorrencia_pcpm_ressarcimento", self.view)
        self.assertIn('"Atualização da ocorrência"', self.view)
        self.assertIn("dados da avaria atualizados", self.view.lower())
        self.assertIn("modalEditarOcorrencia", template)
        self.assertIn('name="fotos_avaria"', template)
        self.assertIn('name="checklist_movimentacao"', template)

    def test_customer_and_approver_stage_is_validated_and_audited(self):
        template = (ROOT / "app" / "templates" / "pcpm_ressarcimento_detalhe.html").read_text(encoding="utf-8")
        pdf_util = (ROOT / "app" / "utils" / "pcpm_ressarcimentos_pdf.py").read_text(encoding="utf-8")
        self.assertIn("atualizar_cliente_pcpm_ressarcimento", self.view)
        self.assertIn("PADRAO_EMAIL", self.view)
        self.assertIn("_normalizar_telefone", self.view)
        self.assertIn("GREATEST(etapa_atual, 2)", self.view)
        self.assertIn('id="modalDadosCliente"', template)
        self.assertIn("modal-header modal-header-trackplan", template)
        self.assertIn("modal-dialog-centered", template)
        self.assertIn('name="empresa_cliente_id"', template)
        self.assertIn('name="cliente_nome"', template)
        self.assertIn("cliente_nome=%s", self.view)
        self.assertIn("Nome do cliente", pdf_util)
        self.assertIn("COLUMN_NAME = 'cliente_nome'", self.migration)
        self.assertIn('name="aprovador_email"', template)
        self.assertIn('name="aprovador_telefone"', template)

    def test_budget_stage_preserves_versions_and_validates_approval(self):
        template = (ROOT / "app" / "templates" / "pcpm_ressarcimento_detalhe.html").read_text(encoding="utf-8")
        self.assertIn("adicionar_orcamento_pcpm_ressarcimento", self.view)
        self.assertIn("atualizar_status_orcamento_pcpm_ressarcimento", self.view)
        self.assertIn("COALESCE(MAX(versao), 0) + 1", self.view)
        self.assertIn("SET vigente=0", self.view)
        self.assertIn("Anexe o e-mail de aprovação do cliente", self.view)
        self.assertIn('id="modalNovoOrcamento"', template)
        self.assertIn('name="arquivo_orcamento"', template)
        self.assertIn('name="arquivo_aprovacao"', template)

    def test_supporting_documents_are_audited_and_logically_removed(self):
        template = (ROOT / "app" / "templates" / "pcpm_ressarcimento_detalhe.html").read_text(encoding="utf-8")
        self.assertIn("adicionar_documentos_pcpm_ressarcimento", self.view)
        self.assertIn("remover_documento_pcpm_ressarcimento", self.view)
        self.assertIn("categoria='documentacao' AND ativo=1", self.view)
        self.assertIn("SET ativo=0", self.view)
        self.assertIn('id="modalDocumentacao"', template)
        self.assertIn('name="documentos"', template)
        self.assertIn("Documentação comprobatória", template)

    def test_book_pdf_requires_approved_budget_and_documents(self):
        template = (ROOT / "app" / "templates" / "pcpm_ressarcimento_detalhe.html").read_text(encoding="utf-8")
        pdf_util = (ROOT / "app" / "utils" / "pcpm_ressarcimentos_pdf.py").read_text(encoding="utf-8")
        self.assertIn("gerar_book_pcpm_ressarcimento", self.view)
        self.assertIn("orçamento vigente aprovado", self.view)
        self.assertIn("documento comprobatório", self.view)
        self.assertIn("gerar_book_ressarcimento", pdf_util)
        self.assertIn("PdfWriter", pdf_util)
        self.assertIn("pode_gerar_book", template)
        self.assertIn("Geração do book", self.view)

    def test_billing_concludes_and_locks_the_process(self):
        template = (ROOT / "app" / "templates" / "pcpm_ressarcimento_detalhe.html").read_text(encoding="utf-8")
        self.assertIn("atualizar_faturamento_pcpm_ressarcimento", self.view)
        self.assertIn("O faturamento já foi realizado e não pode ser revertido", self.view)
        self.assertIn('status_processo = "Concluído"', self.view)
        self.assertIn("A data do faturamento não pode ser futura", self.view)
        self.assertIn('id="modalFaturamento"', template)
        self.assertIn('name="status_faturamento"', template)
        self.assertIn('name="data_faturamento"', template)


if __name__ == "__main__":
    unittest.main()
