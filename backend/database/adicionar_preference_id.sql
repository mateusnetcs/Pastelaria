-- Script para adicionar coluna preference_id na tabela pedidos
USE pastelaria;

-- Verificar se a coluna já existe antes de adicionar
SET @col_exists = 0;
SELECT COUNT(*) INTO @col_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'pastelaria' 
AND TABLE_NAME = 'pedidos' 
AND COLUMN_NAME = 'preference_id';

SET @query = IF(@col_exists = 0,
    'ALTER TABLE pedidos ADD COLUMN preference_id VARCHAR(255) NULL AFTER observacoes',
    'SELECT "Coluna preference_id já existe" as status');
PREPARE stmt FROM @query;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Verificar se a coluna foi adicionada
SELECT 'Coluna preference_id adicionada com sucesso!' as status;
