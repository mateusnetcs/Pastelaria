-- Script para criar tabela de usuários e atualizar tabela de pedidos
USE pastelaria;

-- Criar tabela de usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    senha VARCHAR(255) NOT NULL,
    telefone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Atualizar tabela de pedidos para incluir cliente_id (se não existir)
-- Verificar se a coluna já existe antes de adicionar
SET @col_exists = 0;
SELECT COUNT(*) INTO @col_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'pastelaria' 
AND TABLE_NAME = 'pedidos' 
AND COLUMN_NAME = 'cliente_id';

SET @query = IF(@col_exists = 0,
    'ALTER TABLE pedidos ADD COLUMN cliente_id INT',
    'SELECT "Coluna cliente_id já existe" as status');
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Verificar se as tabelas foram criadas
SELECT 'Tabelas criadas com sucesso!' as status;
