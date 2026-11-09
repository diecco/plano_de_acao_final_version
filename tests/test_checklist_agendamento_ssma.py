import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ChecklistAgendamentoSsmaTests(unittest.TestCase):
    def test_migracao_cria_vinculos_e_unicidade(self):
        sql = (ROOT / "docs" / "integrar_checklists_agendamento_ssma.sql").read_text(
            encoding="utf-8"
        )
        self.assertIn("agendamentos_ssma ADD COLUMN checklist_modelo_id", sql)
        self.assertIn("checklist_execucoes ADD COLUMN agendamento_id", sql)
        self.assertIn("UNIQUE INDEX uq_checklist_execucoes_agendamento", sql)
        self.assertIn("fk_checklist_execucoes_agendamento", sql)

    def test_agenda_valida_escopo_e_abre_checklist(self):
        fonte = (ROOT / "app" / "views" / "agenda_ssma.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"checklist_configuravel"', fonte)
        self.assertIn("buscar_checklist_agendavel", fonte)
        self.assertIn("cm.status = 'publicado'", fonte)
        self.assertIn("cm.disponivel_agendamento = 1", fonte)
        self.assertIn('"main.aplicar_checklist_dinamico"', fonte)

    def test_execucao_conclui_agendamento_sem_duplicidade(self):
        fonte = (ROOT / "app" / "views" / "checklists_dinamicos.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("FOR UPDATE", fonte)
        self.assertIn("agendamento_id", fonte)
        self.assertIn("registro_executado_id = %s", fonte)
        self.assertIn("AND registro_executado_id IS NULL", fonte)
        self.assertIn('"concluida_com_atraso"', fonte)

    def test_telas_exibem_selecao_e_nome_do_checklist(self):
        novo = (ROOT / "app" / "templates" / "novo_agendamento_ssma.html").read_text(
            encoding="utf-8"
        )
        calendario = (ROOT / "app" / "templates" / "meu_calendario_ssma.html").read_text(
            encoding="utf-8"
        )
        self.assertIn('value="checklist_configuravel"', novo)
        self.assertIn('name="checklist_modelo_id"', novo)
        self.assertIn("item.nome_checklist", calendario)
        self.assertNotIn("35784 tokens truncated", novo)

    def test_disponibilidade_e_configuracao_independente_da_sidebar(self):
        fonte = (ROOT / "app" / "views" / "checklists_dinamicos.py").read_text(
            encoding="utf-8"
        )
        cadastro = (ROOT / "app" / "templates" / "checklists_dinamicos.html").read_text(
            encoding="utf-8"
        )
        edicao = (ROOT / "app" / "templates" / "checklist_dinamico_editar.html").read_text(
            encoding="utf-8"
        )
        migracao = (
            ROOT / "docs" / "adicionar_disponibilidade_agendamento_checklists.sql"
        ).read_text(encoding="utf-8")
        self.assertIn("disponivel_agendamento", fonte)
        self.assertIn('name="disponivel_agendamento"', cadastro)
        self.assertIn('name="disponivel_agendamento"', edicao)
        self.assertIn("DEFAULT 0", migracao)


if __name__ == "__main__":
    unittest.main()
