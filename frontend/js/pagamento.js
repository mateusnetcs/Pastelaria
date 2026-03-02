/**
 * Funções de Pagamento e QR Code
 * Gerencia exibição de QR code e verificação de status
 */

// Variáveis globais do pagamento
let pagamentoData = null;
let verificarPagamentoInterval = null;

/**
 * Mostra o modal de pagamento com QR code
 * @param {Object} data - Dados do pagamento (qr_code, total, pedido_id, etc)
 */
function mostrarModalPagamento(data) {
    pagamentoData = data;
    
    const modal = document.getElementById('pagamento-modal');
    if (!modal) return;
    
    modal.classList.remove('hidden');
    
    // Atualizar informações
    const totalEl = document.getElementById('pagamento-total');
    const pedidoIdEl = document.getElementById('pagamento-pedido-id');
    let qrCodeImg = document.getElementById('qr-code-image');
    const pixCodeInput = document.getElementById('pix-code');
    
    if (totalEl) {
        totalEl.textContent = `R$ ${parseFloat(data.total || 0).toFixed(2).replace('.', ',')}`;
    }
    
    if (pedidoIdEl) {
        pedidoIdEl.textContent = data.pedido_id || '-';
    }
    
    // Exibir QR code
    const container = document.getElementById('qr-code-container');
    
    // Limpar container antes de adicionar novo conteúdo
    if (container) {
        container.innerHTML = '';
        const img = document.createElement('img');
        img.id = 'qr-code-image';
        img.alt = 'QR Code';
        img.className = 'w-64 h-64 mx-auto';
        container.appendChild(img);
        qrCodeImg = img;
    }
    
    if (data.qr_code_base64) {
        // QR code em base64 (preferencial - Pix direto)
        qrCodeImg.src = `data:image/png;base64,${data.qr_code_base64}`;
        qrCodeImg.style.display = 'block';
        qrCodeImg.onerror = function() {
            // Se base64 falhar, tentar gerar a partir do código
            if (data.qr_code) {
                const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=${encodeURIComponent(data.qr_code)}`;
                qrCodeImg.src = qrCodeUrl;
            } else if (data.link_pagamento) {
                const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=${encodeURIComponent(data.link_pagamento)}`;
                qrCodeImg.src = qrCodeUrl;
            }
        };
    } else if (data.qr_code) {
        // Gerar QR code a partir do código Pix usando API externa
        const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=${encodeURIComponent(data.qr_code)}`;
        qrCodeImg.src = qrCodeUrl;
        qrCodeImg.style.display = 'block';
    } else if (data.link_pagamento) {
        // Sempre gerar QR code a partir do link de pagamento
        // Cliente escaneia e é redirecionado para escolher método de pagamento
        const qrCodeUrl = `https://api.qrserver.com/v1/create-qr-code/?size=256x256&data=${encodeURIComponent(data.link_pagamento)}`;
        qrCodeImg.src = qrCodeUrl;
        qrCodeImg.style.display = 'block';
        
        if (container) {
            const info = document.createElement('p');
            info.className = 'text-xs text-gray-500 mt-2 text-center';
            info.textContent = 'Escaneie para abrir a página de pagamento do Mercado Pago';
            container.appendChild(info);
        }
    } else {
        // Se não tiver nenhum dado, mostrar mensagem
        if (container) {
            container.innerHTML = '<p class="text-gray-500 py-8 text-center">QR Code não disponível.<br>Use o botão "Pagar no Site" para pagar.</p>';
        }
    }
    
    // Preencher código Pix ou link de pagamento
    if (pixCodeInput) {
        if (data.qr_code) {
            pixCodeInput.value = data.qr_code;
            // Atualizar label
            const label = pixCodeInput.previousElementSibling;
            if (label && label.tagName === 'LABEL') {
                label.textContent = 'Ou copie o código Pix:';
            }
        } else if (data.link_pagamento) {
            pixCodeInput.value = data.link_pagamento;
            // Atualizar label
            const label = pixCodeInput.previousElementSibling;
            if (label && label.tagName === 'LABEL') {
                label.textContent = 'Ou copie o link de pagamento:';
            }
        }
    }
    
    // Iniciar verificação de pagamento (usar payment_id se disponível, senão preference_id)
    const paymentId = data.payment_id || data.preference_id;
    iniciarVerificacaoPagamento(data.pedido_id, paymentId);
}

/**
 * Fecha o modal de pagamento
 */
function fecharModalPagamento() {
    const modal = document.getElementById('pagamento-modal');
    if (modal) {
        modal.classList.add('hidden');
    }
    
    // Parar verificação
    if (verificarPagamentoInterval) {
        clearInterval(verificarPagamentoInterval);
        verificarPagamentoInterval = null;
    }
    
    pagamentoData = null;
}

/**
 * Copia o código Pix para a área de transferência
 */
async function copiarPixCode() {
    const pixCodeInput = document.getElementById('pix-code');
    if (!pixCodeInput || !pixCodeInput.value) {
        showToast('error', 'Erro', 'Código Pix não disponível');
        return;
    }
    
    try {
        await navigator.clipboard.writeText(pixCodeInput.value);
        showToast('success', 'Código copiado!', 'Cole no app do seu banco');
    } catch (error) {
        // Fallback para navegadores antigos
        pixCodeInput.select();
        document.execCommand('copy');
        showToast('success', 'Código copiado!', 'Cole no app do seu banco');
    }
}

/**
 * Abre a página do Mercado Pago em nova aba
 */
function abrirMercadoPago() {
    if (pagamentoData && pagamentoData.link_pagamento) {
        window.open(pagamentoData.link_pagamento, '_blank');
    }
}

/**
 * Inicia verificação periódica do status do pagamento
 * @param {number} pedidoId - ID do pedido
 * @param {string} preferenceId - ID da preferência do Mercado Pago
 */
function iniciarVerificacaoPagamento(pedidoId, preferenceId) {
    // Parar verificação anterior se existir
    if (verificarPagamentoInterval) {
        clearInterval(verificarPagamentoInterval);
    }
    
    // Verificar a cada 5 segundos
    verificarPagamentoInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_URL}/pedido/${pedidoId}/status`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include'
            });
            
            if (response.ok) {
                const data = await response.json();
                
                // Verificar se pagamento foi aprovado
                if (data.aprovado === true || data.status === 'pago' || data.status === 'aprovado' || data.status === 'approved') {
                    clearInterval(verificarPagamentoInterval);
                    verificarPagamentoInterval = null;
                    
                    // Atualizar mensagem no modal
                    const statusMsg = document.getElementById('pagamento-status-msg');
                    if (statusMsg) {
                        statusMsg.innerHTML = '<i class="fas fa-check-circle text-green-500"></i> <span class="text-green-600 font-bold">Pagamento aprovado!</span>';
                    }
                    
                    showToast('success', 'Pagamento aprovado!', 'Seu pedido será preparado em breve.');
                    
                    // Limpar carrinho
                    if (typeof carrinho !== 'undefined') {
                        carrinho = [];
                        if (typeof salvarCarrinho === 'function') {
                            salvarCarrinho();
                        }
                        if (typeof atualizarCarrinho === 'function') {
                            atualizarCarrinho();
                        }
                    }
                    
                    // Fechar modal após 3 segundos
                    setTimeout(() => {
                        fecharModalPagamento();
                        // Redirecionar para página inicial
                        window.location.href = '/?status=success&pedido=' + pedidoId;
                    }, 3000);
                } else if (data.status === 'rejeitado' || data.status === 'rejected') {
                    clearInterval(verificarPagamentoInterval);
                    verificarPagamentoInterval = null;
                    
                    const statusMsg = document.getElementById('pagamento-status-msg');
                    if (statusMsg) {
                        statusMsg.innerHTML = '<i class="fas fa-times-circle text-red-500"></i> <span class="text-red-600">Pagamento rejeitado. Tente novamente.</span>';
                    }
                    
                    showToast('error', 'Pagamento rejeitado', 'Tente realizar o pagamento novamente.');
                }
            }
        } catch (error) {
            console.error('Erro ao verificar pagamento:', error);
        }
    }, 5000); // Verificar a cada 5 segundos
}
