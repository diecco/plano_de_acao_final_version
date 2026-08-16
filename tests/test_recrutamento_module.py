import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RecrutamentoModuleTests(unittest.TestCase):
    def test_templates_compile(self):
        from app import create_app

        app = create_app()
        for nome in (
            "recrutamento_candidatos.html",
            "novo_candidato_recrutamento.html",
            "recrutamento_candidatura_detalhe.html",
            "recrutamento_minhas_avaliacoes.html",
            "recrutamento_minha_avaliacao_detalhe.html",
        ):
            app.jinja_env.get_template(nome)

    def test_routes_are_registered(self):
        source = (ROOT / "app" / "routes.py").read_text(encoding="utf-8")
        self.assertIn("register_recrutamento_routes", source)

    def test_all_module_routes_require_exclusive_permission(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        self.assertGreaterEqual(
            source.count('@module_required("acesso_recrutamento")'),
            7,
        )
        self.assertNotIn("acesso_gestao_pessoas", source)

    def test_permission_is_available_across_user_flows(self):
        usuarios = (ROOT / "app" / "views" / "usuarios.py").read_text(
            encoding="utf-8"
        )
        autenticacao = (ROOT / "app" / "views" / "autenticacao.py").read_text(
            encoding="utf-8"
        )
        sidebar = (
            ROOT / "app" / "templates" / "components" / "sidebar.html"
        ).read_text(encoding="utf-8")

        self.assertGreaterEqual(usuarios.count("acesso_recrutamento"), 12)
        self.assertIn("session['acesso_recrutamento']", autenticacao)
        self.assertIn(
            "session.get('acesso_recrutamento') or is_admin",
            sidebar,
        )

        for template in (
            "usuarios.html",
            "editar_usuario.html",
            "permissoes_usuario.html",
        ):
            source = (ROOT / "app" / "templates" / template).read_text(
                encoding="utf-8"
            )
            self.assertIn('name="acesso_recrutamento"', source)

    def test_schema_separates_candidate_and_application(self):
        migration = (
            ROOT / "docs" / "criar_modulo_recrutamento.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("recrutamento_candidatos (", migration)
        self.assertIn("UNIQUE (cpf)", migration)
        self.assertIn("recrutamento_candidaturas (", migration)
        self.assertIn("recrutamento_etapas (", migration)
        self.assertIn("recrutamento_pre_admissao (", migration)
        self.assertIn("recrutamento_historico (", migration)

    def test_cpf_validation(self):
        from app.views.recrutamento import cpf_valido

        self.assertTrue(cpf_valido("529.982.247-25"))
        self.assertFalse(cpf_valido("111.111.111-11"))
        self.assertFalse(cpf_valido("123"))

    def test_phone_validation_accepts_mobile_and_landline(self):
        from app.views.recrutamento import telefone_valido

        self.assertTrue(telefone_valido("(31) 99999-1234"))
        self.assertTrue(telefone_valido("(31) 3333-1234"))
        self.assertFalse(telefone_valido("9999-1234"))
        self.assertFalse(telefone_valido("(00) 99999-1234"))

    def test_alternative_phone_is_modeled_and_masked(self):
        view = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        template = (
            ROOT / "app" / "templates" / "novo_candidato_recrutamento.html"
        ).read_text(encoding="utf-8")
        migration = (
            ROOT / "docs" / "adicionar_telefone_alternativo_recrutamento.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("telefone_alternativo", view)
        self.assertIn('name="telefone_alternativo"', template)
        self.assertIn("formatarCpf", template)
        self.assertIn("formatarTelefone", template)
        self.assertIn("telefone_alternativo", migration)

    def test_selection_workflow_has_server_side_rules(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("_etapas_obrigatorias_concluidas", source)
        self.assertIn("_pode_gerenciar_candidatura", source)
        self.assertIn("etapa[\"avaliador_id\"] == session.get(\"usuario_id\")", source)
        self.assertIn("decisao_consolidada", source)
        self.assertIn("recrutamento_pareceres_complementares", source)
        self.assertIn("e.avaliador_id = %s", source)

    def test_evaluator_view_minimizes_personal_data(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        detalhe = (ROOT / "app" / "templates" / "recrutamento_minha_avaliacao_detalhe.html").read_text(encoding="utf-8")
        self.assertIn("candidato_nome", detalhe)
        self.assertIn("telefone", detalhe)
        self.assertIn("cargo_pretendido", detalhe)
        self.assertIn("parecer_rh", detalhe)
        self.assertNotIn("cpf", detalhe.lower())
        self.assertIn("curriculo_minha_avaliacao_recrutamento", source)

    def test_parallel_flow_migration_is_available(self):
        migration = (ROOT / "docs" / "ajustar_fluxo_avaliacoes_recrutamento.sql").read_text(encoding="utf-8")
        self.assertIn("decisao_resultado", migration)
        self.assertIn("recrutamento_pareceres_complementares", migration)

    def test_practical_test_requires_an_explicit_choice(self):
        view = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        template = (
            ROOT / "app" / "templates" / "novo_candidato_recrutamento.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            'request.form.get("exige_teste_pratico") or ""',
            view,
        )
        self.assertIn('value="" disabled', template)
        self.assertNotIn(
            "request.form.get('exige_teste_pratico', 'nao_aplicavel')",
            template,
        )

    def test_assignment_notifies_evaluator_by_email(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("Nova avaliação atribuída a você - TrackPlan", source)
        self.assertIn("mail.send(msg)", source)
        self.assertIn('avaliador.get("email")', source)
        self.assertIn('"main.detalhe_minha_avaliacao_recrutamento"', source)

    def test_assignment_requires_and_displays_deadline(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        manager_template = (
            ROOT / "app" / "templates" / "recrutamento_candidatura_detalhe.html"
        ).read_text(encoding="utf-8")
        evaluator_template = (
            ROOT / "app" / "templates" / "recrutamento_minha_avaliacao_detalhe.html"
        ).read_text(encoding="utf-8")

        self.assertIn('request.form.get("data_prevista")', source)
        self.assertIn("prazo < date.today()", source)
        self.assertIn("SET avaliador_id = %s, data_prevista = %s", source)
        self.assertIn('name="data_prevista"', manager_template)
        self.assertIn("etapa.data_prevista", evaluator_template)

    def test_candidate_reuse_preserves_previous_cycle(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        template = (
            ROOT / "app" / "templates" / "recrutamento_candidatura_detalhe.html"
        ).read_text(encoding="utf-8")
        migration = (
            ROOT / "docs" / "adicionar_reaproveitamento_candidatura.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("def reaproveitar_candidatura_recrutamento", source)
        self.assertIn("recrutamento_ciclos_historico", source)
        self.assertIn("recrutamento_etapas_historico", source)
        self.assertIn("recrutamento_complementos_historico", source)
        self.assertIn("etapas_reabrir", source)
        self.assertIn("Reaproveitar candidatura", template)
        self.assertIn('name="cargo_pretendido"', template)
        self.assertIn('name="justificativa"', template)
        self.assertIn('name="etapas_reabrir"', template)
        self.assertIn('name="exige_teste_pratico"', template)
        self.assertIn("CREATE TABLE IF NOT EXISTS recrutamento_ciclos_historico", migration)
        self.assertIn("CREATE TABLE IF NOT EXISTS recrutamento_etapas_historico", migration)
        self.assertIn("CREATE TABLE IF NOT EXISTS recrutamento_complementos_historico", migration)

    def test_candidate_reuse_requires_consolidated_decision(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        template = (
            ROOT / "app" / "templates" / "recrutamento_candidatura_detalhe.html"
        ).read_text(encoding="utf-8")

        self.assertIn('if not candidatura.get("decisao_resultado")', source)
        self.assertGreaterEqual(
            template.count("pode_gerenciar and candidatura.decisao_resultado"),
            2,
        )

    def test_client_pre_registration_is_a_simple_parallel_stage(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        template = (
            ROOT / "app" / "templates" / "recrutamento_candidatura_detalhe.html"
        ).read_text(encoding="utf-8")
        migration = (
            ROOT / "docs" / "simplificar_pre_cadastro_cliente_recrutamento.sql"
        ).read_text(encoding="utf-8")

        self.assertIn("def salvar_pre_cadastro_cliente_recrutamento", source)
        self.assertIn('"nao_iniciado": "Não iniciado"', source)
        self.assertIn('"aguardando_validacao": "Aguardando validação"', source)
        self.assertIn("Pré-cadastro cliente", template)
        self.assertIn('name="cliente"', template)
        self.assertIn('name="status"', template)
        self.assertNotIn('name="documento_identidade"', template)
        self.assertNotIn("modalNovaValidacao", template)
        self.assertIn('pre_cadastro["status"] == "reprovado"', source)
        self.assertIn("pre_cadastro_cliente", migration)
        self.assertIn("aguardando_validacao", migration)
        self.assertIn("DELETE FROM recrutamento_validacoes_cliente", source)
        self.assertIn(
            "pode_gerenciar and candidatura.status != 'liberado_admissao'",
            template,
        )
        self.assertIn(
            '<div class="collapse mt-3" id="formPreCadastroCliente">',
            template,
        )
        self.assertIn("Editar pré-cadastro", template)

    def test_proposal_and_pre_admission_follow_business_rules(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        template = (
            ROOT / "app" / "templates" / "recrutamento_candidatura_detalhe.html"
        ).read_text(encoding="utf-8")
        migration = (
            ROOT / "docs" / "adicionar_proposta_pre_admissao_recrutamento.sql"
        ).read_text(encoding="utf-8")

        self.assertIn('"nao_enviada": "Não enviada"', source)
        self.assertIn('"sem_retorno": "Sem retorno"', source)
        self.assertIn("def salvar_proposta_recrutamento", source)
        self.assertIn('acao in ("registrar_envio", "editar_envio")', source)
        self.assertIn('acao == "registrar_retorno"', source)
        self.assertIn('name="acao" value="registrar_retorno"', template)
        self.assertIn("Registrar envio", template)
        self.assertIn("Retorno do candidato", template)
        self.assertIn("def salvar_exame_admissional_recrutamento", source)
        self.assertIn('"concluido": "Concluído"', source)
        self.assertIn('"apto_restricao": "Apto com restrição"', source)
        self.assertIn("def salvar_documentos_pre_admissao_recrutamento", source)
        self.assertIn("def concluir_pre_admissao_recrutamento", source)
        self.assertIn("Envio da proposta", template)
        self.assertIn("Exame admissional", template)
        self.assertIn(
            '<div class="collapse mt-3" id="formExameAdmissional">',
            template,
        )
        self.assertIn("Editar exame admissional", template)
        self.assertIn("Documentação admissional", template)
        self.assertIn("recrutamento_tipos_documento", migration)
        self.assertIn("nao_aplicavel", migration)

    def test_candidate_or_hr_can_end_recruitment_without_losing_history(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        template = (
            ROOT / "app" / "templates" / "recrutamento_candidatura_detalhe.html"
        ).read_text(encoding="utf-8")

        self.assertIn("def encerrar_candidatura_recrutamento", source)
        self.assertIn('"desistente": "Candidato declinou"', source)
        self.assertIn('"encerrado": "Cancelado pelo RH"', source)
        self.assertIn(
            'STATUS_CANDIDATURA_ENCERRADA = ("encerrado", "desistente")',
            source,
        )
        self.assertIn('"liberado_admissao"', source)
        self.assertIn("pode_encerrar=(", source)
        self.assertIn("_validar_candidatura_aberta(candidatura)", source)
        self.assertIn("INSERT INTO recrutamento_historico", source)
        self.assertIn('name="tipo_encerramento"', template)
        self.assertIn('value="desistencia"', template)
        self.assertIn('value="cancelamento_rh"', template)
        self.assertIn('name="justificativa"', template)

    def test_recruitment_templates_compile_after_layout_adjustments(self):
        from app import create_app

        app = create_app()
        for template in (
            "novo_candidato_recrutamento.html",
            "recrutamento_candidatos.html",
            "recrutamento_candidatura_detalhe.html",
            "recrutamento_minhas_avaliacoes.html",
            "recrutamento_minha_avaliacao_detalhe.html",
        ):
            app.jinja_env.get_template(template)

    def test_recruitment_layout_and_editing_adjustments_are_preserved(self):
        source = (ROOT / "app" / "views" / "recrutamento.py").read_text(
            encoding="utf-8"
        )
        cadastro = (
            ROOT / "app" / "templates" / "novo_candidato_recrutamento.html"
        ).read_text(encoding="utf-8")
        detalhe = (
            ROOT / "app" / "templates" / "recrutamento_candidatura_detalhe.html"
        ).read_text(encoding="utf-8")
        avaliacao = (
            ROOT / "app" / "templates" / "recrutamento_minha_avaliacao_detalhe.html"
        ).read_text(encoding="utf-8")

        self.assertIn("const cpfValido", cadastro)
        self.assertIn("request.form.get('estado', 'MG')", cadastro)
        self.assertIn('id="cargo_id"', cadastro)
        self.assertIn(">Voltar</a>", cadastro)
        self.assertIn(">Salvar</button>", cadastro)
        self.assertIn("and not etapa.avaliador_id", detalhe)
        self.assertIn("Gerdau - Ouro Branco", detalhe)
        self.assertIn("document.getElementById('dataExame').disabled=this.value!=='agendado'", detalhe)
        self.assertIn("function atualizarCamposExameAdmissional(status)", detalhe)
        self.assertIn("data.disabled = !permiteData", detalhe)
        self.assertIn("resultado.disabled = !concluido", detalhe)
        self.assertIn("observacoes.disabled = !(concluido || cancelado)", detalhe)
        self.assertIn('id="fluxoPosSelecaoConteudo"', detalhe)
        self.assertIn('id="historicoRecrutamentoConteudo"', detalhe)
        self.assertIn("shown.bs.collapse", detalhe)
        self.assertIn("hidden.bs.collapse", detalhe)
        self.assertNotIn("Registrar parecer", detalhe)
        self.assertNotIn("Adicionar complemento", detalhe)
        self.assertNotIn("Salvar documentos", detalhe)
        self.assertIn("observacoes_enviadas", source)
        self.assertIn("já foi atribuída e não pode ser reatribuída", source)
        self.assertIn("DATE_SUB(h.criado_em, INTERVAL 3 HOUR)", source)
        self.assertIn("recrutamento_experiencias", source)
        self.assertIn("Experiências profissionais", avaliacao)
        self.assertIn("etapa.decisao_resultado", avaliacao)


if __name__ == "__main__":
    unittest.main()
