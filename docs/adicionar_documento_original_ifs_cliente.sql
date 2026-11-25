-- Adiciona o PDF original enviado pelo cliente às IFS já implantadas.
-- Script idempotente: pode ser executado novamente sem duplicar estruturas.

CREATE TABLE IF NOT EXISTS ifs_cliente_documentos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    inspecao_id INT NOT NULL,
    tipo VARCHAR(40) NOT NULL DEFAULT 'original_cliente',
    nome_original VARCHAR(255) NOT NULL,
    nome_armazenado VARCHAR(255) NOT NULL,
    mime_type VARCHAR(120) NOT NULL DEFAULT 'application/pdf',
    tamanho_bytes BIGINT NOT NULL,
    hash_sha256 CHAR(64) NOT NULL,
    criado_por INT NOT NULL,
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ifs_cliente_documento (inspecao_id, tipo, ativo),
    CONSTRAINT fk_ifs_cliente_doc_inspecao FOREIGN KEY (inspecao_id)
        REFERENCES ifs_cliente_inspecoes(id) ON DELETE CASCADE,
    CONSTRAINT fk_ifs_cliente_doc_usuario FOREIGN KEY (criado_por)
        REFERENCES usuarios(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
