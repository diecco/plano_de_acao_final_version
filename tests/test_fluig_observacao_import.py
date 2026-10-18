import unittest
from io import BytesIO

from openpyxl import Workbook

from app.services.fluig_observacao_import import FluigImportError, parse_fluig_observacoes


class FluigObservacaoImportTest(unittest.TestCase):
    def _arquivo(self, headers, values):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(headers)
        sheet.append(values)
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def test_parseia_exportacao_e_normaliza_codigos(self):
        headers = [
            "Solicitação", "Situação", "Início", "Calendario - 001",
            "Matricula  Requisitante", "Nome_Lancamento - 001",
            "Cod_CC - 001", "Nome_CC - 001", "Contrato_Func - 001",
            "Contrato_Obs - 001", "Num_Obs - 001", "radio_types - 001",
            "Setor_OBS - 001", "A1 - 001", "C11 - 001", "F3 - 001",
        ]
        values = [
            1122929, "Finalizada", "18/10/2026", "2026-10-18",
            "014446", "Observador Teste", "1.10.0024.01", "Centro Teste",
            "Contrato Teste", "Local Teste", "01", "Operação", "Setor 1",
            "2", 1, 0,
        ]
        registros, erros = parse_fluig_observacoes(self._arquivo(headers, values))
        self.assertEqual(erros, [])
        registro = registros[0]
        self.assertEqual(registro["solicitacao"], "1122929")
        self.assertEqual(registro["pessoas_observadas"], 1)
        self.assertEqual(registro["respostas"], {"A01": 2, "C11": 1})
        self.assertEqual(registro["status"], "concluida")

    def test_rejeita_arquivo_de_outro_processo(self):
        arquivo = self._arquivo(["Solicitação", "Outro campo"], [1, "x"])
        with self.assertRaises(FluigImportError):
            parse_fluig_observacoes(arquivo)

    def test_reporta_linha_invalida_sem_perder_validas(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Solicitação", "Calendario - 001", "A1 - 001"])
        sheet.append([1, "18/10/2026", 1])
        sheet.append([2, "data inválida", 1])
        output = BytesIO()
        workbook.save(output)
        registros, erros = parse_fluig_observacoes(output.getvalue())
        self.assertEqual(len(registros), 1)
        self.assertEqual(erros[0]["linha"], 3)


if __name__ == "__main__":
    unittest.main()
