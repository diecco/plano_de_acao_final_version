import unittest
from pathlib import Path


MATRIX_SOURCE = (
    Path(__file__).resolve().parents[1] / "app" / "views" / "matriz_capacitacao.py"
).read_text(
    encoding="utf-8"
)


def trecho(inicio, fim):
    return MATRIX_SOURCE.split(inicio, 1)[1].split(fim, 1)[0]


class MatrizCapacitacaoRegressionTests(unittest.TestCase):
    def test_rotas_de_inclusao_validam_entidades_no_backend(self):
        rotas = [
            ("def salvar_procedimento_cargo():", "def excluir_procedimento_cargo"),
            ("def adicionar_funcao_cargo():", "def remover_funcao_cargo"),
            ("def adicionar_procedimento_funcao():", "def remover_procedimento_funcao"),
            ("def adicionar_setor_cargo():", "def remover_setor_cargo"),
            ("def adicionar_procedimento_setor():", "def remover_procedimento_setor"),
        ]
        for inicio, fim in rotas:
            with self.subTest(rota=inicio):
                self.assertIn("_mc_validar_vinculo", trecho(inicio, fim))

    def test_procedimentos_subordinados_exigem_vinculo_principal(self):
        for inicio, fim in [
            ("def adicionar_procedimento_funcao():", "def remover_procedimento_funcao"),
            ("def adicionar_procedimento_setor():", "def remover_procedimento_setor"),
        ]:
            with self.subTest(rota=inicio):
                self.assertIn("exigir_vinculo=True", trecho(inicio, fim))

    def test_verificacao_individual_considera_revisao_vigente(self):
        verificacao = MATRIX_SOURCE.split("def verificar_matriz_funcionario():", 1)[1]
        self.assertIn("procedimento_revisao_id", verificacao)
        self.assertIn("requer_treinamento = 1", verificacao)
        self.assertIn("vigente = 1", verificacao)

    def test_consultas_ignoram_vinculos_subordinados_orfaos(self):
        self.assertIn("JOIN matriz_cargo_funcoes mcf", MATRIX_SOURCE)
        self.assertIn("JOIN matriz_cargo_setores mcs", MATRIX_SOURCE)


if __name__ == "__main__":
    unittest.main()
