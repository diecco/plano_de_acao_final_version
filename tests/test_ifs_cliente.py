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
            "INSERT INTO ifs_blocos (nome, ordem, ativo) VALUES ('CONDIÇÃO FÍSICA', 1, 1)",
            migration,
        )
        self.assertNotIn("CONTROLE SISTÊMICO (PROCEDIMENTO/APR/PT)", migration)
        self.assertIn(
            "AND ordem = 1\n  AND nome <> 'CONDIÇÃO FÍSICA'",
            migration,
        )
        self.assertIn(
            "UPDATE ifs_itens SET ativo = 0 WHERE id > 0 AND ativo = 1",
            migration,
        )
        self.assertIn(
            "UPDATE ifs_blocos SET ativo = 0 WHERE id > 0 AND ativo = 1",
            migration,
        )
        self.assertIn(
            "ALTER TABLE ifs_itens MODIFY COLUMN potencial ENUM('A', 'B', 'C') NULL",
            migration,
        )
        self.assertNotIn(", '', ", migration)
        self.assertIn("'Outros:', NULL", migration)
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
        self.assertEqual(source.count("@gestor_ssma_required"), 7)
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

    def test_cabecalho_rev13_e_persistido_e_data_inicia_vazia(self):
        template = (
            ROOT / "app" / "templates" / "nova_ifs_cliente.html"
        ).read_text(encoding="utf-8")
        detalhe = (
            ROOT / "app" / "templates" / "detalhar_ifs_cliente.html"
        ).read_text(encoding="utf-8")
        view = (ROOT / "app" / "views" / "ifs_cliente.py").read_text(
            encoding="utf-8"
        )
        migration = (
            ROOT / "docs" / "adicionar_cabecalho_ifs_cliente_rev13.sql"
        ).read_text(encoding="utf-8")

        self.assertIn('name="data_inspecao" required', template)
        self.assertNotIn("data_hoje", template)
        self.assertNotIn("date.today", view)
        campos = (
            "gerencia",
            "administrador_contrato",
            "contratada",
            "profissional_sesmt_contratada_lideranca",
            "sesmt_gerdau_fiscalizadora",
        )
        for campo in campos:
            self.assertIn(f'name="{campo}"', template)
            self.assertIn(f'request.form.get("{campo}")', view)
            self.assertIn(f"inspecao.{campo}", detalhe)
            self.assertIn(f"COLUMN_NAME = '{campo}'", migration)

    def test_listagem_tem_periodos_indicadores_e_origem_padronizada(self):
        template = (
            ROOT / "app" / "templates" / "listar_ifs_cliente.html"
        ).read_text(encoding="utf-8")
        view = (ROOT / "app" / "views" / "ifs_cliente.py").read_text(
            encoding="utf-8"
        )
        migration = (
            ROOT / "docs" / "corrigir_origem_ifs_cliente.sql"
        ).read_text(encoding="utf-8")

        for periodo in ("mes_atual", "mes_anterior", "mes_proximo", "personalizado"):
            self.assertIn(f'value="{periodo}"', template)
        for indicador in ("total", "nota_media", "nao_conformidades", "acoes_pendentes"):
            self.assertIn(f"indicadores.{indicador}", template)
        self.assertIn('FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")', view)
        self.assertIn('(ORIGEM_IFS_CLIENTE, ORIGEM_IFS_CLIENTE, origem["id"])', view)
        self.assertIn("SET nome = 'IFS do Cliente'", migration)
        self.assertIn("descricao = 'IFS do Cliente'", migration)

    def test_listagem_tem_ordenacao_segura_no_cabecalho(self):
        template = (
            ROOT / "app" / "templates" / "listar_ifs_cliente.html"
        ).read_text(encoding="utf-8")
        view = (ROOT / "app" / "views" / "ifs_cliente.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("botoes_ordenacao", template)
        self.assertIn('class="btn-group btn-group-sm"', template)
        self.assertNotIn("flex-column", template)
        self.assertIn("bi-caret-up-fill", template)
        self.assertIn("bi-caret-down-fill", template)
        for campo in (
            "data_inspecao", "referencia_cliente", "descricao_atividade_os",
            "percentual", "total_nao_conformidades", "total_acoes", "status",
        ):
            self.assertIn(f'"{campo}":', view)
            self.assertIn(f"'{campo}'", template)
        self.assertIn("if filtros[\"sort\"] not in colunas_ordenacao", view)
        self.assertIn("if filtros[\"order\"] not in {\"asc\", \"desc\"}", view)
        self.assertIn('class="col-md-2 ms-md-auto"', template)

    def test_listagem_oferece_edicao_e_exclusao_logica(self):
        template = (
            ROOT / "app" / "templates" / "listar_ifs_cliente.html"
        ).read_text(encoding="utf-8")
        editar = (
            ROOT / "app" / "templates" / "editar_ifs_cliente.html"
        ).read_text(encoding="utf-8")
        view = (ROOT / "app" / "views" / "ifs_cliente.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("Plano de ação", template)
        self.assertIn("main.editar_ifs_cliente", template)
        self.assertIn("main.excluir_ifs_cliente", template)
        self.assertIn("bi-pencil-square", template)
        self.assertIn("bi-trash", template)
        self.assertIn("data-confirmacao-observacao", template)
        self.assertIn("def editar_ifs_cliente", view)
        self.assertIn("def excluir_ifs_cliente", view)
        self.assertIn("SET ativo=0, atualizado_em=CURRENT_TIMESTAMP", view)
        self.assertIn("'exclusao'", view)
        self.assertIn("Respostas, nota, desvios e planos de ação permanecem preservados", editar)

    def test_relatorio_pdf_reproduz_detalhes_sem_historico(self):
        template = (
            ROOT / "app" / "templates" / "listar_ifs_cliente.html"
        ).read_text(encoding="utf-8")
        view = (ROOT / "app" / "views" / "ifs_cliente.py").read_text(
            encoding="utf-8"
        )
        pdf = (ROOT / "app" / "utils" / "ifs_cliente_pdf.py").read_text(
            encoding="utf-8"
        )

        self.assertIn("main.gerar_pdf_ifs_cliente", template)
        self.assertIn("bi-file-earmark-pdf", template)
        self.assertIn("def gerar_pdf_ifs_cliente", view)
        self.assertIn('mimetype="application/pdf"', view)
        self.assertIn("RELATÓRIO DE IFS DO CLIENTE", pdf)
        self.assertIn("Não conformidades e planos de ação", pdf)
        self.assertNotIn("ifs_cliente_historico", pdf)
        self.assertNotIn("Histórico", pdf)


if __name__ == "__main__":
    unittest.main()
