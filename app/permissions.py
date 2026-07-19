def resolver_escopo_usuarios_treinamento(
    perfil,
    centro_custos_id,
    usuario_id,
):
    if perfil in ('administrador', 'avancado'):
        return {}

    if perfil == 'intermediario':
        return {
            'centro_custos_id': centro_custos_id
            if centro_custos_id is not None
            else -1
        }

    return {
        'usuario_id': usuario_id
        if usuario_id is not None
        else -1
    }


def filtrar_usuario_ids_permitidos(
    usuario_ids_solicitados,
    usuario_ids_permitidos,
    selecionar_todos=False,
):
    permitidos = set(usuario_ids_permitidos or [])

    if not permitidos:
        return [-1]

    if selecionar_todos or not usuario_ids_solicitados:
        return sorted(permitidos)

    filtrados = [
        usuario_id
        for usuario_id in usuario_ids_solicitados
        if usuario_id in permitidos
    ]

    return filtrados or [-1]
