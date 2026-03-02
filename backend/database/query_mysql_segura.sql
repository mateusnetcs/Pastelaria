-- Query MySQL Segura para n8n
-- Esta query sempre retorna resultados, mesmo se a mensagem estiver vazia

-- VERSÃO 1: Sempre retorna produtos (para teste)
SELECT 
    nome,
    descricao,
    preco,
    quantidade,
    categoria,
    tipo
FROM produtos
WHERE ativo = TRUE
ORDER BY categoria, nome
LIMIT 10;

-- VERSÃO 2: Com filtro, mas sempre retorna algo se não encontrar
-- (Descomente esta e comente a versão 1 quando quiser usar filtros)

/*
SELECT 
    nome,
    descricao,
    preco,
    quantidade,
    categoria,
    tipo
FROM produtos
WHERE ativo = TRUE
  AND (
    '{{ $json.menssage }}' = '' 
    OR '{{ $json.menssage }}' IS NULL
    OR LOWER(nome) LIKE LOWER(CONCAT('%', '{{ $json.menssage }}', '%'))
    OR LOWER(descricao) LIKE LOWER(CONCAT('%', '{{ $json.menssage }}', '%'))
    OR LOWER(categoria) LIKE LOWER(CONCAT('%', '{{ $json.menssage }}', '%'))
  )
ORDER BY categoria, nome
LIMIT 10;
*/
