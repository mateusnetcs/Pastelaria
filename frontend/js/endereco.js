/**
 * Funções do Modal de Endereço de Entrega
 * Gerencia o formulário de endereço e processamento de pedidos
 */

/**
 * Mostra o modal de endereço de entrega
 */
function mostrarModalEndereco() {
    const modal = document.getElementById('endereco-modal');
    if (!modal) return;
    
    modal.classList.remove('hidden');
    
    const retiradaInput = document.getElementById('retirada-local');
    const entregaInput = document.getElementById('entrega-domicilio');
    const form = document.getElementById('endereco-form');
    
    const salvo = JSON.parse(localStorage.getItem('endereco_cliente') || 'null');
    
    if (salvo && !salvo.retirada_local && salvo.rua) {
        if (entregaInput) entregaInput.checked = true;
        if (retiradaInput) retiradaInput.checked = false;
        if (form) form.classList.remove('hidden');
        document.getElementById('endereco-rua').value = salvo.rua || '';
        document.getElementById('endereco-numero').value = salvo.numero || '';
        document.getElementById('endereco-complemento').value = salvo.complemento || '';
        document.getElementById('endereco-bairro').value = salvo.bairro || '';
        document.getElementById('endereco-outro').value = salvo.outro || '';
    } else {
        if (retiradaInput) retiradaInput.checked = true;
        if (entregaInput) entregaInput.checked = false;
        if (form) form.classList.add('hidden');
        document.getElementById('endereco-rua').value = '';
        document.getElementById('endereco-numero').value = '';
        document.getElementById('endereco-complemento').value = '';
        document.getElementById('endereco-bairro').value = '';
        document.getElementById('endereco-outro').value = '';
    }
}

/**
 * Fecha o modal de endereço
 */
function fecharModalEndereco() {
    const modal = document.getElementById('endereco-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * Confirma o endereço e processa o pedido
 */
function confirmarEndereco() {
    const tipoEntregaInput = document.querySelector('input[name="tipo-entrega"]:checked');
    if (!tipoEntregaInput) return;
    
    const tipoEntrega = tipoEntregaInput.value;
    let endereco_entrega;
    
    if (tipoEntrega === 'retirada') {
        endereco_entrega = {
            retirada_local: true,
            rua: 'Retirada no Local',
            numero: '',
            complemento: '',
            bairro: '',
            outro: '',
            telefone: usuario ? (usuario.telefone || '') : ''
        };
    } else {
        const rua = document.getElementById('endereco-rua').value.trim();
        const numero = document.getElementById('endereco-numero').value.trim();
        const bairro = document.getElementById('endereco-bairro').value.trim();
        
        // Validação dos campos obrigatórios
        if (!rua) {
            showToast('error', 'Campo obrigatório', 'Por favor, preencha o nome da rua');
            return;
        }
        if (!numero) {
            showToast('error', 'Campo obrigatório', 'Por favor, preencha o número');
            return;
        }
        if (!bairro) {
            showToast('error', 'Campo obrigatório', 'Por favor, preencha o bairro');
            return;
        }
        
        endereco_entrega = {
            retirada_local: false,
            rua: rua,
            numero: numero,
            complemento: document.getElementById('endereco-complemento').value.trim() || '',
            bairro: bairro,
            outro: document.getElementById('endereco-outro').value.trim() || '',
            telefone: usuario ? (usuario.telefone || '') : ''
        };
    }
    
    localStorage.setItem('endereco_cliente', JSON.stringify(endereco_entrega));
    
    fecharModalEndereco();
    mostrarModalMetodoPagamento(endereco_entrega);
}

/**
 * Inicia o processo de finalização do pedido
 */
async function finalizarPedido() {
    if (!usuario) {
        showToast('error', 'Login necessário', 'Por favor, faça login para finalizar o pedido');
        showLoginModal();
        return;
    }

    if (carrinho.length === 0) {
        showToast('error', 'Carrinho vazio', 'Adicione produtos ao carrinho antes de finalizar');
        return;
    }

    mostrarModalEndereco();
}

/**
 * Mostra modal de seleção de método de pagamento
 * @param {Object} endereco_entrega - Dados do endereço de entrega
 */
function mostrarModalMetodoPagamento(endereco_entrega) {
    const modal = document.getElementById('metodo-pagamento-modal');
    if (!modal) return;
    
    // Salvar endereço temporariamente
    window.enderecoEntregaTemp = endereco_entrega;
    
    modal.classList.remove('hidden');
}

/**
 * Fecha modal de método de pagamento
 */
function fecharModalMetodoPagamento() {
    const modal = document.getElementById('metodo-pagamento-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
    window.enderecoEntregaTemp = null;
}

/**
 * Seleciona método de pagamento
 * @param {string} metodo - 'dinheiro', 'pix' ou 'cartao'
 */
function selecionarMetodoPagamento(metodo) {
    if (!window.enderecoEntregaTemp) return;
    
    if (metodo === 'dinheiro') {
        mostrarModalDinheiro();
    } else if (metodo === 'pix') {
        fecharModalMetodoPagamento();
        processarPedido(window.enderecoEntregaTemp, 'pix');
    } else if (metodo === 'cartao') {
        fecharModalMetodoPagamento();
        processarPedido(window.enderecoEntregaTemp, 'cartao');
    }
}

/**
 * Mostra modal para pagamento em dinheiro
 */
function mostrarModalDinheiro() {
    const modal = document.getElementById('dinheiro-modal');
    if (!modal) return;
    
    // Calcular total
    const total = carrinho.reduce((sum, item) => sum + (item.preco * item.quantidade), 0);
    document.getElementById('dinheiro-total').textContent = `R$ ${total.toFixed(2).replace('.', ',')}`;
    document.getElementById('dinheiro-troco').value = '';
    document.getElementById('dinheiro-troco-resultado').textContent = 'R$ 0,00';
    document.getElementById('dinheiro-troco-resultado').className = 'text-green-600 font-bold text-lg';
    
    fecharModalMetodoPagamento();
    modal.classList.remove('hidden');
}

/**
 * Fecha modal de dinheiro
 */
function fecharModalDinheiro() {
    const modal = document.getElementById('dinheiro-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
}

/**
 * Calcula troco
 */
function calcularTroco() {
    const total = carrinho.reduce((sum, item) => sum + (item.preco * item.quantidade), 0);
    const valorRecebido = parseFloat(document.getElementById('dinheiro-troco').value) || 0;
    const troco = valorRecebido - total;
    
    const resultadoEl = document.getElementById('dinheiro-troco-resultado');
    if (troco < 0) {
        resultadoEl.textContent = `Faltam R$ ${Math.abs(troco).toFixed(2).replace('.', ',')}`;
        resultadoEl.className = 'text-red-600 font-bold text-lg';
    } else {
        resultadoEl.textContent = `R$ ${troco.toFixed(2).replace('.', ',')}`;
        resultadoEl.className = 'text-green-600 font-bold text-lg';
    }
}

/**
 * Confirma pagamento em dinheiro
 */
function confirmarPagamentoDinheiro() {
    const valorRecebido = parseFloat(document.getElementById('dinheiro-troco').value) || 0;
    const total = carrinho.reduce((sum, item) => sum + (item.preco * item.quantidade), 0);
    
    if (valorRecebido < total) {
        showToast('error', 'Valor insuficiente', 'O valor recebido deve ser maior ou igual ao total');
        return;
    }
    
    fecharModalDinheiro();
    processarPedido(window.enderecoEntregaTemp, 'dinheiro', valorRecebido);
}

/**
 * Processa o pedido e redireciona para pagamento
 * @param {Object} endereco_entrega - Dados do endereço de entrega
 * @param {string} metodo_pagamento - Método de pagamento ('dinheiro', 'pix', 'cartao')
 * @param {number} valor_recebido - Valor recebido (apenas para dinheiro)
 */
async function processarPedido(endereco_entrega, metodo_pagamento = 'pix', valor_recebido = null) {
    try {
        showToast('info', 'Processando pedido...', 'Aguarde enquanto processamos seu pedido');
        
        const body = {
            itens: carrinho.map(item => ({
                produto_id: item.produto_id,
                quantidade: item.quantidade
            })),
            endereco_entrega,
            metodo_pagamento
        };
        
        if (metodo_pagamento === 'dinheiro' && valor_recebido) {
            body.valor_recebido = valor_recebido;
        }
        
        const response = await fetch(`${API_URL}/pedido`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify(body)
        });
        
        const data = await response.json();
        
        if (data.success) {
            if (metodo_pagamento === 'dinheiro') {
                // Pagamento em dinheiro - pedido já está pago
                showToast('success', 'Pedido confirmado!', 'Seu pedido será preparado em breve');
                carrinho = [];
                salvarCarrinho();
                atualizarCarrinho();
                // Fechar carrinho se estiver aberto
                if (typeof toggleCarrinho === 'function') {
                    const sidebar = document.getElementById('carrinho-sidebar');
                    if (sidebar && !sidebar.classList.contains('translate-x-full')) {
                        toggleCarrinho();
                    }
                }
            } else if (metodo_pagamento === 'pix') {
                // Pagamento Pix - mostrar modal com QR code
                mostrarModalPagamento(data);
            } else if (metodo_pagamento === 'cartao') {
                // Pagamento cartão - redirecionar para Mercado Pago
                if (data.link_pagamento) {
                    window.location.href = data.link_pagamento;
                } else {
                    showToast('error', 'Erro ao gerar pagamento', 'Tente novamente');
                }
            }
        } else {
            showToast('error', 'Erro ao criar pedido', data.error);
        }
    } catch (error) {
        showToast('error', 'Erro ao finalizar pedido', error.message);
    }
}
