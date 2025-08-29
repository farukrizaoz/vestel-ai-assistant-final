// WebSocket bağlantısı
const socket = io();

// Global variables
let currentSessionId = null;
let messageCount = 0;
let sessions = [];

// DOM elements
const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendBtn = document.getElementById('send-btn');
const newChatBtn = document.getElementById('new-chat-btn');
const typingIndicator = document.getElementById('typing-indicator');
const connectionStatus = document.getElementById('connection-status');
const sessionIdDisplay = document.getElementById('session-id');
const messageCountDisplay = document.getElementById('message-count');
const lastActivityDisplay = document.getElementById('last-activity');
const sessionDropdown = document.getElementById('sessionDropdown');
const sessionList = document.getElementById('session-list');
const currentSessionName = document.getElementById('current-session-name');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Check for session parameter in URL
    const urlParams = new URLSearchParams(window.location.search);
    const sessionParam = urlParams.get('session');
    
    if (sessionParam) {
        currentSessionId = sessionParam;
        loadSessionHistory(sessionParam);
    } else {
        initializeChat();
    }
    
    setupEventListeners();
    loadSessionList();
});

function initializeChat() {
    chatMessages.innerHTML = `
        <div class="text-center text-muted p-4" id="welcome-message">
            <i class="fas fa-robot fa-3x mb-3 text-primary"></i>
            <h5>Vestel AI Assistant'a Hoş Geldiniz!</h5>
            <p>Ürünler hakkında soru sorabilir, teknik destek alabilir veya kurulum yardımı isteyebilirsiniz.</p>
            <div class="mt-3">
                <small class="text-muted">
                    <i class="fas fa-lightbulb me-1"></i>
                    Örnekler: "650 litre buzdolabı", "Wi-Fi bağlantısı nasıl kurulur?", "No-Frost nedir?"
                </small>
            </div>
        </div>
    `;
}

function setupEventListeners() {
    // Send message on button click
    sendBtn.addEventListener('click', sendMessage);
    
    // Send message on Enter key
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    
    // New chat button
    newChatBtn.addEventListener('click', startNewChat);
    
    // Session dropdown events
    sessionDropdown.addEventListener('click', loadSessionList);
    
    // Session management buttons
    const newSessionBtn = document.getElementById('new-session-btn');
    const clearChatBtn = document.getElementById('clear-chat-btn');
    const deleteSessionBtn = document.getElementById('delete-session-btn');
    
    if (newSessionBtn) {
        newSessionBtn.addEventListener('click', startNewChat);
    }
    
    if (clearChatBtn) {
        clearChatBtn.addEventListener('click', clearCurrentChat);
    }
    
    if (deleteSessionBtn) {
        deleteSessionBtn.addEventListener('click', deleteCurrentSession);
    }
    
    // Quick action buttons
    document.querySelectorAll('.quick-action').forEach(btn => {
        btn.addEventListener('click', function() {
            const message = this.getAttribute('data-message');
            messageInput.value = message;
            sendMessage();
        });
    });
}

function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Clear welcome message if exists
    const welcomeMessage = document.getElementById('welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    // Add user message to chat
    addMessage('user', message);
    
    // Clear input
    messageInput.value = '';
    
    // Send to server
    socket.emit('send_message', {
        message: message,
        session_id: currentSessionId
    });
    
    updateLastActivity();
}

function addMessage(sender, content, timestamp = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message message-${sender}`;
    
    const now = timestamp || new Date();
    const timeStr = now.toLocaleTimeString('tr-TR', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
    
    const avatarClass = sender === 'user' ? 'avatar-user' : 'avatar-assistant';
    const avatarIcon = sender === 'user' ? 'fa-user' : 'fa-robot';
    
    // Format content for assistant messages
    let formattedContent = content;
    if (sender === 'assistant') {
        formattedContent = formatAssistantMessage(content);
    }
    
    messageDiv.innerHTML = `
        <div class="d-flex ${sender === 'user' ? 'flex-row-reverse' : 'flex-row'} align-items-end">
            <div class="avatar ${avatarClass}">
                <i class="fas ${avatarIcon}"></i>
            </div>
            <div class="message-content">
                ${formattedContent}
                <div class="message-meta">${timeStr}</div>
            </div>
        </div>
    `;
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
    
    // Update message count
    messageCount++;
    updateMessageCount();
}

function formatAssistantMessage(content) {
    // Basic formatting for assistant messages
    let formatted = content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Bold
        .replace(/\*(.*?)\*/g, '<em>$1</em>') // Italic
        .replace(/`(.*?)`/g, '<code>$1</code>') // Code
        .replace(/\n/g, '<br>'); // Line breaks
    
    return formatted;
}

function startNewChat() {
    fetch('/api/chat/new', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentSessionId = data.session_id;
                initializeChat();
                currentSessionName.textContent = `Yeni Chat ${data.session_id.substring(0, 8)}`;
                
                // Update URL
                const newUrl = new URL(window.location);
                newUrl.searchParams.set('session', data.session_id);
                window.history.pushState({}, '', newUrl);
                
                loadSessionList();
            }
        })
        .catch(error => console.error('Yeni chat oluşturulamadı:', error));
}

function updateSessionInfo() {
    if (currentSessionId && sessionIdDisplay) {
        sessionIdDisplay.textContent = currentSessionId.substring(0, 8) + '...';
    }
}

function updateMessageCount() {
    if (messageCountDisplay) {
        messageCountDisplay.textContent = messageCount;
    }
}

function updateLastActivity() {
    if (lastActivityDisplay) {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('tr-TR');
        lastActivityDisplay.textContent = timeStr;
    }
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping(show) {
    if (typingIndicator) {
        typingIndicator.style.display = show ? 'block' : 'none';
        if (show) {
            scrollToBottom();
        }
    }
}

// Session Management Functions
function loadSessionList() {
    fetch('/api/sessions')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                sessions = data.sessions;
                renderSessionDropdown();
            }
        })
        .catch(error => console.error('Session listesi yüklenemedi:', error));
}

function clearCurrentChat() {
    if (!currentSessionId) {
        alert('Silinecek session yok.');
        return;
    }
    
    if (confirm('Bu session\'daki tüm mesajları silmek istediğinizden emin misiniz?')) {
        // Clear the UI immediately
        chatMessages.innerHTML = '';
        messageCount = 0;
        updateMessageCount();
        initializeChat();
        
        // Clear on server
        fetch(`/api/session/${currentSessionId}/clear`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    console.log('Session temizlendi');
                } else {
                    console.error('Session temizlenemedi:', data.error);
                }
            })
            .catch(error => console.error('Session temizleme hatası:', error));
    }
}

function deleteCurrentSession() {
    if (!currentSessionId) {
        alert('Silinecek session yok.');
        return;
    }
    
    const sessionName = currentSessionName.textContent || currentSessionId.substring(0, 8);
    
    if (confirm(`"${sessionName}" session'ını tamamen silmek istediğinizden emin misiniz?\n\nBu işlem geri alınamaz!`)) {
        fetch(`/api/session/${currentSessionId}/delete`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Session silindi, yeni session başlat
                    startNewChat();
                    loadSessionList();
                    alert('Session başarıyla silindi.');
                } else {
                    alert('Session silinemedi: ' + (data.error || 'Bilinmeyen hata'));
                }
            })
            .catch(error => {
                console.error('Session silme hatası:', error);
                alert('Session silinirken bir hata oluştu.');
            });
    }
}

function renderSessionDropdown() {
    if (!sessionList) return;
    
    sessionList.innerHTML = '';
    
    if (sessions.length === 0) {
        sessionList.innerHTML = '<li><span class="dropdown-item-text text-muted">Session bulunamadı</span></li>';
        return;
    }
    
    sessions.forEach(session => {
        const sessionName = session.session_name || `Chat ${session.session_id.substring(0, 8)}`;
        const isActive = session.session_id === currentSessionId;
        
        const li = document.createElement('li');
        li.innerHTML = `
            <a class="dropdown-item ${isActive ? 'active' : ''}" href="#" 
               onclick="switchToSession('${session.session_id}', '${sessionName}')">
                <strong>${sessionName}</strong><br>
                <small class="text-muted">${session.message_count || 0} mesaj</small>
            </a>
        `;
        sessionList.appendChild(li);
    });
    
    // Add divider and new session option
    const dividerLi = document.createElement('li');
    dividerLi.innerHTML = '<hr class="dropdown-divider">';
    sessionList.appendChild(dividerLi);
    
    const newSessionLi = document.createElement('li');
    newSessionLi.innerHTML = `
        <a class="dropdown-item" href="#" onclick="startNewChat()">
            <i class="fas fa-plus text-primary me-2"></i> Yeni Session
        </a>
    `;
    sessionList.appendChild(newSessionLi);
}

function switchToSession(sessionId, sessionName) {
    if (sessionId === currentSessionId) return;
    
    currentSessionId = sessionId;
    if (currentSessionName) {
        currentSessionName.textContent = sessionName;
    }
    
    loadSessionHistory(sessionId);
    
    // Update URL
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('session', sessionId);
    window.history.pushState({}, '', newUrl);
}

function loadSessionHistory(sessionId) {
    // Duplicate mesajları önlemek için önce temizle
    chatMessages.innerHTML = '';
    messageCount = 0;
    
    fetch(`/api/session/${sessionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Tekrar temizle (timing sorunları için)
                chatMessages.innerHTML = '';
                messageCount = 0;
                
                if (data.history && data.history.length > 0) {
                    data.history.forEach(msg => {
                        addMessage(msg.sender, msg.content, new Date(msg.timestamp));
                    });
                } else {
                    initializeChat();
                }
                
                // Update session info
                const sessionName = data.session_name || `Chat ${sessionId.substring(0, 8)}`;
                if (currentSessionName) {
                    currentSessionName.textContent = sessionName;
                }
                
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        })
        .catch(error => {
            console.error('Session geçmişi yüklenemedi:', error);
            chatMessages.innerHTML = '';
            messageCount = 0;
            initializeChat();
        });
}

// Socket event handlers
socket.on('connect', function() {
    if (connectionStatus) {
        connectionStatus.innerHTML = '<i class="fas fa-circle"></i> Bağlı';
        connectionStatus.className = 'badge bg-success me-2';
    }
    console.log('Connected to server');
});

socket.on('disconnect', function() {
    if (connectionStatus) {
        connectionStatus.innerHTML = '<i class="fas fa-circle"></i> Bağlantı Kesildi';
        connectionStatus.className = 'badge bg-danger me-2';
    }
    console.log('Disconnected from server');
});

socket.on('status', function(data) {
    console.log('Status:', data.message);
});

socket.on('new_session', function(data) {
    currentSessionId = data.session_id;
    updateSessionInfo();
    console.log('New session created:', currentSessionId);
});

socket.on('typing', function(data) {
    showTyping(data.status);
});

socket.on('message_response', function(data) {
    showTyping(false);
    addMessage('assistant', data.message, new Date());
    updateLastActivity();
    
    // Update session ID if provided
    if (data.session_id && !currentSessionId) {
        currentSessionId = data.session_id;
        updateSessionInfo();
    }
});

socket.on('error', function(data) {
    showTyping(false);
    addMessage('assistant', `❌ Hata: ${data.message}`);
    console.error('Socket error:', data.message);
});

// Auto-focus message input
if (messageInput) {
    messageInput.focus();
}
