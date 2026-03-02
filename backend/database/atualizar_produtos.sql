-- Script para atualizar produtos no banco de dados
-- Execute este script no MySQL para substituir os produtos antigos por novos

USE pastelaria;

-- Limpar produtos antigos (usando DELETE para evitar erro de foreign key)
DELETE FROM produtos;

-- Inserir NOVOS produtos do cardápio
INSERT INTO produtos (nome, descricao, preco, quantidade, categoria, tipo, imagem_url) VALUES
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

-- Verificar se os dados foram inseridos
SELECT COUNT(*) as total_produtos FROM produtos;
SELECT nome, preco, categoria, quantidade FROM produtos ORDER BY categoria, nome;
