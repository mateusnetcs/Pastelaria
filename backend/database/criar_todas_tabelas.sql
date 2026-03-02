-- ============================================
-- Script Completo para Criar Todas as Tabelas
-- Banco: pastelaria
-- Senha: 20220015779Ma@
-- ============================================

-- Criar banco de dados (caso não exista)
CREATE DATABASE IF NOT EXISTS pastelaria CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE pastelaria;

-- ============================================
-- TABELA: produtos
-- ============================================
CREATE TABLE IF NOT EXISTS produtos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    preco DECIMAL(10, 2) NOT NULL,
    quantidade INT NOT NULL DEFAULT 0,
    categoria VARCHAR(50) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    imagem_url VARCHAR(500),
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_categoria (categoria),
    INDEX idx_tipo (tipo),
    INDEX idx_nome (nome),
    INDEX idx_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- TABELA: usuarios
-- ============================================
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    senha VARCHAR(255),
    telefone VARCHAR(20),
    data_nascimento DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_telefone (telefone)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Adicionar campo data_nascimento se não existir
SET @col_data_exists = 0;
SELECT COUNT(*) INTO @col_data_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'pastelaria' 
AND TABLE_NAME = 'usuarios' 
AND COLUMN_NAME = 'data_nascimento';

SET @query_data = IF(@col_data_exists = 0,
    'ALTER TABLE usuarios ADD COLUMN data_nascimento DATE AFTER telefone',
    'SELECT "Coluna data_nascimento já existe" as status');
PREPARE stmt_data FROM @query_data;
EXECUTE stmt_data;
DEALLOCATE PREPARE stmt_data;

-- Adicionar índice idx_telefone se não existir
SET @idx_tel_exists = 0;
SELECT COUNT(*) INTO @idx_tel_exists 
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'pastelaria' 
AND TABLE_NAME = 'usuarios' 
AND INDEX_NAME = 'idx_telefone';

SET @query_idx_tel = IF(@idx_tel_exists = 0,
    'ALTER TABLE usuarios ADD INDEX idx_telefone (telefone)',
    'SELECT "Índice idx_telefone já existe" as status');
PREPARE stmt_idx_tel FROM @query_idx_tel;
EXECUTE stmt_idx_tel;
DEALLOCATE PREPARE stmt_idx_tel;

-- ============================================
-- TABELA: pedidos
-- ============================================
CREATE TABLE IF NOT EXISTS pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_id INT,
    cliente_nome VARCHAR(255),
    cliente_telefone VARCHAR(20),
    cliente_whatsapp VARCHAR(20),
    total DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pendente',
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_cliente_id (cliente_id),
    INDEX idx_cliente_whatsapp (cliente_whatsapp),
    FOREIGN KEY (cliente_id) REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Adicionar campo cliente_id se não existir
SET @col_cliente_exists = 0;
SELECT COUNT(*) INTO @col_cliente_exists 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'pastelaria' 
AND TABLE_NAME = 'pedidos' 
AND COLUMN_NAME = 'cliente_id';

SET @query_cliente = IF(@col_cliente_exists = 0,
    'ALTER TABLE pedidos ADD COLUMN cliente_id INT AFTER id, ADD FOREIGN KEY (cliente_id) REFERENCES usuarios(id) ON DELETE SET NULL',
    'SELECT "Coluna cliente_id já existe" as status');
PREPARE stmt_cliente FROM @query_cliente;
EXECUTE stmt_cliente;
DEALLOCATE PREPARE stmt_cliente;

-- ============================================
-- TABELA: pedido_itens
-- ============================================
CREATE TABLE IF NOT EXISTS pedido_itens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    produto_id INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    FOREIGN KEY (produto_id) REFERENCES produtos(id),
    INDEX idx_pedido_id (pedido_id),
    INDEX idx_produto_id (produto_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- INSERIR PRODUTOS INICIAIS (se não existirem)
-- ============================================
INSERT IGNORE INTO produtos (nome, descricao, preco, quantidade, categoria, tipo, imagem_url) VALUES
-- SALGADOS CLÁSSICOS
('Pastel de Camarão', 'Camarões frescos refogados com cebola, pimentão e temperos especiais.', 16.00, 30, 'Salgado', 'Clássico', 'https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?q=80&w=600&auto=format&fit=crop'),
('Pastel de Frango Grelhado', 'Frango grelhado desfiado com requeijão cremoso e ervas finas.', 13.00, 45, 'Salgado', 'Clássico', 'https://images.unsplash.com/photo-1604503468506-a8da13d82791?q=80&w=600&auto=format&fit=crop'),
('Pastel de Atum', 'Atum sólido com cebola, azeitona e um toque de limão.', 12.00, 35, 'Salgado', 'Clássico', 'https://images.unsplash.com/photo-1542838132-92c53300491e?q=80&w=600&auto=format&fit=crop'),
('Pastel de Ricota', 'Ricota fresca com espinafre refogado e noz-moscada.', 11.00, 40, 'Salgado', 'Clássico', 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?q=80&w=600&auto=format&fit=crop'),

-- SALGADOS ESPECIAIS
('Pastel de Costela', 'Costela bovina desfiada com cebola caramelizada e molho barbecue.', 18.00, 25, 'Salgado', 'Especial', 'https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?q=80&w=600&auto=format&fit=crop'),
('Pastel de Queijo Brie', 'Queijo Brie derretido com mel e nozes picadas.', 17.00, 20, 'Salgado', 'Especial', 'https://images.unsplash.com/photo-1486297678162-eb2a19b0a32d?q=80&w=600&auto=format&fit=crop'),
('Pastel de Alho Poró', 'Alho poró refogado com creme de leite e queijo parmesão.', 14.00, 30, 'Salgado', 'Especial', 'https://images.unsplash.com/photo-1601050690597-df0568f70950?q=80&w=600&auto=format&fit=crop'),
('Pastel de Salmão', 'Salmão defumado com cream cheese e alcaparras.', 19.00, 15, 'Salgado', 'Especial', 'https://images.unsplash.com/photo-1519708227418-c8fd9a32b3a2?q=80&w=600&auto=format&fit=crop'),

-- DOCES
('Pastel de Nutella', 'Nutella cremosa com morangos frescos fatiados.', 16.00, 40, 'Doce', 'Clássico', 'https://images.unsplash.com/photo-1551024506-0bccd828d307?q=80&w=600&auto=format&fit=crop'),
('Pastel de Brigadeiro', 'Brigadeiro cremoso com granulado de chocolate.', 13.00, 50, 'Doce', 'Clássico', 'https://images.unsplash.com/photo-1606313564200-e75d5e30476c?q=80&w=600&auto=format&fit=crop'),
('Pastel de Doce de Leite com Banana', 'Doce de leite com banana caramelizada e canela.', 14.00, 35, 'Doce', 'Clássico', 'https://images.unsplash.com/photo-1621236378699-8597faf6a176?q=80&w=600&auto=format&fit=crop'),
('Pastel de Prestígio', 'Coco ralado com chocolate ao leite derretido.', 15.00, 38, 'Doce', 'Clássico', 'https://images.unsplash.com/photo-1571875257727-256c39da42af?q=80&w=600&auto=format&fit=crop'),

-- BEBIDAS
('Água Mineral', 'Água mineral natural ou com gás. (Garrafa 500ml).', 3.00, 150, 'Bebida', 'Clássico', 'https://images.unsplash.com/photo-1523362628745-0c100150b504?q=80&w=600&auto=format&fit=crop'),
('Suco de Maracujá', 'Suco natural de maracujá, doce e refrescante. (Copo 400ml).', 9.00, 55, 'Bebida', 'Clássico', 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?q=80&w=600&auto=format&fit=crop'),
('Café Expresso', 'Café expresso forte e encorpado. (Xícara 50ml).', 4.00, 80, 'Bebida', 'Clássico', 'https://images.unsplash.com/photo-1517487881594-2787fef5ebf7?q=80&w=600&auto=format&fit=crop'),
('Chá Gelado', 'Chá gelado de pêssego ou limão. (Copo 500ml).', 5.00, 60, 'Bebida', 'Clássico', 'https://images.unsplash.com/photo-1556679343-c7306c1976bc?q=80&w=600&auto=format&fit=crop');

-- ============================================
-- VERIFICAR TABELAS CRIADAS
-- ============================================
SELECT 'Tabelas criadas/atualizadas com sucesso!' as status;
SELECT TABLE_NAME as 'Tabela Criada' 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'pastelaria' 
ORDER BY TABLE_NAME;
