/**
 * Configuração da API e Detecção de Porta
 * Gerencia a conexão com o backend
 */

/** Hostname para montar URL (IPv6 precisa de colchetes). */
function hostnameParaUrl(hostname) {
    if (!hostname) return 'localhost';
    if (hostname.includes(':') && hostname !== '[::1]' && !hostname.startsWith('[')) {
        return `[${hostname}]`;
    }
    return hostname;
}

/** Ambiente local / rede interna: API fica em outra porta; nunca usar só "/api" no 8001. */
function isHostLocalOuRedeInterna() {
    if (typeof location === 'undefined') return false;
    const h = location.hostname;
    if (h === 'localhost' || h === '127.0.0.1' || h === '::1' || h === '[::1]') return true;
    if (/^192\.168\.\d{1,3}\.\d{1,3}$/.test(h)) return true;
    if (/^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(h)) return true;
    if (/^172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}$/.test(h)) return true;
    return false;
}

function defaultApiUrl() {
    if (typeof location === 'undefined') return '/api';
    if (!isHostLocalOuRedeInterna()) return '/api';
    const h = hostnameParaUrl(location.hostname);
    return `http://${h}:5000/api`;
}

let API_URL = defaultApiUrl();

/**
 * Se API_URL for só http(s)://host:porta sem path /api, ${API_URL}/admin/... vira /admin/... na origem → 404.
 */
function normalizarApiUrlComSufixo() {
    if (typeof API_URL !== 'string') return;
    const t = API_URL.trim();
    if (!t || t === '/api' || t.endsWith('/api')) return;
    if (!t.startsWith('http')) return;
    try {
        const u = new URL(t);
        const path = (u.pathname || '/').replace(/\/$/, '') || '/';
        if (path === '/') {
            API_URL = `${u.origin}/api`;
            console.warn('[api] API_URL sem /api — corrigido para', API_URL);
        }
    } catch (e) {}
}

/**
 * Base da API sempre terminando em /api (chame antes de montar `${base}/admin/...`).
 */
function apiRootUrl() {
    if (typeof garantirApiBackendDev === 'function') {
        garantirApiBackendDev();
    }
    normalizarApiUrlComSufixo();
    let b = (typeof API_URL === 'string' && API_URL.trim()) ? API_URL.trim().replace(/\/$/, '') : '';
    if (!b) {
        return typeof location !== 'undefined' ? `${location.origin}/api` : '/api';
    }
    if (b === '/api' || b.endsWith('/api')) return b;
    return `${b}/api`;
}

/**
 * Garante URL absoluta do Flask em dev (evita POST no server.py da porta 8001 → 501).
 */
function garantirApiBackendDev() {
    if (isHostLocalOuRedeInterna()) {
        const relativoOuMesmaOrigemErrada =
            typeof API_URL === 'string' &&
            (API_URL.startsWith('/') ||
                API_URL.startsWith(`${location.origin}/api`));
        if (relativoOuMesmaOrigemErrada) {
            const h = hostnameParaUrl(location.hostname);
            API_URL = `http://${h}:5000/api`;
            console.warn('[api] Corrigindo API_URL para:', API_URL);
        }
    }
    normalizarApiUrlComSufixo();
}

async function detectarPortaBackend() {
    garantirApiBackendDev();

    const hostUrl = hostnameParaUrl(location.hostname);

    async function sondarPortasLocais() {
        const portas = [5000, 5001];
        for (const porta of portas) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 2500);
                const response = await fetch(`http://${hostUrl}:${porta}/api/produtos`, {
                    method: 'GET',
                    mode: 'cors',
                    cache: 'no-cache',
                    headers: { Accept: 'application/json' },
                    signal: controller.signal
                });
                clearTimeout(timeoutId);
                if (response.status >= 200 && response.status < 600) {
                    API_URL = `http://${hostUrl}:${porta}/api`;
                    console.log(`Backend em http://${hostUrl}:${porta} (HTTP ${response.status})`);
                    return true;
                }
            } catch (e) {
                if (e.name !== 'AbortError') {
                    console.log(`Porta ${porta}:`, e.message);
                }
            }
        }
        return false;
    }

    if (isHostLocalOuRedeInterna()) {
        if (await sondarPortasLocais()) return true;
        API_URL = `http://${hostUrl}:5000/api`;
        console.warn('Backend não respondeu em 5000/5001 — usando fallback:', API_URL);
        garantirApiBackendDev();
        return false;
    }

    API_URL = `${location.origin}/api`;
    normalizarApiUrlComSufixo();
    try {
        const resp = await fetch(`${API_URL}/produtos`, { method: 'GET', cache: 'no-cache' });
        if (resp.ok) {
            console.log('Backend via mesma origem:', location.origin);
            return true;
        }
    } catch (e) {}
    console.warn('Backend não encontrado na origem:', location.origin);
    return false;
}
