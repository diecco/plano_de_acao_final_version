from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FormulariosConfiguraveisTests(unittest.TestCase):
    def test_modulo_possui_tabelas_proprias(self):
        sql=(ROOT/'docs'/'criar_formularios_configuraveis.sql').read_text(encoding='utf-8')
        self.assertIn('CREATE TABLE IF NOT EXISTS formulario_modelos',sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS formulario_registros',sql)
        self.assertNotIn('checklist_execucoes',sql)

    def test_modulo_tem_construtor_plano_independente(self):
        js=(ROOT/'app'/'static'/'js'/'formulario-builder.js').read_text(encoding='utf-8')
        template=(ROOT/'app'/'templates'/'formulario_configuravel_editar.html').read_text(encoding='utf-8')
        self.assertIn('Largura',js)
        self.assertIn('Exibir na listagem',js)
        self.assertIn('data-form-builder',template)
        self.assertNotIn('data-checklist-builder',template)

    def test_sidebar_separa_checklists_e_formularios(self):
        sidebar=(ROOT/'app'/'templates'/'components'/'sidebar.html').read_text(encoding='utf-8')
        self.assertIn('Checklists configuráveis',sidebar)
        self.assertIn('Formulários configuráveis',sidebar)


if __name__ == '__main__':
    unittest.main()
