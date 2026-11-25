-- Padroniza a origem das ações da IFS do Cliente.
-- Os vínculos das ações existentes são preservados.

UPDATE origens
SET nome = 'IFS do Cliente',
    descricao = 'IFS do Cliente'
WHERE id > 0
  AND ativo = 1
  AND (
      nome = 'IFS do Cliente'
      OR nome IN (
          'Acoes originadas em IFS realizada pelo cliente',
          'Ações originadas em IFS realizada pelo cliente',
          'Acoes originadas em FS realizada pelo cliente',
          'Ações originadas em FS realizada pelo cliente'
      )
      OR descricao IN (
          'Acoes originadas em IFS realizada pelo cliente',
          'Ações originadas em IFS realizada pelo cliente',
          'Acoes originadas em FS realizada pelo cliente',
          'Ações originadas em FS realizada pelo cliente'
      )
  );

SELECT id, nome, descricao, centro_custos_id, ativo
FROM origens
WHERE nome = 'IFS do Cliente'
ORDER BY centro_custos_id, id;
