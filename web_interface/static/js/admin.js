// Admin Panel JavaScript

// Global variables
let sessions = [];
let refreshInterval;

// Initialize admin panel
document.addEventListener('DOMContentLoaded', function() {
    loadSessions();
    setupEventListeners();
    startAutoRefresh();
});

function setupEventListeners() {
    // Refresh button
    document.getElementById('refresh-btn').addEventListener('click', loadSessions);
    
    // Session modal close
    document.getElementById('sessionModal').addEventListener('hidden.bs.modal', function() {
        // Clear modal content
        clearModalContent();
    });
    
    // Rename modal events
    document.getElementById('save-rename-btn').addEventListener('click', saveRename);
    document.getElementById('rename-form').addEventListener('submit', function(e) {
        e.preventDefault();
        saveRename();
    });
    
    // Delete modal events
    document.getElementById('confirm-delete-btn').addEventListener('click', confirmDelete);
}

function startAutoRefresh() {
    // Auto refresh every 30 seconds
    refreshInterval = setInterval(loadSessions, 30000);
}

function loadSessions() {
    const loadingRow = `
        <tr>
            <td colspan="7" class="text-center text-muted py-4">
                <i class="fas fa-spinner fa-spin"></i> Yükleniyor...
            </td>
        </tr>
    `;
    
    document.getElementById('sessions-table-body').innerHTML = loadingRow;
    
    fetch('/api/sessions')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                sessions = data.sessions;
                renderSessionsTable();
                updateStatistics();
            } else {
                showError('Session verisi yüklenemedi: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading sessions:', error);
            showError('Bağlantı hatası oluştu');
        });
}

function renderSessionsTable() {
    const tbody = document.getElementById('sessions-table-body');
    
    if (sessions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted py-4">
                    <i class="fas fa-inbox"></i> Henüz session bulunamadı
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = sessions.map(session => {
        const createdAt = formatDate(session.created_at);
        const lastActivity = formatDate(session.last_activity);
        const isActive = isSessionActive(session.last_activity);
        const statusBadge = isActive 
            ? '<span class="badge bg-success">Aktif</span>' 
            : '<span class="badge bg-secondary">Pasif</span>';
        
        return `
            <tr>
                <td>
                    <span class="fw-bold">${session.session_name || `Chat ${session.session_id.substring(0, 8)}`}</span>
                </td>
                <td>
                    <span class="font-monospace text-muted">${session.session_id.substring(0, 8)}...</span>
                </td>
                <td>${createdAt}</td>
                <td>${lastActivity}</td>
                <td>
                    <span class="badge bg-info">${session.message_count || 0}</span>
                </td>
                <td>
                    <span class="badge bg-warning">${session.product_count || 0}</span>
                </td>
                <td>
                    <div class="btn-group" role="group">
                        <button class="btn btn-sm btn-outline-primary" 
                                onclick="viewSessionDetails('${session.session_id}')"
                                title="Detayları Görüntüle">
                            <i class="fas fa-eye"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-success" 
                                onclick="switchToSession('${session.session_id}')"
                                title="Bu Session'a Geç">
                            <i class="fas fa-arrow-right"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-warning" 
                                onclick="renameSession('${session.session_id}', '${session.session_name || `Chat ${session.session_id.substring(0, 8)}`}')"
                                title="Adını Değiştir">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger" 
                                onclick="deleteSession('${session.session_id}', '${session.session_name || `Chat ${session.session_id.substring(0, 8)}`}')"
                                title="Sil">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function updateStatistics() {
    const totalSessions = sessions.length;
    const activeSessions = sessions.filter(s => isSessionActive(s.last_activity)).length;
    const totalMessages = sessions.reduce((sum, s) => sum + (s.message_count || 0), 0);
    const totalProducts = sessions.reduce((sum, s) => sum + (s.product_count || 0), 0);
    
    // Update statistic cards with animation
    animateCounter('total-sessions', totalSessions);
    animateCounter('active-sessions', activeSessions);
    animateCounter('total-messages', totalMessages);
    animateCounter('found-products', totalProducts);
}

function animateCounter(elementId, targetValue) {
    const element = document.getElementById(elementId);
    const currentValue = parseInt(element.textContent) || 0;
    const increment = Math.ceil((targetValue - currentValue) / 20);
    
    if (currentValue !== targetValue) {
        const timer = setInterval(() => {
            const newValue = parseInt(element.textContent) + increment;
            if ((increment > 0 && newValue >= targetValue) || 
                (increment < 0 && newValue <= targetValue)) {
                element.textContent = targetValue;
                clearInterval(timer);
            } else {
                element.textContent = newValue;
            }
        }, 50);
    }
}

function viewSessionDetails(sessionId) {
    // Show loading in modal
    const modal = new bootstrap.Modal(document.getElementById('sessionModal'));
    modal.show();
    
    showModalLoading();
    
    fetch(`/api/session/${sessionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateModal(data);
            } else {
                showModalError('Session detayları yüklenemedi: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading session details:', error);
            showModalError('Bağlantı hatası oluştu');
        });
}

function populateModal(sessionData) {
    // Basic info
    document.getElementById('modal-session-id').textContent = sessionData.session_id;
    document.getElementById('modal-created-at').textContent = formatDate(sessionData.created_at);
    document.getElementById('modal-last-activity').textContent = formatDate(sessionData.last_activity);
    document.getElementById('modal-message-count').textContent = sessionData.history.length;
    document.getElementById('modal-product-count').textContent = sessionData.products.length;
    
    // Products
    const productsContainer = document.getElementById('modal-products');
    if (sessionData.products.length > 0) {
        productsContainer.innerHTML = sessionData.products.map(product => `
            <div class="product-item">
                <div>
                    <div class="product-name">${product.name}</div>
                    <div class="product-model">Model: ${product.model || 'Belirtilmemiş'}</div>
                </div>
                ${product.url ? `<a href="${product.url}" target="_blank" class="btn btn-sm btn-outline-primary">
                    <i class="fas fa-external-link-alt"></i>
                </a>` : ''}
            </div>
        `).join('');
    } else {
        productsContainer.innerHTML = '<p class="text-muted">Henüz ürün bulunamadı.</p>';
    }
    
    // Chat history
    const historyContainer = document.getElementById('modal-chat-history');
    if (sessionData.history.length > 0) {
        historyContainer.innerHTML = sessionData.history.map(msg => {
            const timestamp = formatTime(msg.timestamp);
            const senderClass = msg.sender === 'user' ? 'user' : 'assistant';
            const senderIcon = msg.sender === 'user' ? 'fa-user' : 'fa-robot';
            const senderName = msg.sender === 'user' ? 'Kullanıcı' : 'AI Asistan';
            
            return `
                <div class="chat-history-item ${senderClass}">
                    <div class="d-flex align-items-start">
                        <i class="fas ${senderIcon} me-2 mt-1"></i>
                        <div class="flex-grow-1">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <strong class="small">${senderName}</strong>
                                <span class="chat-timestamp">${timestamp}</span>
                            </div>
                            <div class="message-text">${formatMessageForDisplay(msg.content)}</div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    } else {
        historyContainer.innerHTML = '<p class="text-muted">Henüz mesaj bulunamadı.</p>';
    }
    
    // Scroll to bottom of chat history
    historyContainer.scrollTop = historyContainer.scrollHeight;
}

function formatMessageForDisplay(content) {
    // Truncate long messages and preserve basic formatting
    const maxLength = 200;
    let formatted = content.length > maxLength 
        ? content.substring(0, maxLength) + '...' 
        : content;
    
    // Basic HTML escaping and line break conversion
    return formatted
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>');
}

function deleteSession(sessionId, sessionName) {
    // Show delete confirmation modal
    document.getElementById('delete-session-id').value = sessionId;
    document.getElementById('delete-session-name').textContent = sessionName;
    
    const modal = new bootstrap.Modal(document.getElementById('deleteModal'));
    modal.show();
}

function confirmDelete() {
    const sessionId = document.getElementById('delete-session-id').value;
    
    if (!sessionId) return;
    
    // Show loading
    const btn = document.getElementById('confirm-delete-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Siliniyor...';
    btn.disabled = true;
    
    fetch(`/api/session/${sessionId}/delete`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Hide modal
            bootstrap.Modal.getInstance(document.getElementById('deleteModal')).hide();
            
            // Show success notification
            showNotification('Session başarıyla silindi!', 'success');
            
            // Refresh sessions list
            loadSessions();
        } else {
            showNotification('Session silinemedi: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        console.error('Error deleting session:', error);
        showNotification('Bağlantı hatası oluştu', 'danger');
    })
    .finally(() => {
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

function renameSession(sessionId, currentName) {
    // Show rename modal
    document.getElementById('rename-session-id').value = sessionId;
    document.getElementById('new-session-name').value = currentName;
    
    const modal = new bootstrap.Modal(document.getElementById('renameModal'));
    modal.show();
    
    // Focus on input
    setTimeout(() => {
        document.getElementById('new-session-name').focus();
        document.getElementById('new-session-name').select();
    }, 500);
}

function saveRename() {
    const sessionId = document.getElementById('rename-session-id').value;
    const newName = document.getElementById('new-session-name').value.trim();
    
    if (!sessionId || !newName) {
        showNotification('Session adı boş olamaz', 'warning');
        return;
    }
    
    // Show loading
    const btn = document.getElementById('save-rename-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Kaydediliyor...';
    btn.disabled = true;
    
    fetch(`/api/session/${sessionId}/rename`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            new_name: newName
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Hide modal
            bootstrap.Modal.getInstance(document.getElementById('renameModal')).hide();
            
            // Show success notification
            showNotification('Session adı güncellendi!', 'success');
            
            // Refresh sessions list
            loadSessions();
        } else {
            showNotification('Session adı güncellenemedi: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        console.error('Error renaming session:', error);
        showNotification('Bağlantı hatası oluştu', 'danger');
    })
    .finally(() => {
        // Reset button
        btn.innerHTML = originalText;
        btn.disabled = false;
    });
}

function switchToSession(sessionId) {
    // Switch to session
    fetch(`/api/session/${sessionId}/switch`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('Session değiştirildi! Chat\'e yönlendiriliyorsunuz...', 'success');
            
            // Redirect to chat with session parameter
            setTimeout(() => {
                window.location.href = `/?session=${sessionId}`;
            }, 1500);
        } else {
            showNotification('Session değiştirilemedi: ' + data.error, 'danger');
        }
    })
    .catch(error => {
        console.error('Error switching session:', error);
        showNotification('Bağlantı hatası oluştu', 'danger');
    });
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

function showModalLoading() {
    const content = `
        <div class="text-center py-4">
            <i class="fas fa-spinner fa-spin fa-2x mb-3"></i>
            <p>Session detayları yükleniyor...</p>
        </div>
    `;
    document.querySelector('#sessionModal .modal-body').innerHTML = content;
}

function showModalError(message) {
    const content = `
        <div class="text-center py-4">
            <i class="fas fa-exclamation-triangle fa-2x text-danger mb-3"></i>
            <p class="text-danger">${message}</p>
        </div>
    `;
    document.querySelector('#sessionModal .modal-body').innerHTML = content;
}

function clearModalContent() {
    document.getElementById('modal-session-id').textContent = '-';
    document.getElementById('modal-created-at').textContent = '-';
    document.getElementById('modal-last-activity').textContent = '-';
    document.getElementById('modal-message-count').textContent = '0';
    document.getElementById('modal-product-count').textContent = '0';
    document.getElementById('modal-products').innerHTML = '<p class="text-muted">Ürün bulunamadı.</p>';
    document.getElementById('modal-chat-history').innerHTML = '<p class="text-muted">Mesaj bulunamadı.</p>';
}

function showError(message) {
    const tbody = document.getElementById('sessions-table-body');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center text-danger py-4">
                <i class="fas fa-exclamation-triangle"></i> ${message}
            </td>
        </tr>
    `;
}

// Utility functions
function formatDate(dateString) {
    if (!dateString || dateString === 'Bilinmiyor') return 'Bilinmiyor';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('tr-TR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}

function formatTime(dateString) {
    if (!dateString) return '';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleTimeString('tr-TR', {
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}

function isSessionActive(lastActivity) {
    if (!lastActivity || lastActivity === 'Bilinmiyor') return false;
    
    try {
        const lastDate = new Date(lastActivity);
        const now = new Date();
        const diffMinutes = (now - lastDate) / (1000 * 60);
        return diffMinutes < 30; // Active if last activity within 30 minutes
    } catch (e) {
        return false;
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
});
