-- Script SQL para MySQL Local - Pastelaria Delícia
-- Execute este script no seu MySQL Workbench ou via linha de comando

-- Criar banco de dados (caso não exista)
CREATE DATABASE IF NOT EXISTS pastelaria CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE pastelaria;

-- Criar tabela de produtos
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
    INDEX idx_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Limpar dados existentes (opcional - descomente se quiser resetar)
-- TRUNCATE TABLE produtos;

-- Inserir produtos do cardápio
INSERT INTO produtos (nome, descricao, preco, quantidade, categoria, tipo, imagem_url) VALUES
-- SALGADOS CLÁSSICOS
('Carne Tradicional', 'Carne moída temperada com especiarias da casa e azeitona.', 10.00, 50, 'Salgado', 'Clássico', 'https://images.unsplash.com/photo-1644610266050-70597395455c?q=80&w=600&auto=format&fit=crop'),
('Queijo Especial', 'Muçarela derretida de alta qualidade com um toque de orégano.', 10.00, 45, 'Salgado', 'Clássico', 'https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?q=80&w=600&auto=format&fit=crop'),
('Frango com Catupiry', 'Peito de frango desfiado e temperado com o legítimo Catupiry.', 12.00, 40, 'Salgado', 'Clássico', 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?q=80&w=600&auto=format&fit=crop'),
('Pizza', 'Presunto, muçarela, tomate picado e bastante orégano.', 11.00, 35, 'Salgado', 'Clássico', 'https://images.unsplash.com/photo-1541544741938-0af808891cc5?q=80&w=600&auto=format&fit=crop'),

-- SALGADOS ESPECIAIS
('Carne Seca com Abóbora', 'Carne seca desfiada com purê de abóbora cabotiá temperado.', 15.00, 30, 'Salgado', 'Especial', 'https://images.unsplash.com/photo-1512152272829-e3139592d56f?q=80&w=600&auto=format&fit=crop'),
('Palmito Gourmet', 'Palmito macio picado com molho branco e tempero verde.', 14.00, 25, 'Salgado', 'Especial', 'https://images.unsplash.com/photo-1627308595229-7830a5c91f9f?q=80&w=600&auto=format&fit=crop'),
('Calabresa com Cebola', 'Linguiça calabresa moída com cebola e um toque de pimenta.', 11.00, 40, 'Salgado', 'Clássico', 'https://images.unsplash.com/photo-1604382354936-07c5d9983bd3?q=80&w=600&auto=format&fit=crop'),
('Bacalhau Premium', 'O verdadeiro bacalhau do porto desfiado com azeitona preta.', 18.00, 20, 'Salgado', 'Especial', 'https://images.unsplash.com/photo-1593504049359-74330189a345?q=80&w=600&auto=format&fit=crop'),

-- DOCES
('Chocolate com Morango', 'Chocolate ao leite derretido com fatias de morango fresco.', 15.00, 30, 'Doce', 'Clássico', 'https://images.unsplash.com/photo-1551024506-0bccd828d307?q=80&w=600&auto=format&fit=crop'),
('Doce de Leite com Coco', 'Doce de leite cremoso salpicado com coco ralado fino.', 12.00, 35, 'Doce', 'Clássico', 'https://images.unsplash.com/photo-1587049633562-ad3002f02574?q=80&w=600&auto=format&fit=crop'),
('Romeu e Julieta', 'A clássica combinação de goiabada cascão com queijo minas.', 12.00, 40, 'Doce', 'Clássico', 'https://images.unsplash.com/photo-1590089415225-401ed6f9db8e?q=80&w=600&auto=format&fit=crop'),
('Banana com Canela', 'Bananas caramelizadas com açúcar e um toque de canela.', 11.00, 35, 'Doce', 'Clássico', 'https://images.unsplash.com/photo-1621236378699-8597faf6a176?q=80&w=600&auto=format&fit=crop'),

-- BEBIDAS
('Refrigerante Lata', 'Coca-Cola, Guaraná Antártica ou Fanta (Lata 350ml).', 6.00, 100, 'Bebida', 'Clássico', 'https://images.unsplash.com/photo-1622483767028-3f66f32aef97?q=80&w=600&auto=format&fit=crop'),
('Suco de Laranja', 'Suco 100% natural, espremido na hora. (Copo 400ml).', 8.00, 60, 'Bebida', 'Clássico', 'https://images.unsplash.com/photo-1595981267035-21045a2d59f8?q=80&w=600&auto=format&fit=crop'),
('Caldo de Cana', 'Geladinho, com ou sem limão. O par perfeito do pastel!', 7.00, 50, 'Bebida', 'Clássico', 'https://images.unsplash.com/photo-1534353436294-0dbd4bdac845?q=80&w=600&auto=format&fit=crop');

-- Criar tabela de pedidos (opcional, para futuras funcionalidades)
CREATE TABLE IF NOT EXISTS pedidos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    cliente_nome VARCHAR(255),
    cliente_telefone VARCHAR(20),
    cliente_whatsapp VARCHAR(20),
    total DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pendente',
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_cliente_whatsapp (cliente_whatsapp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Criar tabela de itens do pedido (opcional)
CREATE TABLE IF NOT EXISTS pedido_itens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id INT NOT NULL,
    produto_id INT NOT NULL,
    quantidade INT NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (pedido_id) REFERENCES pedidos(id) ON DELETE CASCADE,
    FOREIGN KEY (produto_id) REFERENCES produtos(id),
    INDEX idx_pedido_id (pedido_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verificar se os dados foram inseridos
SELECT COUNT(*) as total_produtos FROM produtos;
SELECT nome, preco, categoria, quantidade FROM produtos ORDER BY categoria, nome;
