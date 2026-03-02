/**
 * Funções de Acompanhamento de Pedidos
 * Gerencia exibição de pedidos e cronômetro
 */

// Variáveis globais
let pedidosInterval = null;
let cronometros = {};

/**
 * Toggle do sidebar de pedidos
 */
function togglePedidos() {
    const sidebar = document.getElementById('pedidos-sidebar');
    if (!sidebar) return;
    
    sidebar.classList.toggle('translate-x-full');
    
    // Se abrindo, carregar pedidos
    if (!sidebar.classList.contains('translate-x-full')) {
        carregarPedidos();
    } else {
        // Se fechando, parar verificações
        if (pedidosInterval) {
            clearInterval(pedidosInterval);
            pedidosInterval = null;
        }
    }
}

/**
 * Carrega pedidos do usuário
 */
async function carregarPedidos() {
    try {
        const response = await fetch(`${API_URL}/pedidos`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                renderizarPedidos(data.pedidos || []);
                iniciarVerificacaoPedidos();
            }
        } else if (response.status === 401) {
            // Não autenticado
            document.getElementById('pedidos-container').innerHTML = `
                <div class="text-center py-8">
                    <i class="fas fa-lock text-gray-400 text-4xl mb-4"></i>
                    <p class="text-gray-600">Faça login para acompanhar seus pedidos</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Erro ao carregar pedidos:', error);
    }
}

/**
 * Renderiza lista de pedidos
 */
function renderizarPedidos(pedidos) {
    const container = document.getElementById('pedidos-container');
    if (!container) return;
    
    if (pedidos.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8">
                <i class="fas fa-shopping-bag text-gray-400 text-4xl mb-4"></i>
                <p class="text-gray-600">Você ainda não fez nenhum pedido</p>
            </div>
        `;
        return;
    }
    
    // Ordenar pedidos: mais recentes primeiro
    pedidos.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
    
    container.innerHTML = pedidos.map(pedido => {
        const status = getStatusPedido(pedido.status);
        const dataPedido = new Date(pedido.created_at);
        const tempoRestante = calcularTempoRestante(pedido);
        
        return `
            <div class="border-b border-gray-200 pb-4 mb-4 last:border-0">
                <div class="flex justify-between items-start mb-2">
                    <div>
                        <h3 class="font-bold text-lg">Pedido #${pedido.id}</h3>
                        <p class="text-sm text-gray-500">${formatarData(dataPedido)}</p>
                    </div>
                    <span class="px-3 py-1 rounded-full text-xs font-semibold ${status.class}">
                        ${status.label}
                    </span>
                </div>
                
                <div class="mb-3">
                    <p class="text-gray-700 font-semibold">Total: R$ ${parseFloat(pedido.total).toFixed(2).replace('.', ',')}</p>
                </div>
                
                ${pedido.status === 'pago' || pedido.status === 'preparando' ? `
                    <div class="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-2">
                        <div class="flex items-center justify-between">
                            <span class="text-sm text-orange-800 font-semibold">
                                <i class="fas fa-clock mr-2"></i>
                                Tempo estimado:
                            </span>
                            <span id="cronometro-${pedido.id}" class="text-lg font-bold text-orange-600">
                                ${tempoRestante}
                            </span>
                        </div>
                    </div>
                ` : ''}
                
                ${pedido.status === 'pendente' ? `
                    <div class="flex gap-2 mt-3">
                        <button onclick="pagarPedido(${pedido.id})" class="flex-1 bg-orange-600 text-white py-2 px-4 rounded-lg font-semibold hover:bg-orange-700 transition text-sm">
                            <i class="fas fa-qrcode mr-2"></i>
                            Pagar
                        </button>
                        <button onclick="cancelarPedido(${pedido.id}, 'R$ ${parseFloat(pedido.total).toFixed(2).replace('.', ',')}')" class="flex-1 bg-red-600 text-white py-2 px-4 rounded-lg font-semibold hover:bg-red-700 transition text-sm">
                            <i class="fas fa-trash mr-2"></i>
                            Não quero mais
                        </button>
                    </div>
                ` : ''}
                
                ${pedido.observacoes ? `
                    <div class="text-sm text-gray-600 mt-2">
                        <i class="fas fa-map-marker-alt mr-1"></i>
                        ${formatarEndereco(pedido.observacoes)}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
    
    // Iniciar cronômetros
    iniciarCronometros(pedidos);
}

/**
 * Obtém informações de status do pedido
 */
function getStatusPedido(status) {
    const statusMap = {
        'pendente': { label: 'Aguardando Pagamento', class: 'bg-yellow-100 text-yellow-800' },
        'pago': { label: 'Em Preparação', class: 'bg-blue-100 text-blue-800' },
        'preparando': { label: 'Em Preparação', class: 'bg-blue-100 text-blue-800' },
        'pronto': { label: 'Pronto', class: 'bg-green-100 text-green-800' },
        'entregue': { label: 'Entregue', class: 'bg-gray-100 text-gray-800' },
        'cancelado': { label: 'Cancelado', class: 'bg-red-100 text-red-800' }
    };
    
    return statusMap[status] || { label: status, class: 'bg-gray-100 text-gray-800' };
}

/**
 * Calcula tempo restante para o pedido (60 minutos a partir da criação)
 */
function calcularTempoRestante(pedido) {
    if (pedido.status !== 'pago' && pedido.status !== 'preparando') {
        return '--:--';
    }
    
    // Sempre contar desde a criação do pedido (created_at)
    const dataPedido = new Date(pedido.created_at);
    const agora = new Date();
    const tempoDecorrido = agora - dataPedido; // em milissegundos
    const sessentaMinutos = 60 * 60 * 1000; // 60 minutos em milissegundos
    const tempoRestante = sessentaMinutos - tempoDecorrido;
    
    if (tempoRestante <= 0) {
        return '00:00';
    }
    
    const minutos = Math.floor(tempoRestante / (60 * 1000));
    const segundos = Math.floor((tempoRestante % (60 * 1000)) / 1000);
    
    return `${String(minutos).padStart(2, '0')}:${String(segundos).padStart(2, '0')}`;
}

/**
 * Inicia cronômetros para pedidos em preparação
 */
function iniciarCronometros(pedidos) {
    // Limpar cronômetros anteriores
    Object.keys(cronometros).forEach(id => {
        clearInterval(cronometros[id]);
        delete cronometros[id];
    });
    
    // Iniciar novos cronômetros
    pedidos.forEach(pedido => {
        if (pedido.status === 'pago' || pedido.status === 'preparando') {
            const cronometroEl = document.getElementById(`cronometro-${pedido.id}`);
            if (cronometroEl) {
                // Atualizar imediatamente
                cronometroEl.textContent = calcularTempoRestante(pedido);
                
                // Atualizar a cada segundo
                cronometros[pedido.id] = setInterval(() => {
                    const tempo = calcularTempoRestante(pedido);
                    cronometroEl.textContent = tempo;
                    
                    // Se tempo acabou, parar cronômetro
                    if (tempo === '00:00') {
                        clearInterval(cronometros[pedido.id]);
                        delete cronometros[pedido.id];
                    }
                }, 1000);
            }
        }
    });
}

/**
 * Inicia verificação periódica de pedidos
 */
function iniciarVerificacaoPedidos() {
    // Parar verificação anterior
    if (pedidosInterval) {
        clearInterval(pedidosInterval);
    }
    
    // Verificar a cada 30 segundos
    pedidosInterval = setInterval(() => {
        carregarPedidos();
    }, 30000);
}

/**
 * Formata data para exibição
 */
function formatarData(data) {
    const agora = new Date();
    const diff = agora - data;
    const minutos = Math.floor(diff / 60000);
    
    if (minutos < 1) return 'Agora mesmo';
    if (minutos < 60) return `Há ${minutos} minuto${minutos > 1 ? 's' : ''}`;
    
    const horas = Math.floor(minutos / 60);
    if (horas < 24) return `Há ${horas} hora${horas > 1 ? 's' : ''}`;
    
    const dias = Math.floor(horas / 24);
    return `Há ${dias} dia${dias > 1 ? 's' : ''}`;
}

/**
 * Formata endereço para exibição
 */
function formatarEndereco(observacoes) {
    try {
        const endereco = typeof observacoes === 'string' ? JSON.parse(observacoes) : observacoes;
        
        if (endereco.retirada_local) {
            return 'Retirada no local';
        }
        
        let enderecoFormatado = '';
        if (endereco.rua) enderecoFormatado += endereco.rua;
        if (endereco.numero) enderecoFormatado += `, ${endereco.numero}`;
        if (endereco.complemento) enderecoFormatado += ` - ${endereco.complemento}`;
        if (endereco.bairro) enderecoFormatado += `, ${endereco.bairro}`;
        
        return enderecoFormatado || 'Endereço não informado';
    } catch (e) {
        return observacoes || 'Endereço não informado';
    }
}

/**
 * Gera QR code de pagamento para pedido pendente
 */
async function pagarPedido(pedidoId) {
    try {
        showToast('info', 'Gerando pagamento...', 'Aguarde um momento');
        
        const response = await fetch(`${API_URL}/pedido/${pedidoId}/pagar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                // Fechar sidebar de pedidos
                togglePedidos();
                
                // Mostrar modal de pagamento
                if (typeof mostrarModalPagamento === 'function') {
                    mostrarModalPagamento(data);
                } else {
                    showToast('success', 'QR Code gerado!', 'Verifique o modal de pagamento');
                }
            } else {
                showToast('error', 'Erro ao gerar pagamento', data.error || 'Tente novamente');
            }
        } else {
            const error = await response.json();
            showToast('error', 'Erro ao gerar pagamento', error.error || 'Tente novamente');
        }
    } catch (error) {
        console.error('Erro ao pagar pedido:', error);
        showToast('error', 'Erro ao gerar pagamento', 'Verifique sua conexão');
    }
}

/**
 * Cancela um pedido pendente
 */
// Variável global para armazenar o ID do pedido a ser excluído
let pedidoParaExcluir = null;
let pedidoParaExcluirTotal = null;

/**
 * Abre modal de confirmação de exclusão
 * @param {number} pedidoId - ID do pedido
 * @param {string} total - Total do pedido formatado
 */
function mostrarModalExclusao(pedidoId, total) {
    // Validar parâmetros
    if (!pedidoId) {
        console.error('Erro: pedidoId não fornecido');
        showToast('error', 'Erro', 'ID do pedido inválido');
        return;
    }
    
    // Converter para número se necessário
    pedidoParaExcluir = parseInt(pedidoId);
    pedidoParaExcluirTotal = total;
    
    const modal = document.getElementById('confirmar-exclusao-modal');
    const pedidoIdEl = document.getElementById('exclusao-pedido-id');
    const pedidoTotalEl = document.getElementById('exclusao-pedido-total');
    
    if (modal && pedidoIdEl && pedidoTotalEl) {
        pedidoIdEl.textContent = pedidoParaExcluir;
        pedidoTotalEl.textContent = total || 'R$ 0,00';
        modal.classList.remove('hidden');
    } else {
        console.error('Erro: elementos do modal não encontrados');
    }
}

/**
 * Fecha modal de exclusão
 */
function fecharModalExclusao() {
    const modal = document.getElementById('confirmar-exclusao-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
    pedidoParaExcluir = null;
    pedidoParaExcluirTotal = null;
}

/**
 * Confirma e executa a exclusão do pedido
 */
async function confirmarExclusaoPedido() {
    if (!pedidoParaExcluir) {
        console.error('Erro: pedidoParaExcluir está null');
        showToast('error', 'Erro', 'ID do pedido não encontrado');
        return;
    }
    
    // Salvar o ID antes de fechar o modal
    const pedidoId = pedidoParaExcluir;
    
    // Fechar modal
    fecharModalExclusao();
    
    try {
        showToast('info', 'Excluindo pedido...', 'Aguarde');
        
        const response = await fetch(`${API_URL}/pedido/${pedidoId}/cancelar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include'
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                showToast('success', 'Pedido excluído', 'O pedido foi excluído com sucesso');
                // Recarregar pedidos (o pedido não aparecerá mais na lista)
                carregarPedidos();
            } else {
                showToast('error', 'Erro ao excluir', data.error || 'Tente novamente');
            }
        } else {
            const error = await response.json();
            showToast('error', 'Erro ao excluir', error.error || 'Tente novamente');
        }
    } catch (error) {
        console.error('Erro ao excluir pedido:', error);
        showToast('error', 'Erro ao excluir', 'Verifique sua conexão');
    }
}

/**
 * Função chamada quando usuário clica em "Não quero mais"
 * @param {number} pedidoId - ID do pedido
 * @param {string} total - Total do pedido formatado
 */
function cancelarPedido(pedidoId, total) {
    mostrarModalExclusao(pedidoId, total);
}
