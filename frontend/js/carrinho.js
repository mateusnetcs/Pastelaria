/**
 * Funções do Carrinho de Compras
 * Gerencia adição, remoção e atualização de itens
 */

/**
 * Adiciona um produto ao carrinho
 * @param {Object} produto - Objeto do produto
 */
function adicionarAoCarrinho(produto) {
    const itemExistente = carrinho.find(item => item.produto_id === produto.id);
    
    if (itemExistente) {
        itemExistente.quantidade++;
        showToast('info', 'Quantidade atualizada!', `${produto.nome} agora tem ${itemExistente.quantidade} unidade(s) no carrinho`);
    } else {
        carrinho.push({
            produto_id: produto.id,
            nome: produto.nome,
            preco: parseFloat(produto.preco),
            quantidade: 1
        });
        showToast('success', 'Produto adicionado!', `${produto.nome} foi adicionado ao carrinho`);
    }
    
    salvarCarrinho();
    atualizarCarrinho();
}

/**
 * Remove um produto do carrinho
 * @param {number} produtoId - ID do produto
 */
function removerDoCarrinho(produtoId) {
    carrinho = carrinho.filter(item => item.produto_id !== produtoId);
    salvarCarrinho();
    atualizarCarrinho();
}

/**
 * Atualiza a quantidade de um item no carrinho
 * @param {number} produtoId - ID do produto
 * @param {number} quantidade - Nova quantidade
 */
function atualizarQuantidade(produtoId, quantidade) {
    const item = carrinho.find(item => item.produto_id === produtoId);
    
    if (item) {
        if (quantidade <= 0) {
            removerDoCarrinho(produtoId);
        } else {
            item.quantidade = quantidade;
            salvarCarrinho();
            atualizarCarrinho();
        }
    }
}

/**
 * Salva o carrinho no localStorage e atualiza o contador
 */
function salvarCarrinho() {
    localStorage.setItem('carrinho', JSON.stringify(carrinho));
    const total = carrinho.reduce((sum, item) => sum + item.quantidade, 0);
    const cartCount = document.getElementById('cart-count');
    const cartCountMobile = document.getElementById('cart-count-mobile');
    if (cartCount) cartCount.textContent = total;
    if (cartCountMobile) cartCountMobile.textContent = total;
}

/**
 * Atualiza a exibição do carrinho na interface
 */
function atualizarCarrinho() {
    const container = document.getElementById('carrinho-items');
    if (!container) return;
    
    const total = carrinho.reduce((sum, item) => sum + (item.preco * item.quantidade), 0);
    
    if (carrinho.length === 0) {
        container.innerHTML = '<p class="text-gray-500">Carrinho vazio</p>';
        const btnFinalizar = document.getElementById('btn-finalizar');
        if (btnFinalizar) btnFinalizar.disabled = true;
    } else {
        container.innerHTML = carrinho.map(item => `
            <div class="flex justify-between items-center mb-4 p-3 bg-gray-50 rounded">
                <div class="flex-1">
                    <p class="font-bold">${item.nome}</p>
                    <p class="text-sm text-gray-600">R$ ${item.preco.toFixed(2)}</p>
                </div>
                <div class="flex items-center space-x-2">
                    <button onclick="atualizarQuantidade(${item.produto_id}, ${item.quantidade - 1})" class="bg-gray-200 px-2 py-1 rounded">-</button>
                    <span>${item.quantidade}</span>
                    <button onclick="atualizarQuantidade(${item.produto_id}, ${item.quantidade + 1})" class="bg-gray-200 px-2 py-1 rounded">+</button>
                    <button onclick="removerDoCarrinho(${item.produto_id})" class="text-red-600 ml-2"><i class="fas fa-trash"></i></button>
                </div>
            </div>
        `).join('');
        
        const btnFinalizar = document.getElementById('btn-finalizar');
        if (btnFinalizar) btnFinalizar.disabled = false;
    }
    
    const carrinhoTotal = document.getElementById('carrinho-total');
    if (carrinhoTotal) {
        carrinhoTotal.textContent = `R$ ${total.toFixed(2)}`;
    }
    
    salvarCarrinho();
}

/**
 * Abre/fecha o carrinho lateral
 */
function toggleCarrinho() {
    const sidebar = document.getElementById('carrinho-sidebar');
    if (sidebar) {
        sidebar.classList.toggle('translate-x-full');
    }
}
