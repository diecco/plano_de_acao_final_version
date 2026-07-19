from flask import Blueprint, flash, jsonify, redirect, request, url_for

main_routes = Blueprint('main', __name__)

from app.views.agenda_ssma import register_agenda_ssma_routes
from app.views.apr import register_apr_routes
from app.views.auditoria_padrao import register_auditoria_padrao_routes
from app.views.autenticacao import register_autenticacao_routes
from app.views.centros_custos import register_centros_custos_routes
from app.views.cargos import register_cargos_routes
from app.views.funcoes import register_funcoes_routes
from app.views.horas_seguranca import register_horas_seguranca_routes
from app.views.ifs import register_ifs_routes
from app.views.instrutores import register_instrutores_routes
from app.views.matriz_capacitacao import register_matriz_capacitacao_routes
from app.views.melhorias import register_melhorias_routes
from app.views.origens import register_origens_routes
from app.views.pcpm_cadastros import register_pcpm_cadastros_routes
from app.views.pcpm_checklist import register_pcpm_checklist_routes
from app.views.pcpm_equipamentos import register_pcpm_equipamentos_routes
from app.views.pcpm_movimentacoes import register_pcpm_movimentacoes_routes
from app.views.plano_acao import register_plano_acao_routes
from app.views.procedimentos import register_procedimentos_routes
from app.views.recusa_tarefa import register_recusa_tarefa_routes
from app.views.reconhecimentos import register_reconhecimentos_routes
from app.views.setores import register_setores_routes
from app.views.superintendencias import register_superintendencias_routes
from app.views.tipos_documento import register_tipos_documento_routes
from app.views.treinamentos import register_treinamentos_routes
from app.views.usuarios import register_usuarios_routes

register_agenda_ssma_routes(main_routes)
register_apr_routes(main_routes)
register_auditoria_padrao_routes(main_routes)
register_autenticacao_routes(main_routes)
register_centros_custos_routes(main_routes)
register_superintendencias_routes(main_routes)
register_origens_routes(main_routes)
register_setores_routes(main_routes)
register_funcoes_routes(main_routes)
register_horas_seguranca_routes(main_routes)
register_ifs_routes(main_routes)
register_cargos_routes(main_routes)
register_tipos_documento_routes(main_routes)
register_instrutores_routes(main_routes)
register_matriz_capacitacao_routes(main_routes)
register_melhorias_routes(main_routes)
register_pcpm_cadastros_routes(main_routes)
register_pcpm_checklist_routes(main_routes)
register_pcpm_equipamentos_routes(main_routes)
register_pcpm_movimentacoes_routes(main_routes)
register_plano_acao_routes(main_routes)
register_procedimentos_routes(main_routes)
register_recusa_tarefa_routes(main_routes)
register_reconhecimentos_routes(main_routes)
register_treinamentos_routes(main_routes)
register_usuarios_routes(main_routes)


@main_routes.app_errorhandler(413)
def arquivo_muito_grande(_erro):
    mensagem = "O envio excede o limite máximo de 20 MB."
    if request.path.startswith('/api/'):
        return jsonify({'sucesso': False, 'mensagem': mensagem}), 413
    flash(mensagem, 'danger')
    return redirect(request.referrer or url_for('main.index'))
