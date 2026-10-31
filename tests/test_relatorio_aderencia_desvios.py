import unittest

from app.views.agenda_ssma import _carregar_desvios_execucao


class CursorDesviosFake:
    def __init__(self):
        self.resultado = []
        self.consultas = []

    def execute(self, sql, parametros):
        self.consultas.append((sql, parametros))
        if 'FROM hs_respostas' in sql:
            self.resultado = [
                {'registro_id': 10, 'descricao': 'Desvio do checklist'},
                {'registro_id': 10, 'descricao': 'Desvio adicional'}
            ]
        elif 'FROM auditoria_padrao_desvios' in sql:
            self.resultado = [
                {'registro_id': 20, 'descricao': 'Desvio da auditoria'}
            ]
        elif 'FROM ifs_desvios' in sql:
            self.resultado = [
                {'registro_id': 30, 'descricao': 'Desvio da IFS'}
            ]
        else:
            raise AssertionError('Consulta inesperada')

    def fetchall(self):
        return self.resultado


class RelatorioAderenciaDesviosTest(unittest.TestCase):
    def test_carrega_desvios_reais_das_tres_praticas(self):
        cursor = CursorDesviosFake()
        registros = [
            {'pratica': 'hora_seguranca', 'registro_executado_id': 10},
            {'pratica': 'auditoria_padrao', 'registro_executado_id': 20},
            {'pratica': 'ifs', 'registro_executado_id': 30},
            {'pratica': 'hora_seguranca', 'registro_executado_id': 40}
        ]

        _carregar_desvios_execucao(cursor, registros)

        self.assertEqual(
            registros[0]['desvios_execucao'],
            'Desvio do checklist; Desvio adicional'
        )
        self.assertEqual(
            registros[1]['desvios_execucao'],
            'Desvio da auditoria'
        )
        self.assertEqual(
            registros[2]['desvios_execucao'],
            'Desvio da IFS'
        )
        self.assertIsNone(registros[3]['desvios_execucao'])
        self.assertEqual(len(cursor.consultas), 3)

    def test_nao_consulta_banco_sem_execucoes_vinculadas(self):
        cursor = CursorDesviosFake()
        registros = [
            {'pratica': 'ifs', 'registro_executado_id': None},
            {'pratica': 'outra', 'registro_executado_id': 99}
        ]

        _carregar_desvios_execucao(cursor, registros)

        self.assertEqual(cursor.consultas, [])
        self.assertIsNone(registros[0]['desvios_execucao'])
        self.assertIsNone(registros[1]['desvios_execucao'])


if __name__ == '__main__':
    unittest.main()

