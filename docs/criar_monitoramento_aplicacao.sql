-- Monitoramento técnico e de acessos do TrackPlan.
-- Execute no schema correto. O script não altera registros existentes.

CREATE TABLE IF NOT EXISTS aplicacao_sessoes (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    token_sessao CHAR(64) NOT NULL,
    usuario_id INT NULL,
    login_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultima_atividade DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    logout_em DATETIME NULL,
    motivo_encerramento VARCHAR(40) NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(500) NULL,
    dispositivo VARCHAR(40) NULL,
    navegador VARCHAR(60) NULL,
    sistema_operacional VARCHAR(60) NULL,
    ultimo_endpoint VARCHAR(180) NULL,
    ultima_rota VARCHAR(255) NULL,
    total_requisicoes INT NOT NULL DEFAULT 0,
    tempo_total_ms BIGINT NOT NULL DEFAULT 0,
    ultimo_status_http SMALLINT NULL,
    UNIQUE KEY uq_aplicacao_sessao_token (token_sessao),
    KEY idx_aplicacao_sessao_atividade (ultima_atividade),
    KEY idx_aplicacao_sessao_usuario (usuario_id, login_em),
    CONSTRAINT fk_aplicacao_sessao_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS aplicacao_erros (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    codigo_correlacao CHAR(12) NOT NULL,
    token_sessao CHAR(64) NULL,
    usuario_id INT NULL,
    endpoint VARCHAR(180) NULL,
    rota VARCHAR(255) NULL,
    metodo VARCHAR(10) NULL,
    tipo_erro VARCHAR(120) NOT NULL,
    mensagem_resumida VARCHAR(500) NULL,
    ocorrido_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_aplicacao_erro_codigo (codigo_correlacao),
    KEY idx_aplicacao_erro_data (ocorrido_em),
    KEY idx_aplicacao_erro_usuario (usuario_id, ocorrido_em),
    CONSTRAINT fk_aplicacao_erro_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS aplicacao_tentativas_login (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    identificador_hash CHAR(64) NOT NULL,
    identificador_mascarado VARCHAR(180) NOT NULL,
    sucesso TINYINT(1) NOT NULL DEFAULT 0,
    motivo VARCHAR(100) NOT NULL,
    ip_address VARCHAR(45) NULL,
    user_agent VARCHAR(500) NULL,
    ocorrido_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_aplicacao_login_data (ocorrido_em),
    KEY idx_aplicacao_login_sucesso (sucesso, ocorrido_em)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SELECT 'Estruturas de monitoramento verificadas com sucesso.' AS informacao;
