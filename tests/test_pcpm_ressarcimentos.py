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
        self.assertIn("CREATE TABLE pcpm_ressarcimentos_orcamentos", self.migration)
        self.assertIn("UNIQUE KEY uq_ressarcimento_orcamento_versao", self.migration)
        self.assertIn("CREATE TABLE pcpm_ressarcimentos_anexos", self.migration)
        self.assertIn("CREATE TABLE pcpm_ressarcimentos_historico", self.migration)
        self.assertIn("dados_anteriores JSON", self.migration)
        self.assertIn("dados_posteriores JSON", self.migration)

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
        self.assertIn("atualizar_cliente_pcpm_ressarcimento", self.view)
        self.assertIn("PADRAO_EMAIL", self.view)
        self.assertIn("_normalizar_telefone", self.view)
        self.assertIn("GREATEST(etapa_atual, 2)", self.view)
        self.assertIn('id="modalDadosCliente"', template)
        self.assertIn('name="empresa_cliente_id"', template)
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


if __name__ == "__main__":
    unittest.main()
