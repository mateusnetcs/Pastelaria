/**
 * Funções de Autenticação
 * Gerencia login, cadastro e logout
 */

/**
 * Processa o login do usuário
 * @param {Event} e - Evento do formulário
 */
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value;
    const senha = document.getElementById('login-senha').value;
    
    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, senha })
        });
        const data = await response.json();
        
        if (data.success) {
            usuario = data.user;
            localStorage.setItem('usuario', JSON.stringify(usuario));
            updateUI();
            closeModals();
            showToast('success', 'Login realizado com sucesso!', `Bem-vindo, ${data.user.nome}!`);
        } else {
            showToast('error', 'Erro no login', data.error);
        }
    } catch (error) {
        showToast('error', 'Erro ao fazer login', error.message);
    }
}

/**
 * Processa o cadastro do usuário
 * @param {Event} e - Evento do formulário
 */
async function handleRegister(e) {
    e.preventDefault();
    const nome = document.getElementById('reg-nome').value;
    const email = document.getElementById('reg-email').value;
    const telefone = document.getElementById('reg-telefone').value;
    const senha = document.getElementById('reg-senha').value;
    
    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ nome, email, telefone, senha })
        });
        const data = await response.json();
        
        if (data.success) {
            usuario = data.user;
            localStorage.setItem('usuario', JSON.stringify(usuario));
            updateUI();
            closeModals();
            showToast('success', 'Cadastro realizado!', `Bem-vindo, ${data.user.nome}!`);
        } else {
            showToast('error', 'Erro no cadastro', data.error);
        }
    } catch (error) {
        showToast('error', 'Erro ao cadastrar', error.message);
    }
}

/**
 * Realiza logout do usuário
 */
async function logout() {
    try {
        await fetch(`${API_URL}/logout`, { method: 'POST', credentials: 'include' });
        usuario = null;
        localStorage.removeItem('usuario');
        updateUI();
        showToast('info', 'Logout realizado', 'Você saiu da sua conta');
    } catch (error) {
        console.error('Erro ao fazer logout:', error);
        showToast('error', 'Erro no logout', error.message);
    }
}

/**
 * Mostra o modal de login
 */
function showLoginModal() {
    document.getElementById('login-modal').classList.remove('hidden');
}

/**
 * Mostra o modal de cadastro
 */
function showRegisterModal() {
    document.getElementById('register-modal').classList.remove('hidden');
}

/**
 * Fecha todos os modais
 */
function closeModals() {
    document.getElementById('login-modal').classList.add('hidden');
    document.getElementById('register-modal').classList.add('hidden');
}
