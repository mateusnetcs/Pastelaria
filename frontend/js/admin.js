/**
 * Script de Administração
 * Gerencia dashboard Kanban e funcionalidades admin
 */

// Variáveis globais
let todosPedidos = [];
let pedidosAnteriores = [];
let pedidoArrastado = null;
let audioNotificacao = null;

let todosProdutos = [];
let produtoExcluirId = null;
let pedidoDetalheAtual = null;
const pedidosJaImpressos = new Set();

// Inicialização movida para admin.html (controle de login)

/**
 * Navegação do menu
 */
const SECTIONS = ['dashboard-content', 'pedidos-content', 'produtos-content', 'clientes-content', 'relatorios-content'];

function esconderTodasSecoes() {
    SECTIONS.forEach(id => { const el = document.getElementById(id); if (el) el.classList.add('hidden'); });
}

function mostrarDashboard() {
    esconderTodasSecoes();
    document.getElementById('dashboard-content').classList.remove('hidden');
    document.getElementById('page-title').textContent = 'Dashboard';
    atualizarMenuAtivo('dashboard');
}

function mostrarPedidos() {
    esconderTodasSecoes();
    document.getElementById('pedidos-content').classList.remove('hidden');
    document.getElementById('page-title').textContent = 'Pedidos';
    atualizarMenuAtivo('pedidos');
}

// ========= DETALHE DO PEDIDO =========

async function abrirDetalhePedido(pedidoId) {
    try {
        const resp = await fetch(`/api/admin/pedido/${pedidoId}/detalhes`, { headers: adminHeaders() });
        const data = await resp.json();
        if (!data.success) { showToast('Erro ao carregar pedido', 'error'); return; }

        pedidoDetalheAtual = { pedido: data.pedido, itens: data.itens };
        const p = data.pedido;
        const itens = data.itens;

        document.getElementById('detalhe-titulo').textContent = `Pedido #${p.id}`;

        const statusColors = {
            'pagamento_pendente': 'bg-yellow-100 text-yellow-800',
            'confirmado': 'bg-green-100 text-green-800',
            'em_preparacao': 'bg-blue-100 text-blue-800',
            'pronto': 'bg-purple-100 text-purple-800',
            'entregue': 'bg-emerald-100 text-emerald-800'
        };
        const statusLabels = {
            'pagamento_pendente': 'Pagamento Pendente',
            'confirmado': 'Confirmado',
            'em_preparacao': 'Em Preparação',
            'pronto': 'Pronto para Entrega',
            'entregue': 'Entregue/Retirado'
        };

        const dataPedido = p.created_at ? new Date(p.created_at).toLocaleString('pt-BR') : '-';

        let itensHtml = itens.map(it => `
            <div class="flex justify-between items-center py-2 border-b border-gray-100 last:border-0">
                <div class="flex-1">
                    <span class="font-medium text-gray-800">${it.produto_nome}</span>
                    <span class="text-gray-500 text-sm ml-2">x${it.quantidade}</span>
                </div>
                <span class="font-semibold text-gray-700">R$ ${it.subtotal.toFixed(2)}</span>
            </div>
        `).join('');

        document.getElementById('detalhe-body').innerHTML = `
            <div class="flex items-center gap-3 mb-1">
                <span class="px-3 py-1 rounded-full text-xs font-semibold ${statusColors[p.status] || 'bg-gray-100 text-gray-800'}">
                    ${statusLabels[p.status] || p.status}
                </span>
                <span class="text-sm text-gray-500">${dataPedido}</span>
            </div>

            <div class="bg-gray-50 rounded-xl p-4 space-y-1">
                <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">Cliente</h3>
                <p class="font-semibold text-gray-800"><i class="fas fa-user mr-2 text-orange-400"></i>${p.cliente_nome || 'N/A'}</p>
                <p class="text-sm text-gray-600"><i class="fas fa-phone mr-2 text-orange-400"></i>${formatarTelefone(p.cliente_telefone)}</p>
                <p class="text-sm text-gray-600"><i class="fas fa-envelope mr-2 text-orange-400"></i>${p.cliente_email || 'N/A'}</p>
            </div>

            <div class="bg-gray-50 rounded-xl p-4">
                <h3 class="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Itens do Pedido</h3>
                ${itensHtml}
            </div>

            ${p.observacoes ? (() => {
                let obsHtml = '';
                try {
                    const obs = typeof p.observacoes === 'string' ? JSON.parse(p.observacoes) : p.observacoes;
                    if (obs && typeof obs === 'object') {
                        const tipo = obs.tipo_entrega || '';
                        if (tipo === 'entrega' || obs.rua) {
                            const endereco = [obs.rua, obs.numero].filter(Boolean).join(', ');
                            const bairro = obs.bairro || '';
                            const compl = obs.complemento || '';
                            obsHtml = `
                                <div class="bg-blue-50 rounded-xl p-4">
                                    <h3 class="text-sm font-semibold text-blue-700 uppercase tracking-wide mb-2"><i class="fas fa-truck mr-1"></i>Entrega</h3>
                                    <p class="text-sm text-blue-800 font-medium">${endereco}</p>
                                    ${bairro ? `<p class="text-sm text-blue-700">${bairro}</p>` : ''}
                                    ${compl ? `<p class="text-sm text-blue-600 italic">${compl}</p>` : ''}
                                </div>`;
                        } else if (tipo === 'retirada' || obs.retirada_local) {
                            obsHtml = `
                                <div class="bg-green-50 rounded-xl p-4">
                                    <h3 class="text-sm font-semibold text-green-700 uppercase tracking-wide"><i class="fas fa-store mr-1"></i>Retirada no Local</h3>
                                </div>`;
                        } else {
                            obsHtml = `<div class="bg-amber-50 rounded-xl p-4"><h3 class="text-sm font-semibold text-amber-700 uppercase tracking-wide mb-1">Observações</h3><p class="text-sm text-amber-800">${JSON.stringify(obs)}</p></div>`;
                        }
                    } else {
                        obsHtml = `<div class="bg-amber-50 rounded-xl p-4"><h3 class="text-sm font-semibold text-amber-700 uppercase tracking-wide mb-1">Observações</h3><p class="text-sm text-amber-800">${p.observacoes}</p></div>`;
                    }
                } catch(e) {
                    obsHtml = `<div class="bg-amber-50 rounded-xl p-4"><h3 class="text-sm font-semibold text-amber-700 uppercase tracking-wide mb-1">Observações</h3><p class="text-sm text-amber-800">${p.observacoes}</p></div>`;
                }
                return obsHtml;
            })() : ''}

            <div class="flex justify-between items-center bg-orange-50 rounded-xl p-4">
                <span class="font-semibold text-gray-700 text-lg">Total</span>
                <span class="font-bold text-orange-600 text-2xl">R$ ${p.total.toFixed(2)}</span>
            </div>
        `;

        document.getElementById('modal-pedido-detalhe').classList.remove('hidden');
    } catch (err) {
        console.error(err);
        showToast('Erro ao carregar detalhes do pedido', 'error');
    }
}

function fecharDetalhePedido() {
    document.getElementById('modal-pedido-detalhe').classList.add('hidden');
    pedidoDetalheAtual = null;
}


async function imprimirCupom() {
    if (!pedidoDetalheAtual) return;
    await imprimirCupomSilencioso(pedidoDetalheAtual.pedido.id);
}

async function imprimirCupomSilencioso(pedidoId) {
    try {
        const resp = await fetch(`/api/admin/pedido/${pedidoId}/imprimir`, {
            method: 'POST',
            headers: { ...adminHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify({})
        });
        const data = await resp.json();
        if (data.success) {
            showToast('success', 'Impressão', `Cupom #${pedidoId} enviado para impressora`);
        } else {
            showToast('error', 'Erro', data.error || 'Erro ao imprimir');
        }
    } catch (err) {
        console.error('Erro ao imprimir cupom:', err);
        showToast('error', 'Erro', 'Falha ao enviar para impressora');
    }
}

async function imprimirCupomAutomatico(pedidoId) {
    await imprimirCupomSilencioso(pedidoId);
}

// ========= FIM DETALHE DO PEDIDO =========

function mostrarProdutos() {
    esconderTodasSecoes();
    document.getElementById('produtos-content').classList.remove('hidden');
    document.getElementById('page-title').textContent = 'Produtos';
    document.querySelector('header p').textContent = 'Gerencie o cardápio da pastelaria';
    atualizarMenuAtivo('produtos');
    carregarProdutosAdmin();
}

function mostrarClientes() {
    esconderTodasSecoes();
    document.getElementById('clientes-content').classList.remove('hidden');
    document.getElementById('page-title').textContent = 'Clientes';
    document.querySelector('header p').textContent = 'Gerencie os clientes cadastrados';
    atualizarMenuAtivo('clientes');
    carregarClientesAdmin();
}

function mostrarRelatorios() {
    esconderTodasSecoes();
    document.getElementById('relatorios-content').classList.remove('hidden');
    document.getElementById('page-title').textContent = 'Relatórios';
    document.querySelector('header p').textContent = 'Acompanhe o desempenho da pastelaria';
    atualizarMenuAtivo('relatorios');
    carregarTodosRelatorios();
}

function atualizarMenuAtivo(ativo) {
    document.querySelectorAll('.sidebar-item').forEach(item => {
        item.classList.remove('active');
        item.classList.remove('text-gray-100');
        item.classList.add('text-gray-400');
    });
    if (event && event.target) {
        const item = event.target.closest('.sidebar-item');
        if (item) {
            item.classList.add('active', 'text-gray-100');
            item.classList.remove('text-gray-400');
        }
    }
}

/**
 * Carrega todos os pedidos
 */
async function carregarPedidos() {
    try {
        console.log('Carregando pedidos de:', `${API_URL}/admin/pedidos`);
        const token = localStorage.getItem('admin_token') || '';
        const response = await fetch(`${API_URL}/admin/pedidos`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            credentials: 'include'
        });
        
        console.log('Response status:', response.status);
        
        if (response.ok) {
            const data = await response.json();
            console.log('Dados recebidos:', data);
            if (data.success) {
                const novosPedidos = data.pedidos || [];
                
                // Detectar novos pedidos confirmados
                detectarNovoPedidoConfirmado(novosPedidos);
                
                todosPedidos = novosPedidos;
                pedidosAnteriores = JSON.parse(JSON.stringify(novosPedidos)); // Cópia profunda
                
                console.log('Total de pedidos:', todosPedidos.length);
                console.log('Pedidos:', todosPedidos);
                renderizarKanban();
            } else {
                console.error('API retornou success: false', data);
                showToast('error', 'Erro', data.error || 'Erro ao carregar pedidos');
            }
        } else if (response.status === 401) {
            // Sessão expirada ou não autenticado - voltar para tela de login
            if (typeof logoutAdmin === 'function') {
                logoutAdmin();
            } else {
                localStorage.removeItem('admin_token');
                localStorage.removeItem('admin_nome');
                localStorage.removeItem('admin_email');
                window.location.reload();
            }
        } else {
            const errorData = await response.json().catch(() => ({}));
            console.error('Erro na resposta:', response.status, errorData);
            showToast('error', 'Erro', `Erro ${response.status}: ${errorData.error || 'Erro desconhecido'}`);
        }
    } catch (error) {
        console.error('Erro ao carregar pedidos:', error);
        showToast('error', 'Erro', 'Não foi possível carregar os pedidos. Verifique o console.');
    }
}

/**
 * Detecta novos pedidos confirmados e toca som
 */
function detectarNovoPedidoConfirmado(novosPedidos) {
    if (pedidosAnteriores.length === 0) {
        // Primeira carga, não tocar som
        return;
    }
    
    // Encontrar IDs dos pedidos confirmados anteriores
    const idsConfirmadosAnteriores = pedidosAnteriores
        .filter(p => p.status === 'pago')
        .map(p => p.id);
    
    // Encontrar novos pedidos confirmados
    const novosConfirmados = novosPedidos.filter(p => 
        p.status === 'pago' && !idsConfirmadosAnteriores.includes(p.id)
    );
    
    if (novosConfirmados.length > 0) {
        console.log('Novo pedido confirmado detectado:', novosConfirmados);
        tocarSomNotificacao();
        
        novosConfirmados.forEach(pedido => {
            showToast('success', 'Novo Pedido Confirmado!', `Pedido #${pedido.id} foi confirmado`);
            if (!pedidosJaImpressos.has(pedido.id)) {
                pedidosJaImpressos.add(pedido.id);
                imprimirCupomAutomatico(pedido.id);
            }
        });
    }
}

/**
 * Toca som de notificação
 */
function tocarSomNotificacao() {
    try {
        // Criar contexto de áudio
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Criar um beep simples (frequência 800Hz, duração 200ms)
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 800; // Frequência do beep
        oscillator.type = 'sine'; // Tipo de onda
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime); // Volume
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.2);
        
        // Segundo beep mais agudo (1000Hz)
        setTimeout(() => {
            const oscillator2 = audioContext.createOscillator();
            const gainNode2 = audioContext.createGain();
            
            oscillator2.connect(gainNode2);
            gainNode2.connect(audioContext.destination);
            
            oscillator2.frequency.value = 1000;
            oscillator2.type = 'sine';
            
            gainNode2.gain.setValueAtTime(0.3, audioContext.currentTime);
            gainNode2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.15);
            
            oscillator2.start(audioContext.currentTime);
            oscillator2.stop(audioContext.currentTime + 0.15);
        }, 100);
        
    } catch (error) {
        console.error('Erro ao tocar som:', error);
        // Fallback: usar vibração se disponível
        if (navigator.vibrate) {
            navigator.vibrate([200, 100, 200]);
        }
    }
}

/**
 * Renderiza o quadro Kanban
 */
function renderizarKanban() {
    // Limpar colunas
    const colunaPendente = document.getElementById('coluna-pendente');
    const colunaConfirmado = document.getElementById('coluna-confirmado');
    const colunaPreparacao = document.getElementById('coluna-preparacao');
    const colunaPronto = document.getElementById('coluna-pronto');
    const colunaEntregue = document.getElementById('coluna-entregue');
    
    colunaPendente.innerHTML = '';
    colunaConfirmado.innerHTML = '';
    colunaPreparacao.innerHTML = '';
    colunaPronto.innerHTML = '';
    colunaEntregue.innerHTML = '';
    
    // Contadores
    let countPendente = 0;
    let countConfirmado = 0;
    let countPreparacao = 0;
    let countPronto = 0;
    let countEntregue = 0;
    
    // Agrupar pedidos por status
    console.log('Renderizando Kanban com', todosPedidos.length, 'pedidos');
    todosPedidos.forEach(pedido => {
        // Ignorar pedidos cancelados
        if (pedido.status === 'cancelado') {
            console.log('Pedido cancelado ignorado:', pedido.id);
            return;
        }
        
        console.log('Processando pedido:', pedido.id, 'Status:', pedido.status);
        const card = criarCardPedido(pedido);
        
        if (pedido.status === 'pendente') {
            colunaPendente.appendChild(card);
            countPendente++;
        } else if (pedido.status === 'pago') {
            // Pedidos pagos (PIX, cartão, dinheiro) vão para "Confirmado"
            colunaConfirmado.appendChild(card);
            countConfirmado++;
        } else if (pedido.status === 'preparando') {
            colunaPreparacao.appendChild(card);
            countPreparacao++;
        } else if (pedido.status === 'pronto') {
            colunaPronto.appendChild(card);
            countPronto++;
        } else if (pedido.status === 'entregue' || pedido.status === 'retirado') {
            colunaEntregue.appendChild(card);
            countEntregue++;
        } else {
            console.warn('Status desconhecido:', pedido.status, 'para pedido', pedido.id);
        }
    });
    
    // Mostrar mensagem quando coluna está vazia
    if (countPendente === 0) {
        colunaPendente.innerHTML = '<div class="flex flex-col items-center justify-center h-full opacity-40"><i class="fas fa-inbox text-4xl mb-2 text-gray-300"></i><p class="text-sm text-gray-400">Nenhum pedido pendente</p></div>';
    }
    if (countConfirmado === 0) {
        colunaConfirmado.innerHTML = '<div class="flex flex-col items-center justify-center h-full opacity-40"><i class="fas fa-inbox text-4xl mb-2 text-gray-300"></i><p class="text-sm text-gray-400">Nenhum pedido confirmado</p></div>';
    }
    if (countPreparacao === 0) {
        colunaPreparacao.innerHTML = '<div class="flex flex-col items-center justify-center h-full opacity-40"><i class="fas fa-inbox text-4xl mb-2 text-gray-300"></i><p class="text-sm text-gray-400">Nenhum pedido em preparação</p></div>';
    }
    if (countPronto === 0) {
        colunaPronto.innerHTML = '<div class="flex flex-col items-center justify-center h-full opacity-40"><i class="fas fa-inbox text-4xl mb-2 text-gray-300"></i><p class="text-sm text-gray-400">Nenhum pedido pronto</p></div>';
    }
    if (countEntregue === 0) {
        colunaEntregue.innerHTML = '<div class="flex flex-col items-center justify-center h-full opacity-40"><i class="fas fa-inbox text-4xl mb-2 text-gray-300"></i><p class="text-sm text-gray-400">Nenhum pedido finalizado</p></div>';
    }
    
    // Atualizar contadores
    document.getElementById('count-pendente').textContent = countPendente;
    document.getElementById('count-confirmado').textContent = countConfirmado;
    document.getElementById('count-preparacao').textContent = countPreparacao;
    document.getElementById('count-pronto').textContent = countPronto;
    document.getElementById('count-entregue').textContent = countEntregue;
}

/**
 * Cria um card de pedido
 */
function criarCardPedido(pedido) {
    const card = document.createElement('div');
    card.className = 'kanban-card bg-white p-4 rounded-lg shadow-sm border border-gray-100 hover:border-orange-200 hover:shadow-md transition-all cursor-move';
    card.draggable = true;
    card.id = `pedido-${pedido.id}`;
    card.ondragstart = (e) => dragStart(e, pedido.id);
    card.ondragend = dragEnd;
    card.onclick = (e) => {
        if (e.target.closest('.btn-mover') || e.target.closest('.dragging')) return;
        abrirDetalhePedido(pedido.id);
    };
    
    const endereco = formatarEndereco(pedido.observacoes);
    let dataPedido;
    if (pedido.created_at instanceof Date) {
        dataPedido = pedido.created_at;
    } else if (typeof pedido.created_at === 'string') {
        dataPedido = new Date(pedido.created_at);
    } else {
        dataPedido = new Date();
    }
    const metodoPagamento = obterMetodoPagamento(pedido);
    const isEntregue = pedido.status === 'entregue' || pedido.status === 'retirado';
    
    const estiloFinalizado = isEntregue ? 'bg-gray-100/50 grayscale-[0.5]' : '';
    const corTexto = isEntregue ? 'text-gray-600' : 'text-gray-800';
    const corTextoSecundario = isEntregue ? 'text-gray-400' : 'text-gray-500';

    const statusMapped = (pedido.status === 'retirado' || pedido.status === 'entregue') ? 'entregue' : pedido.status;
    const idxStatus = STATUS_ORDEM.indexOf(statusMapped);
    const temAnterior = idxStatus > 0;
    const temProximo = idxStatus >= 0 && idxStatus < STATUS_ORDEM.length - 1;
    
    card.innerHTML = `
        <div class="${estiloFinalizado}">
            <div class="flex justify-between items-start mb-2">
                <span class="text-xs font-bold text-gray-400">#${pedido.id}</span>
                ${metodoPagamento ? `<span class="text-xs font-bold ${metodoPagamento.cor} ${metodoPagamento.bg} px-2 py-0.5 rounded">${metodoPagamento.texto}</span>` : ''}
            </div>
            <h4 class="font-bold ${corTexto} mb-1">${pedido.cliente_nome || 'Cliente'}</h4>
            <p class="text-xs ${corTextoSecundario} mb-3">${pedido.itens_descricao || 'Sem itens'}</p>
            ${!isEntregue ? `<p class="text-xs ${corTextoSecundario} mb-2"><i class="fas fa-map-marker-alt mr-1"></i>${endereco}</p>` : ''}
            <div class="flex justify-between items-center pt-2 border-t border-gray-50">
                <span class="text-sm font-bold text-slate-700">R$ ${parseFloat(pedido.total).toFixed(2).replace('.', ',')}</span>
                ${isEntregue ? `<span class="text-[10px] text-gray-400 uppercase tracking-wider">Finalizado às ${formatarHora(dataPedido)}</span>` : `<span class="text-[10px] text-gray-400">${formatarHora(dataPedido)}</span>`}
            </div>
            <div class="flex justify-between items-center mt-2 pt-2 border-t border-gray-100">
                ${temAnterior ? `<button class="btn-mover text-xs px-2 py-1 rounded bg-gray-100 hover:bg-gray-200 text-gray-600 transition-colors" onclick="event.stopPropagation(); moverPedidoEsquerda(${pedido.id})" title="Voltar"><i class="fas fa-chevron-left mr-1"></i>Voltar</button>` : '<span></span>'}
                ${temProximo ? `<button class="btn-mover text-xs px-2 py-1 rounded bg-orange-100 hover:bg-orange-200 text-orange-700 transition-colors" onclick="event.stopPropagation(); moverPedidoDireita(${pedido.id})" title="Avançar">Avançar<i class="fas fa-chevron-right ml-1"></i></button>` : '<span></span>'}
            </div>
        </div>
    `;
    
    return card;
}

/**
 * Obtém método de pagamento do pedido
 */
function obterMetodoPagamento(pedido) {
    // Tentar obter do observacoes ou inferir do status
    try {
        if (pedido.observacoes) {
            const obs = typeof pedido.observacoes === 'string' ? JSON.parse(pedido.observacoes) : pedido.observacoes;
            if (obs.metodo_pagamento) {
                const metodo = obs.metodo_pagamento.toLowerCase();
                if (metodo === 'pix') {
                    return { texto: 'PIX', cor: 'text-orange-600', bg: 'bg-orange-50' };
                } else if (metodo === 'dinheiro') {
                    return { texto: 'Dinheiro', cor: 'text-green-600', bg: 'bg-green-50' };
                } else if (metodo === 'cartao') {
                    return { texto: 'Cartão', cor: 'text-blue-600', bg: 'bg-blue-50' };
                }
            }
        }
    } catch (e) {
        // Ignorar erro
    }
    
    // Se status é pago, assumir PIX
    if (pedido.status === 'pago' || pedido.status === 'preparando') {
        return { texto: 'Pago', cor: 'text-green-600', bg: 'bg-green-50' };
    }
    
    return null;
}

/**
 * Formata hora
 */
function formatarHora(data) {
    return data.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

/**
 * Formata endereço
 */
function formatarTelefone(tel) {
    if (!tel) return 'N/A';
    let digits = tel.replace(/\D/g, '');
    if (digits.length >= 12 && digits.startsWith('55')) digits = digits.substring(2);
    if (digits.length === 11) return `(${digits.slice(0,2)}) ${digits.slice(2,7)}-${digits.slice(7)}`;
    if (digits.length === 10) return `(${digits.slice(0,2)}) ${digits.slice(2,6)}-${digits.slice(6)}`;
    return tel;
}

function formatarEndereco(observacoes) {
    if (!observacoes) return 'Endereço não informado';
    
    try {
        const end = typeof observacoes === 'string' ? JSON.parse(observacoes) : observacoes;
        
        if (end.retirada_local || end.tipo_entrega === 'retirada') {
            return '🏪 Retirada no Local';
        }

        if (end.tipo_entrega === 'entrega' || end.rua) {
            let endereco = end.rua || '';
            if (end.numero) endereco += `, ${end.numero}`;
            if (end.bairro) endereco += ` - ${end.bairro}`;
            if (end.complemento) endereco += ` (${end.complemento})`;
            return endereco ? `🛵 ${endereco}` : 'Endereço não informado';
        }

        return 'Endereço não informado';
    } catch (e) {
        return 'Endereço não informado';
    }
}

/**
 * Formata data
 */
function formatarData(data) {
    const agora = new Date();
    const diff = agora - data;
    const minutos = Math.floor(diff / 60000);
    const horas = Math.floor(minutos / 60);
    
    if (minutos < 1) return 'Agora';
    if (minutos < 60) return `Há ${minutos} min`;
    if (horas < 24) return `Há ${horas}h`;
    return data.toLocaleDateString('pt-BR');
}

/**
 * Drag and Drop
 */
function allowDrop(ev) {
    ev.preventDefault();
    if (ev.currentTarget.classList.contains('kanban-body') || ev.currentTarget.id.startsWith('coluna-')) {
        ev.currentTarget.classList.add('drag-over');
    }
}

// Remover classe drag-over quando sair da área
document.addEventListener('dragleave', (e) => {
    if (e.target.id && e.target.id.startsWith('coluna-')) {
        e.target.classList.remove('drag-over');
    }
});

document.addEventListener('drop', (e) => {
    if (e.target.id && e.target.id.startsWith('coluna-')) {
        e.target.classList.remove('drag-over');
    }
});

function dragStart(ev, pedidoId) {
    pedidoArrastado = pedidoId;
    ev.dataTransfer.effectAllowed = 'move';
    ev.currentTarget.classList.add('dragging');
}

function dragEnd(ev) {
    ev.currentTarget.classList.remove('dragging');
}

function drop(ev) {
    ev.preventDefault();
    ev.stopPropagation();
    
    const pedidoId = pedidoArrastado;
    if (!pedidoId) return;
    pedidoArrastado = null;
    
    const coluna = ev.currentTarget;
    coluna.classList.remove('drag-over');
    if (!coluna) return;
    
    const novoStatus = resolverStatusColuna(coluna.id, pedidoId);
    if (!novoStatus) return;
    
    moverPedidoParaStatus(pedidoId, novoStatus);
}

function resolverStatusColuna(colunaId, pedidoId) {
    const mapa = {
        'coluna-pendente': 'pendente',
        'coluna-confirmado': 'pago',
        'coluna-preparacao': 'preparando',
        'coluna-pronto': 'pronto'
    };
    if (mapa[colunaId]) return mapa[colunaId];
    
    if (colunaId === 'coluna-entregue') {
        const pedido = todosPedidos.find(p => p.id === pedidoId);
        if (pedido) {
            try {
                const obs = typeof pedido.observacoes === 'string' ? JSON.parse(pedido.observacoes) : pedido.observacoes;
                return (obs && (obs.retirada_local || obs.rua === 'Retirada no Local')) ? 'retirado' : 'entregue';
            } catch (e) { return 'entregue'; }
        }
        return 'entregue';
    }
    return null;
}

const STATUS_ORDEM = ['pendente', 'pago', 'preparando', 'pronto', 'entregue'];

function obterStatusAnterior(statusAtual) {
    const mapped = (statusAtual === 'retirado' || statusAtual === 'entregue') ? 'entregue' : statusAtual;
    const idx = STATUS_ORDEM.indexOf(mapped);
    return idx > 0 ? STATUS_ORDEM[idx - 1] : null;
}

function obterProximoStatus(statusAtual, pedidoId) {
    const mapped = (statusAtual === 'retirado' || statusAtual === 'entregue') ? 'entregue' : statusAtual;
    const idx = STATUS_ORDEM.indexOf(mapped);
    if (idx < 0 || idx >= STATUS_ORDEM.length - 1) return null;
    const prox = STATUS_ORDEM[idx + 1];
    if (prox === 'entregue') {
        const pedido = todosPedidos.find(p => p.id === pedidoId);
        if (pedido) {
            try {
                const obs = typeof pedido.observacoes === 'string' ? JSON.parse(pedido.observacoes) : pedido.observacoes;
                return (obs && (obs.retirada_local || obs.rua === 'Retirada no Local')) ? 'retirado' : 'entregue';
            } catch(e) { return 'entregue'; }
        }
        return 'entregue';
    }
    return prox;
}

function moverPedidoEsquerda(pedidoId) {
    const pedido = todosPedidos.find(p => p.id === pedidoId);
    if (!pedido) return;
    const anterior = obterStatusAnterior(pedido.status);
    if (anterior) moverPedidoParaStatus(pedidoId, anterior);
}

function moverPedidoDireita(pedidoId) {
    const pedido = todosPedidos.find(p => p.id === pedidoId);
    if (!pedido) return;
    const proximo = obterProximoStatus(pedido.status, pedidoId);
    if (proximo) moverPedidoParaStatus(pedidoId, proximo);
}

function moverPedidoParaStatus(pedidoId, novoStatus) {
    const pedidoLocal = todosPedidos.find(p => p.id === pedidoId);
    if (!pedidoLocal) return;
    
    const statusAnterior = pedidoLocal.status;
    if (statusAnterior === novoStatus) return;
    
    pedidoLocal.status = novoStatus;
    renderizarKanban();
    
    if (novoStatus === 'pago' && !pedidosJaImpressos.has(pedidoId)) {
        pedidosJaImpressos.add(pedidoId);
        imprimirCupomAutomatico(pedidoId);
    }

    fetch(`${API_URL}/admin/pedido/${pedidoId}/status`, {
        method: 'PUT',
        headers: { ...adminHeaders(), 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ status: novoStatus })
    }).then(r => r.json()).then(data => {
        if (data.success) {
            showToast('success', 'Status atualizado', `Pedido #${pedidoId} movido`);
        } else {
            pedidoLocal.status = statusAnterior;
            renderizarKanban();
            showToast('error', 'Erro', data.error || 'Falha ao atualizar');
        }
    }).catch(err => {
        console.error('Erro ao atualizar status:', err);
        pedidoLocal.status = statusAnterior;
        renderizarKanban();
        showToast('error', 'Erro', 'Verifique sua conexão');
    });
}


// ==================== CRUD PRODUTOS ====================

async function carregarProdutosAdmin() {
    try {
        const token = localStorage.getItem('admin_token') || '';
        const resp = await fetch(`${API_URL}/admin/produtos`, {
            headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        const data = await resp.json();
        if (data.success) {
            todosProdutos = data.produtos || [];
            preencherFiltros();
            filtrarProdutos();
        } else {
            showToast('error', 'Erro', data.error || 'Erro ao carregar produtos');
        }
    } catch (e) {
        console.error('Erro ao carregar produtos:', e);
        showToast('error', 'Erro', 'Não foi possível carregar produtos');
    }
}

function preencherFiltros() {
    // Filtros fixos já definidos no HTML
}

function filtrarProdutos() {
    const busca = (document.getElementById('busca-produto')?.value || '').toLowerCase();
    const catFiltro = document.getElementById('filtro-categoria')?.value || '';
    const mostrarInativos = document.getElementById('mostrar-inativos')?.checked || false;

    const filtrados = todosProdutos.filter(p => {
        if (!mostrarInativos && !p.ativo) return false;
        if (catFiltro && p.categoria !== catFiltro) return false;
        if (busca) {
            const texto = `${p.nome} ${p.descricao || ''} ${p.categoria}`.toLowerCase();
            if (!texto.includes(busca)) return false;
        }
        return true;
    });

    renderizarTabelaProdutos(filtrados);
}

function renderizarTabelaProdutos(produtos) {
    const tbody = document.getElementById('tabela-produtos');
    const vazio = document.getElementById('produtos-vazio');
    const contagem = document.getElementById('produtos-contagem');

    if (produtos.length === 0) {
        tbody.innerHTML = '';
        vazio.classList.remove('hidden');
        contagem.textContent = '';
        return;
    }

    vazio.classList.add('hidden');
    const ativos = todosProdutos.filter(p => p.ativo).length;
    contagem.textContent = `${ativos} produto(s) ativo(s) | ${todosProdutos.length} total`;

    tbody.innerHTML = produtos.map(p => {
        const inativo = !p.ativo;
        const rowClass = inativo ? 'bg-gray-50 opacity-60' : 'hover:bg-orange-50/30';
        const statusBadge = inativo
            ? '<span class="px-2.5 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-600">Inativo</span>'
            : '<span class="px-2.5 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-600">Ativo</span>';

        const imgHtml = p.imagem_url
            ? `<img src="${p.imagem_url}" class="w-10 h-10 rounded-lg object-cover border border-gray-200" onerror="this.src='';this.className='hidden'">`
            : `<div class="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center"><i class="fas fa-box text-orange-400"></i></div>`;

        return `
            <tr class="${rowClass} transition-colors">
                <td class="px-6 py-4">
                    <div class="flex items-center gap-3">
                        ${imgHtml}
                        <div>
                            <p class="font-semibold text-gray-800 text-sm">${p.nome}</p>
                            <p class="text-xs text-gray-400 max-w-xs truncate">${p.descricao || '-'}</p>
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4">
                    <span class="px-2.5 py-1 text-xs font-medium rounded-full ${
                        p.categoria === 'Salgados' ? 'bg-amber-100 text-amber-700' :
                        p.categoria === 'Doces' ? 'bg-pink-100 text-pink-700' :
                        p.categoria === 'Bebidas' ? 'bg-blue-100 text-blue-700' :
                        'bg-slate-100 text-slate-600'
                    }">${p.categoria}</span>
                </td>
                <td class="px-6 py-4 text-right">
                    <p class="font-bold text-sm text-gray-800">R$ ${parseFloat(p.preco).toFixed(2).replace('.', ',')}</p>
                    <p class="text-[10px] text-gray-400">Custo: R$ ${parseFloat(p.custo || 0).toFixed(2).replace('.', ',')}</p>
                </td>
                <td class="px-6 py-4 text-center">
                    <span class="text-sm font-medium ${p.quantidade > 0 ? 'text-green-600' : 'text-red-500'}">${p.quantidade}</span>
                </td>
                <td class="px-6 py-4 text-center">${statusBadge}</td>
                <td class="px-6 py-4 text-center">
                    <div class="flex items-center justify-center gap-1">
                        <button onclick="editarProduto(${p.id})" class="p-2 text-blue-500 hover:bg-blue-50 rounded-lg transition-colors" title="Editar">
                            <i class="fas fa-pen text-xs"></i>
                        </button>
                        ${inativo
                            ? `<button onclick="restaurarProduto(${p.id})" class="p-2 text-green-500 hover:bg-green-50 rounded-lg transition-colors" title="Restaurar">
                                <i class="fas fa-undo text-xs"></i>
                               </button>`
                            : `<button onclick="abrirModalExcluir(${p.id}, '${p.nome.replace(/'/g, "\\'")}')" class="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Desativar">
                                <i class="fas fa-trash text-xs"></i>
                               </button>`
                        }
                    </div>
                </td>
            </tr>`;
    }).join('');
}

function abrirModalProduto(produto = null) {
    document.getElementById('modal-produto').classList.remove('hidden');
    document.getElementById('modal-produto-titulo').textContent = produto ? 'Editar Produto' : 'Novo Produto';

    document.getElementById('produto-id').value = produto ? produto.id : '';
    document.getElementById('produto-nome').value = produto ? produto.nome : '';
    document.getElementById('produto-descricao').value = produto ? (produto.descricao || '') : '';
    document.getElementById('produto-preco').value = produto ? produto.preco : '';
    document.getElementById('produto-custo').value = produto ? (produto.custo || 0) : '';
    document.getElementById('produto-quantidade').value = produto ? produto.quantidade : 0;
    document.getElementById('produto-categoria').value = produto ? produto.categoria : '';
    document.getElementById('produto-imagem').value = produto ? (produto.imagem_url || '') : '';
    document.getElementById('produto-imagem-url').value = produto ? (produto.imagem_url || '') : '';
    calcularMargem();

    resetUploadArea();
    if (produto && produto.imagem_url) {
        mostrarPreview(produto.imagem_url, 'Imagem atual');
    }

    setTimeout(() => document.getElementById('produto-nome').focus(), 100);
}

function fecharModalProduto() {
    document.getElementById('modal-produto').classList.add('hidden');
    document.getElementById('form-produto').reset();
    resetUploadArea();
}

function resetUploadArea() {
    document.getElementById('upload-placeholder').classList.remove('hidden');
    document.getElementById('upload-preview').classList.add('hidden');
    document.getElementById('upload-progress').classList.add('hidden');
    document.getElementById('produto-arquivo').value = '';
}

function mostrarPreview(src, nome) {
    document.getElementById('upload-placeholder').classList.add('hidden');
    document.getElementById('upload-preview').classList.remove('hidden');
    document.getElementById('preview-img').src = src;
    document.getElementById('preview-nome').textContent = nome || '';
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('border-orange-500', 'bg-orange-50');
    const files = e.dataTransfer.files;
    if (files.length > 0) uploadImagem(files[0]);
}

function handleFileSelect(input) {
    if (input.files.length > 0) uploadImagem(input.files[0]);
}

function usarUrl(url) {
    if (url.trim()) {
        document.getElementById('produto-imagem').value = url.trim();
        mostrarPreview(url.trim(), 'URL externa');
    } else {
        resetUploadArea();
        document.getElementById('produto-imagem').value = '';
    }
}

async function uploadImagem(arquivo) {
    const ext = arquivo.name.split('.').pop().toLowerCase();
    if (!['jpg', 'jpeg', 'png', 'webp', 'gif'].includes(ext)) {
        showToast('error', 'Erro', 'Formato inválido. Use JPG, PNG, WEBP ou GIF');
        return;
    }
    if (arquivo.size > 5 * 1024 * 1024) {
        showToast('error', 'Erro', 'Imagem muito grande. Máximo 5MB');
        return;
    }

    const previewUrl = URL.createObjectURL(arquivo);
    mostrarPreview(previewUrl, arquivo.name);

    const progress = document.getElementById('upload-progress');
    const bar = document.getElementById('upload-bar');
    const status = document.getElementById('upload-status');
    progress.classList.remove('hidden');
    bar.style.width = '30%';
    status.textContent = 'Enviando...';

    const formData = new FormData();
    formData.append('imagem', arquivo);

    try {
        const token = localStorage.getItem('admin_token') || '';
        bar.style.width = '60%';

        const resp = await fetch(`${API_URL}/admin/upload-imagem`, {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token },
            credentials: 'include',
            body: formData
        });

        bar.style.width = '90%';
        const data = await resp.json();

        if (data.success) {
            bar.style.width = '100%';
            status.textContent = 'Upload concluído!';
            document.getElementById('produto-imagem').value = data.url;
            document.getElementById('produto-imagem-url').value = data.url;
            document.getElementById('preview-nome').textContent = arquivo.name + ' - Upload OK';
            setTimeout(() => progress.classList.add('hidden'), 1500);
        } else {
            status.textContent = 'Erro: ' + (data.error || 'falhou');
            bar.classList.replace('bg-orange-500', 'bg-red-500');
            showToast('error', 'Erro', data.error || 'Erro no upload');
        }
    } catch (e) {
        status.textContent = 'Erro de conexão';
        bar.classList.replace('bg-orange-500', 'bg-red-500');
        showToast('error', 'Erro', 'Falha no upload');
    }
}

function editarProduto(id) {
    const produto = todosProdutos.find(p => p.id === id);
    if (produto) abrirModalProduto(produto);
}

async function salvarProduto(e) {
    e.preventDefault();
    const id = document.getElementById('produto-id').value;
    const dados = {
        nome: document.getElementById('produto-nome').value.trim(),
        descricao: document.getElementById('produto-descricao').value.trim(),
        preco: parseFloat(document.getElementById('produto-preco').value),
        custo: parseFloat(document.getElementById('produto-custo').value) || 0,
        quantidade: parseInt(document.getElementById('produto-quantidade').value) || 0,
        categoria: document.getElementById('produto-categoria').value.trim(),
        tipo: document.getElementById('produto-categoria').value.trim(),
        imagem_url: document.getElementById('produto-imagem').value.trim()
    };

    const token = localStorage.getItem('admin_token') || '';
    const url = id ? `${API_URL}/admin/produto/${id}` : `${API_URL}/admin/produto`;
    const method = id ? 'PUT' : 'POST';

    try {
        const btn = document.getElementById('btn-salvar-produto');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Salvando...';

        const resp = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
            credentials: 'include',
            body: JSON.stringify(dados)
        });

        const data = await resp.json();
        if (data.success) {
            showToast('success', 'Sucesso', id ? 'Produto atualizado!' : 'Produto criado!');
            fecharModalProduto();
            carregarProdutosAdmin();
        } else {
            showToast('error', 'Erro', data.error || 'Erro ao salvar produto');
        }
    } catch (err) {
        showToast('error', 'Erro', 'Erro de conexão ao salvar');
    } finally {
        const btn = document.getElementById('btn-salvar-produto');
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-save mr-2"></i>Salvar';
    }
}

function abrirModalExcluir(id, nome) {
    produtoExcluirId = id;
    document.getElementById('excluir-produto-nome').textContent = `"${nome}" será desativado do cardápio.`;
    document.getElementById('modal-excluir').classList.remove('hidden');
}

function fecharModalExcluir() {
    document.getElementById('modal-excluir').classList.add('hidden');
    produtoExcluirId = null;
}

async function confirmarExclusao() {
    if (!produtoExcluirId) return;
    const token = localStorage.getItem('admin_token') || '';

    try {
        const resp = await fetch(`${API_URL}/admin/produto/${produtoExcluirId}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        const data = await resp.json();
        if (data.success) {
            showToast('success', 'Sucesso', 'Produto desativado!');
            fecharModalExcluir();
            carregarProdutosAdmin();
        } else {
            showToast('error', 'Erro', data.error);
        }
    } catch (e) {
        showToast('error', 'Erro', 'Erro ao desativar produto');
    }
}

async function restaurarProduto(id) {
    const token = localStorage.getItem('admin_token') || '';
    try {
        const resp = await fetch(`${API_URL}/admin/produto/${id}/restaurar`, {
            method: 'POST',
            headers: { 'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        const data = await resp.json();
        if (data.success) {
            showToast('success', 'Sucesso', 'Produto restaurado!');
            carregarProdutosAdmin();
        } else {
            showToast('error', 'Erro', data.error);
        }
    } catch (e) {
        showToast('error', 'Erro', 'Erro ao restaurar produto');
    }
}


function calcularMargem() {
    const preco = parseFloat(document.getElementById('produto-preco')?.value) || 0;
    const custo = parseFloat(document.getElementById('produto-custo')?.value) || 0;
    const preview = document.getElementById('margem-preview');
    const valor = document.getElementById('margem-valor');
    if (!preview || !valor) return;

    if (preco > 0 && custo > 0) {
        const margem = ((preco - custo) / preco * 100).toFixed(1);
        const lucro = (preco - custo).toFixed(2).replace('.', ',');
        valor.textContent = `${margem}% (R$ ${lucro} por unidade)`;
        preview.classList.remove('hidden');
        if (margem < 20) { preview.className = 'bg-red-50 border border-red-200 rounded-lg px-4 py-2 text-sm'; valor.className = 'font-bold text-red-800'; }
        else if (margem < 40) { preview.className = 'bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2 text-sm'; valor.className = 'font-bold text-yellow-800'; }
        else { preview.className = 'bg-green-50 border border-green-200 rounded-lg px-4 py-2 text-sm'; valor.className = 'font-bold text-green-800'; }
    } else {
        preview.classList.add('hidden');
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const precoInput = document.getElementById('produto-preco');
    const custoInput = document.getElementById('produto-custo');
    if (precoInput) precoInput.addEventListener('input', calcularMargem);
    if (custoInput) custoInput.addEventListener('input', calcularMargem);
});


// ==================== RELATÓRIOS ====================

let graficoFaturamento = null;

function fmtR$(v) { return 'R$ ' + parseFloat(v || 0).toFixed(2).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, '.'); }

function adminHeaders() {
    return { 'Authorization': 'Bearer ' + (localStorage.getItem('admin_token') || ''), 'Content-Type': 'application/json' };
}

async function carregarTodosRelatorios() {
    carregarResumo();
    carregarFaturamento('dia');
    carregarDRE('mes');
    carregarTopClientes();
    carregarTopProdutos();
}

async function carregarResumo() {
    try {
        const resp = await fetch(`${API_URL}/admin/relatorios/resumo`, { headers: adminHeaders(), credentials: 'include' });
        const data = await resp.json();
        if (data.success) {
            const r = data.resumo;
            document.getElementById('kpi-hoje').textContent = fmtR$(r.receita_hoje);
            document.getElementById('kpi-semana').textContent = fmtR$(r.receita_semana);
            document.getElementById('kpi-mes').textContent = fmtR$(r.receita_mes);
            document.getElementById('kpi-ticket').textContent = fmtR$(r.ticket_medio);
            document.getElementById('kpi-pedidos').textContent = r.total_pedidos;
            document.getElementById('kpi-clientes').textContent = r.total_clientes;
            document.getElementById('kpi-pendentes').textContent = r.pedidos_pendentes;
            document.getElementById('kpi-total').textContent = fmtR$(r.receita_total);
        }
    } catch (e) { console.error('Erro resumo:', e); }
}

async function carregarFaturamento(periodo) {
    document.querySelectorAll('[id^="btn-fat-"]').forEach(b => {
        b.className = 'px-3 py-1 rounded-md text-xs font-semibold text-gray-600 hover:bg-gray-200';
    });
    document.getElementById('btn-fat-' + periodo).className = 'px-3 py-1 rounded-md text-xs font-semibold bg-orange-500 text-white';

    try {
        const resp = await fetch(`${API_URL}/admin/relatorios/faturamento?periodo=${periodo}`, { headers: adminHeaders(), credentials: 'include' });
        const data = await resp.json();
        if (data.success) {
            const dados = data.dados;
            let labels, valores, pedidos;

            if (periodo === 'dia') {
                labels = dados.map(d => { const dt = new Date(d.data + 'T12:00:00'); return dt.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }); });
                valores = dados.map(d => d.faturamento);
                pedidos = dados.map(d => d.qtd_pedidos);
            } else if (periodo === 'semana') {
                labels = dados.map(d => { const di = new Date(d.data_inicio + 'T12:00:00'); const df = new Date(d.data_fim + 'T12:00:00'); return di.toLocaleDateString('pt-BR', {day:'2-digit',month:'2-digit'}) + ' - ' + df.toLocaleDateString('pt-BR', {day:'2-digit',month:'2-digit'}); });
                valores = dados.map(d => d.faturamento);
                pedidos = dados.map(d => d.qtd_pedidos);
            } else {
                labels = dados.map(d => { const [y,m] = d.mes.split('-'); const meses = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']; return meses[parseInt(m)-1] + '/' + y.slice(2); });
                valores = dados.map(d => d.faturamento);
                pedidos = dados.map(d => d.qtd_pedidos);
            }

            renderizarGraficoFaturamento(labels, valores, pedidos);
        }
    } catch (e) { console.error('Erro faturamento:', e); }
}

function renderizarGraficoFaturamento(labels, valores, pedidos) {
    const ctx = document.getElementById('grafico-faturamento');
    if (graficoFaturamento) graficoFaturamento.destroy();

    graficoFaturamento = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Faturamento (R$)',
                    data: valores,
                    backgroundColor: 'rgba(249, 115, 22, 0.7)',
                    borderColor: 'rgb(249, 115, 22)',
                    borderWidth: 1,
                    borderRadius: 6,
                    yAxisID: 'y'
                },
                {
                    label: 'Pedidos',
                    data: pedidos,
                    type: 'line',
                    borderColor: 'rgb(59, 130, 246)',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: 4,
                    pointBackgroundColor: 'rgb(59, 130, 246)',
                    fill: true,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top', labels: { font: { size: 11 }, usePointStyle: true } },
                tooltip: { callbacks: { label: function(ctx) { return ctx.dataset.label === 'Faturamento (R$)' ? 'R$ ' + ctx.parsed.y.toFixed(2) : ctx.parsed.y + ' pedidos'; } } }
            },
            scales: {
                y: { type: 'linear', position: 'left', ticks: { callback: v => 'R$ ' + v.toFixed(0) }, grid: { color: 'rgba(0,0,0,0.05)' } },
                y1: { type: 'linear', position: 'right', grid: { drawOnChartArea: false }, ticks: { stepSize: 1 } },
                x: { grid: { display: false } }
            }
        }
    });
}

async function carregarDRE(periodo) {
    try {
        const resp = await fetch(`${API_URL}/admin/relatorios/dre?periodo=${periodo}`, { headers: adminHeaders(), credentials: 'include' });
        const data = await resp.json();
        if (data.success) {
            const d = data.dre;
            const margemCor = d.margem_lucro >= 30 ? 'text-green-600' : d.margem_lucro >= 15 ? 'text-yellow-600' : 'text-red-600';

            let catHtml = '';
            if (d.por_categoria && d.por_categoria.length > 0) {
                catHtml = d.por_categoria.map(c => {
                    const cor = c.categoria === 'Salgados' ? 'bg-amber-400' : c.categoria === 'Doces' ? 'bg-pink-400' : c.categoria === 'Bebidas' ? 'bg-blue-400' : 'bg-gray-400';
                    const pct = d.receita_bruta > 0 ? (c.total / d.receita_bruta * 100).toFixed(0) : 0;
                    return `<div class="flex items-center justify-between text-xs">
                        <div class="flex items-center gap-2"><span class="w-2.5 h-2.5 rounded-full ${cor}"></span>${c.categoria}</div>
                        <span class="font-semibold">${fmtR$(c.total)} <span class="text-gray-400">(${pct}%)</span></span>
                    </div>`;
                }).join('');
            }

            document.getElementById('dre-content').innerHTML = `
                <div class="space-y-1.5">
                    <div class="flex justify-between py-2 border-b border-gray-200 font-bold text-gray-800">
                        <span><i class="fas fa-arrow-up text-green-500 mr-1"></i> Receita Bruta</span>
                        <span>${fmtR$(d.receita_bruta)}</span>
                    </div>
                    <div class="flex justify-between py-1.5 text-red-500">
                        <span class="pl-4">(-) Cancelamentos/Devoluções</span>
                        <span>${fmtR$(d.cancelados)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-gray-200 font-semibold text-gray-700">
                        <span>= Receita Líquida</span>
                        <span>${fmtR$(d.receita_liquida)}</span>
                    </div>
                    <div class="flex justify-between py-1.5 text-red-500">
                        <span class="pl-4">(-) CMV ${d.cmv_estimado ? '<span class="text-[10px] text-gray-400">(est. 35%)</span>' : '<span class="text-[10px] text-green-500">(custo real)</span>'}</span>
                        <span>${fmtR$(d.custo_mercadoria)}</span>
                    </div>
                    <div class="flex justify-between py-2 border-b border-gray-200 font-semibold text-gray-700">
                        <span>= Lucro Bruto</span>
                        <span>${fmtR$(d.lucro_bruto)}</span>
                    </div>
                    <div class="flex justify-between py-1.5 text-red-500">
                        <span class="pl-4">(-) Impostos (est. 6%)</span>
                        <span>${fmtR$(d.impostos)}</span>
                    </div>
                    <div class="flex justify-between py-3 border-t-2 border-gray-800 font-bold text-lg text-gray-800">
                        <span>= Lucro Líquido</span>
                        <span class="${margemCor}">${fmtR$(d.lucro_liquido)}</span>
                    </div>
                    <div class="flex justify-between pt-2">
                        <span class="text-xs text-gray-500">Margem de Lucro</span>
                        <span class="text-sm font-bold ${margemCor}">${d.margem_lucro.toFixed(1)}%</span>
                    </div>
                    <div class="flex justify-between">
                        <span class="text-xs text-gray-500">Qtd. Pedidos</span>
                        <span class="text-sm font-semibold">${d.qtd_pedidos}</span>
                    </div>
                </div>
                ${catHtml ? `<div class="mt-4 pt-4 border-t border-gray-200"><p class="text-xs font-semibold text-gray-500 uppercase mb-2">Receita por Categoria</p><div class="space-y-2">${catHtml}</div></div>` : ''}
                <p class="text-[10px] text-gray-400 mt-3 italic">* ${d.cmv_estimado ? 'CMV estimado em 35% (cadastre o custo nos produtos para cálculo real). ' : ''}Impostos estimados em 6%. Ajuste conforme sua contabilidade.</p>
            `;
        }
    } catch (e) { console.error('Erro DRE:', e); }
}

async function carregarTopClientes() {
    try {
        const resp = await fetch(`${API_URL}/admin/relatorios/top-clientes`, { headers: adminHeaders(), credentials: 'include' });
        const data = await resp.json();
        if (data.success) {
            const tbody = document.getElementById('tabela-top-clientes');
            if (data.clientes.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-gray-400">Nenhum cliente encontrado</td></tr>';
                return;
            }
            tbody.innerHTML = data.clientes.map((c, i) => {
                const medalha = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `<span class="text-gray-400">${i + 1}</span>`;
                const ultimo = c.ultimo_pedido ? new Date(c.ultimo_pedido).toLocaleDateString('pt-BR') : '-';
                return `<tr class="hover:bg-orange-50/30 transition-colors">
                    <td class="px-4 py-3 text-center text-lg">${medalha}</td>
                    <td class="px-4 py-3">
                        <p class="font-semibold text-gray-800 text-sm">${c.nome || '-'}</p>
                        <p class="text-xs text-gray-400">${c.email || ''}</p>
                    </td>
                    <td class="px-4 py-3 text-sm text-gray-600">${c.telefone || '-'}</td>
                    <td class="px-4 py-3 text-center"><span class="bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full text-xs font-bold">${c.total_pedidos}</span></td>
                    <td class="px-4 py-3 text-right font-bold text-sm text-gray-800">${fmtR$(c.total_gasto)}</td>
                    <td class="px-4 py-3 text-right text-xs text-gray-500">${ultimo}</td>
                </tr>`;
            }).join('');
        }
    } catch (e) { console.error('Erro top clientes:', e); }
}

async function carregarTopProdutos() {
    try {
        const resp = await fetch(`${API_URL}/admin/relatorios/produtos-vendidos`, { headers: adminHeaders(), credentials: 'include' });
        const data = await resp.json();
        if (data.success) {
            const container = document.getElementById('top-produtos');
            const produtos = data.produtos.filter(p => p.qtd_vendida > 0).slice(0, 10);
            if (produtos.length === 0) {
                container.innerHTML = '<p class="text-gray-400 text-center py-6">Nenhuma venda registrada</p>';
                return;
            }
            const maxQtd = Math.max(...produtos.map(p => p.qtd_vendida));
            container.innerHTML = produtos.map((p, i) => {
                const pct = (p.qtd_vendida / maxQtd * 100).toFixed(0);
                const catCor = p.categoria === 'Salgados' ? 'bg-amber-400' : p.categoria === 'Doces' ? 'bg-pink-400' : p.categoria === 'Bebidas' ? 'bg-blue-400' : 'bg-gray-400';
                return `<div class="flex items-center gap-3">
                    <span class="text-xs font-bold text-gray-400 w-5 text-right">${i + 1}</span>
                    <div class="flex-1">
                        <div class="flex justify-between items-center mb-1">
                            <span class="text-sm font-semibold text-gray-800">${p.nome}</span>
                            <span class="text-xs text-gray-500">${p.qtd_vendida} un · ${fmtR$(p.faturamento)}</span>
                        </div>
                        <div class="w-full bg-gray-100 rounded-full h-2">
                            <div class="${catCor} h-2 rounded-full transition-all" style="width: ${pct}%"></div>
                        </div>
                    </div>
                </div>`;
            }).join('');
        }
    } catch (e) { console.error('Erro top produtos:', e); }
}


// ==================== CRUD CLIENTES ====================

let todosClientes = [];
let clienteExcluirId = null;

async function carregarClientesAdmin() {
    try {
        const resp = await fetch(`${API_URL}/admin/clientes`, { headers: adminHeaders(), credentials: 'include' });
        const data = await resp.json();
        if (data.success) {
            todosClientes = data.clientes || [];
            filtrarClientes();
        } else {
            showToast('error', 'Erro', data.error || 'Erro ao carregar clientes');
        }
    } catch (e) {
        console.error('Erro ao carregar clientes:', e);
        showToast('error', 'Erro', 'Falha ao carregar clientes');
    }
}

function filtrarClientes() {
    const busca = (document.getElementById('busca-cliente')?.value || '').toLowerCase();
    const filtrados = todosClientes.filter(c => {
        const nome = (c.nome || '').toLowerCase();
        const email = (c.email || '').toLowerCase();
        const tel = (c.telefone || '');
        return nome.includes(busca) || email.includes(busca) || tel.includes(busca);
    });
    document.getElementById('total-clientes').textContent = filtrados.length;
    renderizarTabelaClientes(filtrados);
}

function renderizarTabelaClientes(clientes) {
    const tbody = document.getElementById('tabela-clientes');
    if (!tbody) return;

    if (clientes.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-gray-400"><i class="fas fa-users text-3xl mb-2 block"></i>Nenhum cliente encontrado</td></tr>`;
        return;
    }

    tbody.innerHTML = clientes.map(c => {
        const dataCadastro = c.created_at ? new Date(c.created_at).toLocaleDateString('pt-BR') : '-';
        const tel = formatarTelefoneAdmin(c.telefone);
        return `
            <tr class="hover:bg-gray-50 transition-colors">
                <td class="px-4 py-3">
                    <div class="flex items-center gap-3">
                        <div class="w-9 h-9 rounded-full bg-orange-100 flex items-center justify-center flex-shrink-0">
                            <span class="text-orange-600 font-bold text-sm">${(c.nome || '?')[0].toUpperCase()}</span>
                        </div>
                        <div class="min-w-0">
                            <p class="font-semibold text-gray-800 truncate">${c.nome || '-'}</p>
                            <p class="text-xs text-gray-400 sm:hidden">${c.email || '-'}</p>
                        </div>
                    </div>
                </td>
                <td class="px-4 py-3 text-gray-600 hidden sm:table-cell">${c.email || '-'}</td>
                <td class="px-4 py-3 text-gray-600 hidden md:table-cell">${tel}</td>
                <td class="px-4 py-3 text-gray-500 text-xs hidden lg:table-cell">${dataCadastro}</td>
                <td class="px-4 py-3 hidden lg:table-cell">
                    <span class="text-xs font-semibold text-gray-600">${c.total_pedidos || 0} pedidos</span>
                    <span class="text-xs text-gray-400 block">R$ ${(c.total_gasto || 0).toFixed(2).replace('.', ',')}</span>
                </td>
                <td class="px-4 py-3 text-center">
                    <div class="flex justify-center gap-1">
                        <button onclick="abrirModalCliente(${c.id})" class="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Editar">
                            <i class="fas fa-pen text-xs"></i>
                        </button>
                        <button onclick="pedirExclusaoCliente(${c.id})" class="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Excluir">
                            <i class="fas fa-trash text-xs"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function formatarTelefoneAdmin(tel) {
    if (!tel) return '-';
    let d = tel.replace(/\D/g, '');
    if (d.length >= 12 && d.startsWith('55')) d = d.substring(2);
    if (d.length === 11) return `(${d.slice(0,2)}) ${d.slice(2,7)}-${d.slice(7)}`;
    if (d.length === 10) return `(${d.slice(0,2)}) ${d.slice(2,6)}-${d.slice(6)}`;
    return tel;
}

async function abrirModalCliente(id = null) {
    document.getElementById('cliente-id').value = '';
    document.getElementById('cliente-nome').value = '';
    document.getElementById('cliente-email').value = '';
    document.getElementById('cliente-telefone').value = '';
    document.getElementById('cliente-nascimento').value = '';
    document.getElementById('cliente-senha').value = '';

    if (id) {
        document.getElementById('modal-cliente-titulo').textContent = 'Editar Cliente';
        document.getElementById('cliente-senha').placeholder = 'Deixe em branco para manter a atual';
        try {
            const resp = await fetch(`${API_URL}/admin/cliente/${id}`, { headers: adminHeaders(), credentials: 'include' });
            const data = await resp.json();
            if (data.success) {
                const c = data.cliente;
                document.getElementById('cliente-id').value = c.id;
                document.getElementById('cliente-nome').value = c.nome || '';
                document.getElementById('cliente-email').value = c.email || '';
                document.getElementById('cliente-telefone').value = formatarTelefoneAdmin(c.telefone);
                document.getElementById('cliente-nascimento').value = c.data_nascimento || '';
            }
        } catch (e) {
            showToast('error', 'Erro', 'Não foi possível carregar dados do cliente');
            return;
        }
    } else {
        document.getElementById('modal-cliente-titulo').textContent = 'Novo Cliente';
        document.getElementById('cliente-senha').placeholder = 'Deixe em branco para gerar automaticamente';
    }
    document.getElementById('modal-cliente').classList.remove('hidden');
}

function fecharModalCliente() {
    document.getElementById('modal-cliente').classList.add('hidden');
}

async function salvarCliente() {
    const id = document.getElementById('cliente-id').value;
    const dados = {
        nome: document.getElementById('cliente-nome').value.trim(),
        email: document.getElementById('cliente-email').value.trim(),
        telefone: document.getElementById('cliente-telefone').value.trim(),
        data_nascimento: document.getElementById('cliente-nascimento').value || null,
        senha: document.getElementById('cliente-senha').value.trim()
    };

    if (!dados.nome || !dados.email) {
        showToast('error', 'Erro', 'Nome e email são obrigatórios');
        return;
    }

    const url = id ? `${API_URL}/admin/cliente/${id}` : `${API_URL}/admin/cliente`;
    const method = id ? 'PUT' : 'POST';

    try {
        const resp = await fetch(url, {
            method,
            headers: { ...adminHeaders(), 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(dados)
        });
        const data = await resp.json();
        if (data.success) {
            fecharModalCliente();
            carregarClientesAdmin();
            const msg = id ? 'Cliente atualizado' : 'Cliente criado';
            if (!id && data.senha_gerada) {
                showToast('success', msg, `Senha gerada: ${data.senha_gerada}`);
            } else {
                showToast('success', msg, '');
            }
        } else {
            showToast('error', 'Erro', data.error || 'Falha ao salvar');
        }
    } catch (e) {
        showToast('error', 'Erro', 'Falha na comunicação com o servidor');
    }
}

function pedirExclusaoCliente(id) {
    clienteExcluirId = id;
    document.getElementById('modal-excluir-cliente').classList.remove('hidden');
}

async function confirmarExclusaoCliente() {
    if (!clienteExcluirId) return;
    try {
        const resp = await fetch(`${API_URL}/admin/cliente/${clienteExcluirId}`, {
            method: 'DELETE',
            headers: adminHeaders(),
            credentials: 'include'
        });
        const data = await resp.json();
        if (data.success) {
            showToast('success', 'Cliente excluído', '');
            carregarClientesAdmin();
        } else {
            showToast('error', 'Erro', data.error || 'Falha ao excluir');
        }
    } catch (e) {
        showToast('error', 'Erro', 'Falha na comunicação com o servidor');
    }
    clienteExcluirId = null;
    document.getElementById('modal-excluir-cliente').classList.add('hidden');
}
