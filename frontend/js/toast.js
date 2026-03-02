/**
 * Sistema de Toast Notifications
 * Exibe notificações elegantes para o usuário
 */

/**
 * Mostra uma notificação toast
 * @param {string} type - Tipo: 'success', 'info', 'error'
 * @param {string} title - Título da notificação
 * @param {string} message - Mensagem da notificação
 */
function showToast(type, title, message) {
    const container = document.getElementById('toast-container');
    if (!container) {
        console.error('Container de toast não encontrado');
        return;
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icons = {
        success: 'fa-check-circle',
        info: 'fa-info-circle',
        error: 'fa-exclamation-circle'
    };
    
    toast.innerHTML = `
        <i class="fas ${icons[type]} toast-icon"></i>
        <div class="flex-1">
            <div class="font-bold text-gray-800">${title}</div>
            <div class="text-sm text-gray-600">${message}</div>
        </div>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}
