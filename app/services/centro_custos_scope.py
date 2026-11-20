def centros_ativos_da_mesma_unidade(cursor, centro_custos_id):
    """Retorna os centros ativos que representam a mesma unidade operacional."""
    cursor.execute(
        """
        SELECT DISTINCT escopo.id, escopo.codigo
        FROM centros_custos origem
        JOIN centros_custos escopo
          ON escopo.ativo = 1
         AND (
              escopo.id = origem.id
              OR (
                   TRIM(COALESCE(origem.descricao, '')) <> ''
                   AND CAST(TRIM(escopo.descricao) AS BINARY) =
                       CAST(TRIM(origem.descricao) AS BINARY)
              )
         )
        WHERE origem.id = %s
        ORDER BY escopo.codigo
        """,
        (centro_custos_id or 0,),
    )
    return cursor.fetchall() or []


def codigos_centros_ativos_da_mesma_unidade(cursor, centro_custos_id):
    return [
        (centro.get("codigo") or "").strip()
        for centro in centros_ativos_da_mesma_unidade(cursor, centro_custos_id)
        if (centro.get("codigo") or "").strip()
    ]
