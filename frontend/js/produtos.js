/**
 * Funções de Produtos
 * Gerencia carregamento e renderização de produtos
 */

async function carregarProdutos() {
    const container = document.getElementById('produtos-container');
    if (!container) return;
    
    container.innerHTML = '<div class="col-span-full text-center py-8"><i class="fas fa-spinner fa-spin text-4xl text-orange-600"></i><p class="mt-4 text-gray-600">Carregando produtos...</p></div>';
    
    try {
        console.log('Tentando carregar produtos de:', API_URL + '/produtos');
        const response = await fetch(`${API_URL}/produtos`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            mode: 'cors',
            cache: 'no-cache'
        });
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const data = await response.json();
        if (data.success && data.produtos) {
            produtos = data.produtos;
            renderizarProdutos();
        } else {
            throw new Error(data.error || 'Erro ao carregar produtos');
        }
    } catch (error) {
        console.error('Erro ao carregar produtos:', error);
        container.innerHTML = `
            <div class="col-span-full text-center py-8">
                <i class="fas fa-exclamation-triangle text-4xl text-red-500 mb-4"></i>
                <p class="text-red-600 font-bold mb-2">Erro ao carregar produtos</p>
                <p class="text-gray-600 text-sm mb-4">${error.message}</p>
                <button onclick="carregarProdutos()" class="bg-orange-600 text-white px-6 py-2 rounded-lg hover:bg-orange-700">
                    Tentar Novamente
                </button>
            </div>
        `;
    }
}

let categoriaFiltro = 'Todos';

function filtrarCategoria(cat) {
    categoriaFiltro = cat;
    renderizarProdutos();
}

function renderizarProdutos() {
    const container = document.getElementById('produtos-container');
    if (!container) return;
    
    if (!produtos || produtos.length === 0) {
        container.innerHTML = `
            <div class="col-span-full text-center py-8">
                <i class="fas fa-box-open text-4xl text-gray-400 mb-4"></i>
                <p class="text-gray-600">Nenhum produto encontrado no momento.</p>
            </div>
        `;
        return;
    }

    const catIcons = { 'Todos': 'fa-th-large', 'Salgados': 'fa-fire', 'Doces': 'fa-candy-cane', 'Bebidas': 'fa-glass-water' };
    const catColors = { 'Todos': 'gray', 'Salgados': 'orange', 'Doces': 'pink', 'Bebidas': 'blue' };
    const ordemCat = ['Salgados', 'Doces', 'Bebidas'];

    const categoriasExistentes = {};
    produtos.forEach(p => {
        const cat = p.categoria || 'Outros';
        if (!categoriasExistentes[cat]) categoriasExistentes[cat] = [];
        categoriasExistentes[cat].push(p);
    });
    const catKeys = [...ordemCat.filter(c => categoriasExistentes[c]), ...Object.keys(categoriasExistentes).filter(c => !ordemCat.includes(c))];
    const filtroTabs = ['Todos', ...catKeys];

    let html = `<div class="col-span-full flex gap-2 overflow-x-auto pb-2 scrollbar-hide -mx-1 px-1">`;
    filtroTabs.forEach(cat => {
        const ativo = categoriaFiltro === cat;
        const cor = catColors[cat] || 'gray';
        const icon = catIcons[cat] || 'fa-tag';
        const qtd = cat === 'Todos' ? produtos.length : (categoriasExistentes[cat] || []).length;
        if (ativo) {
            html += `<button onclick="filtrarCategoria('${cat}')" class="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap bg-orange-600 text-white shadow-md shadow-orange-200 transition-all">
                <i class="fas ${icon} text-xs"></i>${cat}<span class="bg-white/20 text-[10px] px-1.5 py-0.5 rounded-full">${qtd}</span></button>`;
        } else {
            html += `<button onclick="filtrarCategoria('${cat}')" class="flex items-center gap-1.5 px-4 py-2 rounded-full text-sm font-semibold whitespace-nowrap bg-white text-gray-600 border border-gray-200 hover:border-orange-300 hover:text-orange-600 transition-all">
                <i class="fas ${icon} text-xs text-${cor}-400"></i>${cat}<span class="text-[10px] text-gray-400">${qtd}</span></button>`;
        }
    });
    html += `</div>`;

    const produtosFiltrados = categoriaFiltro === 'Todos' ? produtos : produtos.filter(p => (p.categoria || 'Outros') === categoriaFiltro);

    const categoriasFiltradas = {};
    produtosFiltrados.forEach(p => {
        const cat = p.categoria || 'Outros';
        if (!categoriasFiltradas[cat]) categoriasFiltradas[cat] = [];
        categoriasFiltradas[cat].push(p);
    });
    const catKeysFiltradas = [...ordemCat.filter(c => categoriasFiltradas[c]), ...Object.keys(categoriasFiltradas).filter(c => !ordemCat.includes(c))];

    catKeysFiltradas.forEach(cat => {
        const cor = catColors[cat] || 'gray';
        const icon = catIcons[cat] || 'fa-tag';
        if (categoriaFiltro === 'Todos') {
            html += `
                <div class="col-span-full mt-4 mb-1">
                    <h3 class="text-lg md:text-xl font-bold text-gray-800 flex items-center gap-2">
                        <span class="w-7 h-7 md:w-8 md:h-8 rounded-full bg-${cor}-100 flex items-center justify-center">
                            <i class="fas ${icon} text-${cor}-600 text-xs md:text-sm"></i>
                        </span>
                        ${cat}
                        <span class="text-sm font-normal text-gray-400">(${categoriasFiltradas[cat].length})</span>
                    </h3>
                </div>
            `;
        }

        categoriasFiltradas[cat].forEach(produto => {
            const nome = (produto.nome || '').replace(/'/g, "&#39;").replace(/"/g, "&quot;");
            const descricao = (produto.descricao || '').replace(/'/g, "&#39;").replace(/"/g, "&quot;");
            const preco = parseFloat(produto.preco || 0).toFixed(2).replace('.', ',');
            const imagem = produto.imagem_url || '';
            const produtoJson = JSON.stringify(produto).replace(/'/g, "&#39;").replace(/"/g, "&quot;");
            const placeholderIcon = `<div class="w-full h-full bg-gradient-to-br from-orange-50 to-orange-100 flex items-center justify-center"><i class="fas fa-utensils text-orange-300 text-2xl md:text-3xl"></i></div>`;

            html += `
                <div class="produto-card bg-white rounded-xl md:rounded-2xl overflow-hidden shadow-sm md:shadow-lg border border-gray-100 cursor-pointer hover:shadow-md transition-all active:scale-[0.98]" onclick="abrirDetalheProduto(${produto.id})">
                    <div class="flex md:flex-col">
                        <div class="w-24 h-24 md:w-full md:h-48 flex-shrink-0 bg-gray-100 overflow-hidden">
                            ${imagem ? `<img src="${imagem}" alt="${nome}" class="w-full h-full object-cover">` : placeholderIcon}
                        </div>
                        <div class="flex-1 p-3 md:p-5 flex flex-col justify-center md:justify-start min-w-0">
                            <h4 class="font-bold text-gray-800 text-sm md:text-lg truncate md:whitespace-normal md:mb-1">${nome}</h4>
                            <p class="text-gray-400 text-xs md:text-sm truncate md:whitespace-normal md:line-clamp-2 md:mb-4">${descricao}</p>
                            <div class="flex justify-between items-center mt-1.5 md:mt-auto">
                                <span class="text-base md:text-xl font-bold text-orange-600">R$ ${preco}</span>
                                <button onclick="event.stopPropagation(); adicionarAoCarrinho(${produtoJson})" class="bg-orange-600 text-white px-3 py-1.5 md:px-4 md:py-2 rounded-lg text-xs md:text-sm font-bold hover:bg-orange-700 transition active:scale-95">
                                    <i class="fas fa-plus md:hidden mr-1"></i><span class="hidden md:inline">Adicionar</span><span class="md:hidden">Adicionar</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
    });

    container.innerHTML = html;
}

function abrirDetalheProduto(produtoId) {
    const produto = produtos.find(p => p.id === produtoId);
    if (!produto) return;

    const nome = produto.nome || '';
    const descricao = produto.descricao || 'Sem descrição disponível';
    const preco = parseFloat(produto.preco || 0).toFixed(2).replace('.', ',');
    const categoria = produto.categoria || 'Geral';
    const imagem = produto.imagem_url || '';
    const produtoJson = JSON.stringify(produto).replace(/'/g, "&#39;").replace(/"/g, "&quot;");

    const catColors = { 'Salgados': 'orange', 'Doces': 'pink', 'Bebidas': 'blue' };
    const cor = catColors[categoria] || 'gray';

    const existente = document.getElementById('modal-detalhe-produto');
    if (existente) existente.remove();

    const modal = document.createElement('div');
    modal.id = 'modal-detalhe-produto';
    modal.className = 'fixed inset-0 bg-black/60 z-50 flex items-end sm:items-center justify-center';
    modal.onclick = (e) => { if (e.target === modal) fecharDetalheProduto(); };

    modal.innerHTML = `
        <div class="bg-white w-full sm:max-w-md sm:rounded-2xl rounded-t-3xl max-h-[90vh] overflow-y-auto animate-slide-up shadow-2xl">
            <div class="relative">
                ${imagem
                    ? `<img src="${imagem}" alt="${nome}" class="w-full h-56 sm:h-64 object-cover" onerror="this.parentElement.innerHTML='<div class=\\'w-full h-56 sm:h-64 bg-gradient-to-br from-orange-50 to-orange-100 flex items-center justify-center\\'><i class=\\'fas fa-utensils text-orange-300 text-5xl\\'></i></div><button onclick=\\'fecharDetalheProduto()\\' class=\\'absolute top-4 right-4 w-9 h-9 bg-white/90 rounded-full flex items-center justify-center shadow-lg text-gray-600\\'><i class=\\'fas fa-times\\'></i></button>'">`
                    : `<div class="w-full h-56 sm:h-64 bg-gradient-to-br from-orange-50 to-orange-100 flex items-center justify-center"><i class="fas fa-utensils text-orange-300 text-5xl"></i></div>`
                }
                <button onclick="fecharDetalheProduto()" class="absolute top-4 right-4 w-9 h-9 bg-white/90 backdrop-blur rounded-full flex items-center justify-center shadow-lg text-gray-600 hover:text-gray-900 transition">
                    <i class="fas fa-times"></i>
                </button>
                <span class="absolute top-4 left-4 bg-${cor}-100 text-${cor}-700 text-xs font-bold px-3 py-1 rounded-full">${categoria}</span>
            </div>

            <div class="p-6">
                <h2 class="text-2xl font-bold text-gray-900 mb-2">${nome}</h2>
                <p class="text-gray-500 leading-relaxed mb-6">${descricao}</p>

                <div class="flex items-center justify-between bg-orange-50 rounded-xl p-4">
                    <div>
                        <span class="text-sm text-gray-500">Preço</span>
                        <p class="text-2xl font-bold text-orange-600">R$ ${preco}</p>
                    </div>
                    <button onclick="adicionarAoCarrinho(${produtoJson}); fecharDetalheProduto();" class="bg-orange-600 text-white px-6 py-3 rounded-xl font-bold hover:bg-orange-700 transition active:scale-95 shadow-lg shadow-orange-200">
                        <i class="fas fa-cart-plus mr-2"></i>Adicionar
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => modal.querySelector('.bg-white').style.opacity = '1');
}

function fecharDetalheProduto() {
    const modal = document.getElementById('modal-detalhe-produto');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
}
