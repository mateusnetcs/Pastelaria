/**
 * Arquivo Principal - Inicialização
 * Coordena a inicialização da aplicação
 */

// Variáveis globais
let produtos = [];
let carrinho = JSON.parse(localStorage.getItem('carrinho') || '[]');
let usuario = JSON.parse(localStorage.getItem('usuario') || 'null');

/**
 * Atualiza a interface baseado no estado do usuário
 */
function updateUI() {
    const userMenu = document.getElementById('user-menu');
    const loginButtons = document.getElementById('login-buttons');
    const userName = document.getElementById('user-name');
    const userMenuMobile = document.getElementById('user-menu-mobile');
    const loginButtonsMobile = document.getElementById('login-buttons-mobile');
    const userNameMobile = document.getElementById('user-name-mobile');
    const mobileLogado = document.getElementById('mobile-user-logado');
    const mobileDeslogado = document.getElementById('mobile-user-deslogado');
    const userNameHeader = document.getElementById('user-name-header');
    
    if (usuario) {
        if (userMenu) userMenu.classList.remove('hidden');
        if (loginButtons) loginButtons.classList.add('hidden');
        if (userName) userName.textContent = usuario.nome;
        if (userMenuMobile) userMenuMobile.classList.remove('hidden');
        if (loginButtonsMobile) loginButtonsMobile.classList.add('hidden');
        if (userNameMobile) userNameMobile.textContent = usuario.nome;
        if (mobileLogado) mobileLogado.classList.remove('hidden');
        if (mobileDeslogado) mobileDeslogado.classList.add('hidden');
        if (userNameHeader) userNameHeader.textContent = usuario.nome.split(' ')[0];
    } else {
        if (userMenu) userMenu.classList.add('hidden');
        if (loginButtons) loginButtons.classList.remove('hidden');
        if (userMenuMobile) userMenuMobile.classList.add('hidden');
        if (loginButtonsMobile) loginButtonsMobile.classList.remove('hidden');
        if (mobileLogado) mobileLogado.classList.add('hidden');
        if (mobileDeslogado) mobileDeslogado.classList.remove('hidden');
    }
}

function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    if (menu) menu.classList.toggle('hidden');
}

/**
 * Verifica status de pagamento na URL
 */
function verificarStatusPagamento() {
    const urlParams = new URLSearchParams(window.location.search);
    const status = urlParams.get('status');
    
    if (status) {
        if (status === 'success') {
            showToast('success', 'Pagamento aprovado!', 'Seu pedido será preparado em breve.');
            carrinho = [];
            salvarCarrinho();
            atualizarCarrinho();
        } else if (status === 'failure') {
            showToast('error', 'Pagamento não aprovado', 'Tente novamente ou escolha outra forma de pagamento.');
        }
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

/**
 * Inicialização quando o DOM estiver pronto
 */
async function restaurarSessao() {
    if (!usuario) return;
    try {
        const resp = await fetch(`${API_URL}/me`, { credentials: 'include' });
        if (resp.ok) {
            const data = await resp.json();
            if (data.success && data.user) {
                usuario = data.user;
                localStorage.setItem('usuario', JSON.stringify(usuario));
                updateUI();
                return;
            }
        }
        if (usuario.email) {
            const resp2 = await fetch(`${API_URL}/auto-login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ user_id: usuario.id, email: usuario.email })
            });
            if (resp2.ok) {
                const data2 = await resp2.json();
                if (data2.success) {
                    usuario = data2.user;
                    localStorage.setItem('usuario', JSON.stringify(usuario));
                    updateUI();
                    return;
                }
            }
        }
    } catch (e) {
        console.warn('Erro ao restaurar sessão:', e);
    }
}

window.addEventListener('DOMContentLoaded', async () => {
    updateUI();
    atualizarCarrinho();
    verificarStatusPagamento();
    
    try {
        const portaDetectada = await detectarPortaBackend();
        if (portaDetectada) {
            console.log('Porta detectada, carregando produtos...');
        } else {
            console.warn('Porta não detectada, tentando carregar produtos mesmo assim...');
        }
    } catch (error) {
        console.warn('Erro ao detectar porta:', error);
    }
    
    restaurarSessao();
    carregarProdutos();
});
