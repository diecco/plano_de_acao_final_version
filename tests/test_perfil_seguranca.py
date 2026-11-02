import unittest
from datetime import date
from pathlib import Path

from app.views.perfil_seguranca import (
    _filtros_usuarios,
    _periodo_perfil,
    _preparar_indicadores,
)


class PerfilSegurancaTests(unittest.TestCase):
    def test_periodo_resolve_mes_inteiro(self):
        mes, inicio, fim = _periodo_perfil("2024-02", date(2026, 10, 31))
        self.assertEqual("2024-02", mes)
        self.assertEqual(date(2024, 2, 1), inicio)
        self.assertEqual(date(2024, 2, 29), fim)

    def test_periodo_invalido_retorna_mes_atual(self):
        mes, inicio, fim = _periodo_perfil("invalido", date(2026, 10, 31))
        self.assertEqual("2026-10", mes)
        self.assertEqual(date(2026, 10, 1), inicio)
        self.assertEqual(date(2026, 10, 31), fim)

    def test_consulta_usa_nome_real_da_tabela_de_auditorias(self):
        fonte = (
            Path(__file__).parents[1] / "app" / "views" / "perfil_seguranca.py"
        ).read_text(encoding="utf-8")
        self.assertIn("FROM auditorias_padrao ap", fonte)
        self.assertNotIn("FROM auditoria_padrao ap", fonte)

    def test_horas_de_seguranca_consideram_relacao_e_campo_legado(self):
        fonte = (
            Path(__file__).parents[1] / "app" / "views" / "perfil_seguranca.py"
        ).read_text(encoding="utf-8")
        self.assertIn("LEFT JOIN hs_registros_participantes hp", fonte)
        self.assertIn("FIND_IN_SET", fonte)
        self.assertIn("COUNT(DISTINCT r.id)", fonte)

    def test_visao_geral_respeita_escopo_e_busca(self):
        sql, parametros = _filtros_usuarios(
            False, 7, "Maria", centro_id=99, cargo_id=4
        )
        self.assertIn("u.centro_custos_id = %s", sql)
        self.assertIn("u.cargo_id = %s", sql)
        self.assertIn("u.nome LIKE %s OR u.matricula LIKE %s", sql)
        self.assertEqual([7, 4, "%Maria%", "%Maria%"], parametros)

    def test_visao_geral_filtra_status_sem_perder_escopo(self):
        sql, parametros = _filtros_usuarios(
            False, 7, status="inativo"
        )
        self.assertIn("u.ativo = 0", sql)
        self.assertIn("u.centro_custos_id = %s", sql)
        self.assertEqual([7], parametros)

        sql_todos, _ = _filtros_usuarios(True, None, status="todos")
        self.assertNotIn("u.ativo", sql_todos)

    def test_indicadores_identificam_colaborador_sem_registros(self):
        item = _preparar_indicadores({
            "horas_seguranca": 0,
            "auditorias_padrao": 0,
            "recusas": 0,
            "melhorias": 0,
            "minutos_treinamento": 0,
        })
        self.assertFalse(item["tem_registros"])
        self.assertEqual(0.0, item["horas_treinamento"])

    def test_indicadores_convertem_minutos_de_treinamento(self):
        item = _preparar_indicadores({
            "horas_seguranca": 1,
            "auditorias_padrao": 2,
            "recusas": 1,
            "melhorias": 0,
            "minutos_treinamento": 90,
        })
        self.assertTrue(item["tem_registros"])
        self.assertEqual(4, item["total_praticas"])
        self.assertEqual(1.5, item["horas_treinamento"])

    def test_historico_abre_visualizacao_somente_leitura(self):
        raiz = Path(__file__).parents[1]
        fonte = (raiz / "app" / "views" / "perfil_seguranca.py").read_text(
            encoding="utf-8"
        )
        template = (
            raiz / "app" / "templates" /
            "visualizar_pratica_perfil_seguranca.html"
        ).read_text(encoding="utf-8")
        self.assertIn("visualizar_pratica_perfil_seguranca", fonte)
        self.assertIn("Consulta somente leitura", template)
        self.assertIn("Voltar ao Perfil de Segurança", template)

    def test_visualizacao_da_recusa_reproduz_campos_do_lancamento(self):
        template = (
            Path(__file__).parents[1] / "app" / "templates" /
            "visualizar_recusa_perfil_seguranca.html"
        ).read_text(encoding="utf-8")
        for rotulo in (
            "Data da Recusa", "Hora da Recusa", "Pessoa que Recusou",
            "Área / Local", "Classificação", "Potencial de Severidade",
            "Causa da Recusa", "Descrição da Recusa",
        ):
            self.assertIn(rotulo, template)
        self.assertNotIn("type=\"submit\"", template)

    def test_visualizacao_hs_reproduz_pdf_e_vincula_acoes(self):
        raiz = Path(__file__).parents[1]
        template = (
            raiz / "app" / "templates" /
            "visualizar_hora_seguranca_perfil.html"
        ).read_text(encoding="utf-8")
        for rotulo in (
            "RELATÓRIO DE HORA DE SEGURANÇA", "1. Identificação",
            "2. Itens de verificação", "Status da ação", "Desvio / ação",
            "Auditados", "Participantes",
        ):
            self.assertIn(rotulo, template)
        self.assertIn("main.editar_acao", template)
        self.assertIn("next=url_retorno", template)
        self.assertIn('<col style="width: 28%">', template)
        self.assertIn('class="hs-voltar">Voltar</a>', template)
        self.assertNotIn("Voltar ao Perfil de Segurança", template)
        self.assertIn("{% block conteudo %}", template)
        self.assertNotIn("{% block content %}", template)
        self.assertNotIn("type=\"submit\"", template)

    def test_visualizacao_ap_exibe_checklist_e_acoes_somente_leitura(self):
        template = (
            Path(__file__).parents[1] / "app" / "templates" /
            "visualizar_auditoria_padrao_perfil.html"
        ).read_text(encoding="utf-8")
        for rotulo in (
            "AUDITORIA DE PADRÃO", "1. Identificação",
            "2. Itens de verificação", "Desvio / ação",
            "Responsável", "Status da ação",
            "Pontos observados / oportunidades de melhoria",
        ):
            self.assertIn(rotulo, template)
        self.assertIn("main.editar_acao", template)
        self.assertIn("next=url_retorno", template)
        self.assertIn(
            'class="btn btn-cinza btn-sm">Voltar</a>', template
        )
        self.assertNotIn("type=\"submit\"", template)


if __name__ == "__main__":
    unittest.main()
