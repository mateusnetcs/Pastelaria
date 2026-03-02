-- Script para adicionar campo data_nascimento na tabela usuarios
-- Execute este script se o campo ainda não existir

USE pastelaria;

-- Verificar se a coluna já existe antes de adicionar
SET @col_exists = 0;
SELECT COUNT(*) INTO @col_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'pastelaria' 
AND TABLE_NAME = 'usuarios' 
AND COLUMN_NAME = 'data_nascimento';

SET @query = IF(@col_exists = 0,
    'ALTER TABLE usuarios ADD COLUMN data_nascimento DATE AFTER telefone',
    'SELECT "Coluna data_nascimento já existe" as status');
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Adicionar índice para busca por telefone/WhatsApp (se não existir)
SET @idx_exists = 0;
SELECT COUNT(*) INTO @idx_exists 
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'pastelaria' 
AND TABLE_NAME = 'usuarios' 
AND INDEX_NAME = 'idx_telefone';

SET @idx_query = IF(@idx_exists = 0,
    'ALTER TABLE usuarios ADD INDEX idx_telefone (telefone)',
    'SELECT "Índice idx_telefone já existe" as status');
PREPARE idx_stmt FROM @idx_query;
EXECUTE idx_stmt;
DEALLOCATE PREPARE idx_stmt;

SELECT 'Campo data_nascimento adicionado com sucesso!' as status;
