import unittest
from io import BytesIO

from openpyxl import Workbook

from app.services.fluig_relato_ocorrencia_import import (
    RelatoOcorrenciaImportError,
    parse_fluig_relatos_ocorrencias,
)


class FluigRelatoOcorrenciaImportTest(unittest.TestCase):
    def _file(self, headers, rows):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        output = BytesIO()
        workbook.save(output)
        return output.getvalue()

    def test_parses_occurrence_and_involved_people(self):
        headers = [
            "Solicitação", "Situação", "Matricula  Requisitante", "Requisitante",
            "DATAOCORRENCIA - Relato de Ocorrência",
            "HORAOCORRENCIA - Relato de Ocorrência",
            "DESCRICAOOCORRENCIA - Relato de Ocorrência",
            "OCORRENCIA - Relato de Ocorrência",
            "TIPOOCORRENCIA - Relato de Ocorrência",
            "CENTROCUSTOOCORRENCIA - Relato de Ocorrência",
            "RESPONSAVELENVOLVIDO - Relato de Ocorrência",
            "MATRICULARESPONSAVELENVOLVIDO - Relato de Ocorrência",
        ]
        rows = [[
            12345, "Finalizada", "uuid-1", "Usuário Teste", "20/11/2026",
            "14:30", "Descrição de teste", "Incidente", "Condição",
            "1.10.0052.13 - Gerdau", "Pessoa A\nPessoa B", "100\n200",
        ]]
        records, errors = parse_fluig_relatos_ocorrencias(self._file(headers, rows))
        self.assertEqual(errors, [])
        self.assertEqual(records[0]["solicitacao"], "12345")
        self.assertEqual(records[0]["tipo_relato"], "Incidente")
        self.assertEqual(records[0]["tipo_origem"], "Condição")
        self.assertEqual(records[0]["centro_custos_codigo"], "1.10.0052.13")
        self.assertEqual(len(records[0]["envolvidos"]), 2)
        self.assertEqual(records[0]["envolvidos"][1]["matricula"], "200")
        self.assertIn("Solicitação", records[0]["dados_origem"])

    def test_rejects_export_from_another_process(self):
        content = self._file(["Solicitação", "Outro campo"], [[1, "x"]])
        with self.assertRaises(RelatoOcorrenciaImportError):
            parse_fluig_relatos_ocorrencias(content)

    def test_reports_invalid_row_without_losing_valid_row(self):
        headers = [
            "Solicitação", "Situação",
            "DATAOCORRENCIA - Relato de Ocorrência",
            "DESCRICAOOCORRENCIA - Relato de Ocorrência",
            "OCORRENCIA - Relato de Ocorrência",
        ]
        rows = [
            [1, "Finalizada", "20/11/2026", "Registro válido", "Desvio"],
            [2, "Finalizada", "data inválida", "Registro inválido", "Desvio"],
        ]
        records, errors = parse_fluig_relatos_ocorrencias(self._file(headers, rows))
        self.assertEqual(len(records), 1)
        self.assertEqual(errors[0]["linha"], 3)
        self.assertEqual(errors[0]["solicitacao"], "2")

    def test_detects_duplicate_request_in_same_file(self):
        headers = [
            "Solicitação", "Situação",
            "DATAOCORRENCIA - Relato de Ocorrência",
            "DESCRICAOOCORRENCIA - Relato de Ocorrência",
            "OCORRENCIA - Relato de Ocorrência",
        ]
        rows = [
            [1, "Finalizada", "20/11/2026", "Primeiro", "Desvio"],
            [1, "Finalizada", "21/11/2026", "Segundo", "Desvio"],
        ]
        records, errors = parse_fluig_relatos_ocorrencias(self._file(headers, rows))
        self.assertEqual(len(records), 1)
        self.assertIn("duplicada", errors[0]["erro"])


if __name__ == "__main__":
    unittest.main()
