PERFIS_GLOBAIS = {"administrador", "avancado"}


def filtro_escopo_visualizacao(perfil, centro_custos_id, alias="r"):
    """Retorna o filtro SQL e os parâmetros do escopo de visualização."""
    if perfil in PERFIS_GLOBAIS:
        return "1 = 1", []

    if centro_custos_id is None:
        return "1 = 0", []

    return f"{alias}.centro_custos_id = %s", [centro_custos_id]


def pode_visualizar_registro(perfil, centro_usuario_id, centro_registro_id):
    if perfil in PERFIS_GLOBAIS:
        return True

    return (
        centro_usuario_id is not None
        and centro_registro_id == centro_usuario_id
    )


def pode_alterar_registro(
    perfil,
    usuario_id,
    centro_usuario_id,
    autor_id,
    centro_registro_id,
):
    if perfil in PERFIS_GLOBAIS:
        return True

    if perfil == "intermediario":
        return (
            centro_usuario_id is not None
            and centro_registro_id == centro_usuario_id
        )

    if perfil == "basico":
        return usuario_id is not None and autor_id == usuario_id

    return False


def pode_excluir_registro(
    perfil,
    usuario_id,
    centro_usuario_id,
    autor_id,
    centro_registro_id,
):
    return pode_alterar_registro(
        perfil,
        usuario_id,
        centro_usuario_id,
        autor_id,
        centro_registro_id,
    )
