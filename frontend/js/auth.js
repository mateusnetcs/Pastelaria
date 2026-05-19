/**
 * Funções de Autenticação
 * Gerencia login, cadastro, logout e Google Sign-In
 */

let googleClientId = null;
let googleScriptInicializado = false;
let googleLoginEmAndamento = false;

/**
 * Garante API_URL apontando para o Flask antes de chamar auth
 */
function prepararApiUrlAuth() {
    if (typeof garantirApiBackendDev === 'function') {
        garantirApiBackendDev();
    }
    if (typeof normalizarApiUrlComSufixo === 'function') {
        normalizarApiUrlComSufixo();
    }
}

/**
 * URLs candidatas para buscar /auth/config
 */
function urlsAuthConfig() {
    prepararApiUrlAuth();
    const urls = [];
    const add = (u) => {
        if (!u) return;
        const base = String(u).replace(/\/$/, '');
        if (!urls.includes(base)) urls.push(base);
    };

    add(typeof API_URL === 'string' ? API_URL : '');
    if (typeof isHostLocalOuRedeInterna === 'function' && isHostLocalOuRedeInterna()) {
        const h = typeof hostnameParaUrl === 'function'
            ? hostnameParaUrl(location.hostname)
            : location.hostname;
        add(`http://${h}:5000/api`);
        add(`http://${h}:5001/api`);
    }
    if (typeof location !== 'undefined') {
        add(`${location.origin}/api`);
    }
    return urls;
}

/**
 * Carrega configuração pública de auth (Client ID do Google)
 */
async function carregarConfigAuth() {
    for (const base of urlsAuthConfig()) {
        try {
            const response = await fetch(`${base}/auth/config`, {
                credentials: 'include',
                cache: 'no-store',
            });
            if (!response.ok) {
                console.warn('[auth] /auth/config', base, response.status);
                continue;
            }
            const data = await response.json();
            if (data.success && data.google_enabled && data.google_client_id) {
                googleClientId = data.google_client_id;
                API_URL = base;
                console.log('[auth] Google habilitado via', base);
                return true;
            }
        } catch (error) {
            console.warn('[auth] Falha em', base, error.message);
        }
    }
    return false;
}

function aguardarGoogleScript() {
    return new Promise((resolve) => {
        if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
            resolve(true);
            return;
        }
        let tentativas = 0;
        const timer = setInterval(() => {
            tentativas += 1;
            if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
                clearInterval(timer);
                resolve(true);
            } else if (tentativas > 60) {
                clearInterval(timer);
                resolve(false);
            }
        }, 200);
    });
}

function inicializarGoogleSignIn() {
    if (!googleClientId) return;
    google.accounts.id.initialize({
        client_id: googleClientId,
        callback: handleGoogleCredential,
        auto_select: false,
        cancel_on_tap_outside: true,
        use_fedcm_for_prompt: false,
    });
    googleScriptInicializado = true;
}

function renderizarBotoesGoogle() {
    if (!googleClientId) return;

    const opts = {
        theme: 'outline',
        size: 'large',
        type: 'standard',
        text: 'continue_with',
        shape: 'rectangular',
        logo_alignment: 'left',
        width: 300,
        locale: 'pt-BR',
    };

    const loginBtn = document.getElementById('google-login-btn');
    const registerBtn = document.getElementById('google-register-btn');

    if (loginBtn) {
        loginBtn.innerHTML = '';
        google.accounts.id.renderButton(loginBtn, opts);
    }
    if (registerBtn) {
        registerBtn.innerHTML = '';
        google.accounts.id.renderButton(registerBtn, opts);
    }

    const fallbackLogin = document.getElementById('google-login-fallback');
    const fallbackRegister = document.getElementById('google-register-fallback');
    if (fallbackLogin) fallbackLogin.classList.add('hidden');
    if (fallbackRegister) fallbackRegister.classList.add('hidden');
}

function mostrarFallbackGoogle() {
    ['google-login-fallback', 'google-register-fallback'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.classList.remove('hidden');
    });
}

/**
 * Prepara Google ao abrir modal (config + botão visível)
 */
async function prepararGoogleAuthNoModal() {
    if (!googleClientId) {
        await carregarConfigAuth();
    }

    const loginWrap = document.getElementById('google-login-wrap');
    const registerWrap = document.getElementById('google-register-wrap');

    if (!googleClientId) {
        if (loginWrap) loginWrap.classList.add('hidden');
        if (registerWrap) registerWrap.classList.add('hidden');
        return;
    }

    if (loginWrap) loginWrap.classList.remove('hidden');
    if (registerWrap) registerWrap.classList.remove('hidden');

    const fallbackLogin = document.getElementById('google-login-fallback');
    const fallbackRegister = document.getElementById('google-register-fallback');
    if (fallbackLogin) fallbackLogin.classList.remove('hidden');
    if (fallbackRegister) fallbackRegister.classList.remove('hidden');

    const scriptOk = await aguardarGoogleScript();
    if (!scriptOk) {
        console.warn('[auth] Script accounts.google.com não carregou');
        mostrarFallbackGoogle();
        return;
    }

    inicializarGoogleSignIn();

    await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));

    try {
        renderizarBotoesGoogle();
        const loginBtn = document.getElementById('google-login-btn');
        if (loginBtn && loginBtn.querySelector('iframe')) {
            if (fallbackLogin) fallbackLogin.classList.add('hidden');
            if (fallbackRegister) fallbackRegister.classList.add('hidden');
        }
    } catch (e) {
        console.warn('[auth] Erro ao renderizar botão Google:', e);
    }
}

/**
 * Fallback: botão manual — tenta renderizar de novo ou abre prompt Google
 */
async function clicarLoginGoogle() {
    await prepararGoogleAuthNoModal();
    showToast('info', 'Google', 'Use o botão oficial "Continuar com Google" logo abaixo');
}

/**
 * Callback do Google — envia JWT ao backend
 */
async function handleGoogleCredential(response) {
    if (!response || !response.credential) {
        showToast('error', 'Google', 'Não foi possível obter credenciais');
        return;
    }

    if (googleLoginEmAndamento) return;
    googleLoginEmAndamento = true;

    prepararApiUrlAuth();
    if (!googleClientId) {
        await carregarConfigAuth();
    }

    try {
        const res = await fetch(`${API_URL}/auth/google`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ credential: response.credential }),
        });
        const data = await res.json();

        if (data.success) {
            usuario = data.user;
            localStorage.setItem('usuario', JSON.stringify(usuario));
            updateUI();
            closeModals();
            showToast('success', 'Login realizado!', `Bem-vindo, ${data.user.nome}!`);
        } else {
            showToast('error', 'Erro no login Google', data.error || 'Tente novamente');
        }
    } catch (error) {
        showToast('error', 'Erro no login Google', error.message);
    } finally {
        googleLoginEmAndamento = false;
    }
}

/**
 * Processa o login do usuário
 */
async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('login-email').value.trim();
    const senha = document.getElementById('login-senha').value;

    if (!email || !senha) {
        showToast('error', 'Campos obrigatórios', 'Informe email e senha ou use o Google');
        return;
    }

    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email, senha }),
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
            body: JSON.stringify({ nome, email, telefone, senha }),
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
async function showLoginModal() {
    document.getElementById('login-modal').classList.remove('hidden');
    await prepararGoogleAuthNoModal();
}

/**
 * Mostra o modal de cadastro
 */
async function showRegisterModal() {
    document.getElementById('register-modal').classList.remove('hidden');
    await prepararGoogleAuthNoModal();
}

/**
 * Fecha todos os modais
 */
function closeModals() {
    document.getElementById('login-modal').classList.add('hidden');
    document.getElementById('register-modal').classList.add('hidden');
}
