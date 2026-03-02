/**
 * Configuração da API e Detecção de Porta
 * Gerencia a conexão com o backend
 */

let API_URL = '/api';

async function detectarPortaBackend() {
    const isLocal = location.hostname === 'localhost' || location.hostname === '127.0.0.1';

    if (!isLocal) {
        API_URL = `${location.origin}/api`;
        try {
            const resp = await fetch(`${API_URL}/produtos`, { method: 'GET', cache: 'no-cache' });
            if (resp.ok) {
                console.log('Backend detectado via origem:', location.origin);
                return true;
            }
        } catch (e) {}
        console.warn('Backend não respondeu na origem atual');
        return false;
    }

    const portas = [5000, 5001];
    for (const porta of portas) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000);
            const response = await fetch(`http://localhost:${porta}/api/produtos`, {
                method: 'GET', mode: 'cors', cache: 'no-cache',
                headers: { 'Accept': 'application/json' },
                signal: controller.signal
            });
            clearTimeout(timeoutId);
            if (response.ok) {
                API_URL = `http://localhost:${porta}/api`;
                console.log(`Backend detectado na porta ${porta}`);
                return true;
            }
        } catch (e) {
            if (e.name !== 'AbortError') {
                console.log(`Porta ${porta} não disponível:`, e.message);
            }
        }
    }

    console.warn('Backend não encontrado nas portas 5000 ou 5001');
    return false;
}
