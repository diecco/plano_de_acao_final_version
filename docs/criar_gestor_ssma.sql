-- Executar primeiro na base de homologação.
ALTER TABLE usuarios
    ADD COLUMN gestor_ssma TINYINT(1) NOT NULL DEFAULT 0;

-- Conferência para definição manual dos novos Gestores SSMA.
SELECT
    id,
    nome,
    matricula,
    pode_criar_agendamento_ssma,
    pode_direcionar_desvios,
    gestor_ssma
FROM usuarios
WHERE ativo = 1
  AND (
      pode_criar_agendamento_ssma = 1
      OR pode_direcionar_desvios = 1
  )
ORDER BY nome;

-- Exemplo de ativação após conferência:
-- UPDATE usuarios
-- SET gestor_ssma = 1,
--     acesso_ssma = 1
-- WHERE id IN (1, 2);
