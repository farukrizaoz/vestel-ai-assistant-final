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
    // Clear welcome message when first message is sent
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
    
    // New chat button
    newChatBtn.addEventListener('click', startNewChat);
    
    // Session dropdown events
    sessionDropdown.addEventListener('click', loadSessionList);
    
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
    
    // Format content for assistant messages (support markdown-like formatting)
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
    
    // Check for product information pattern
    if (formatted.includes('Model:') && formatted.includes('URL:')) {
        formatted = formatProductCard(formatted);
    }
    
    // Check for step-by-step instructions
    if (formatted.includes('✅') || formatted.includes('📞')) {
        formatted = formatInstructionList(formatted);
    }
    
    return formatted;
}

function formatProductCard(content) {
    // Extract product information and format as card
    const lines = content.split('<br>');
    let productHTML = '<div class="product-card mt-2">';
    
    lines.forEach(line => {
        if (line.includes('Ürün:')) {
            const productName = line.replace('- Ürün:', '').trim();
            productHTML += `<h6 class="product-title mb-2">${productName}</h6>`;
        } else if (line.includes('Model:')) {
            const model = line.replace('Model:', '').trim();
            productHTML += `<p class="mb-1"><strong>Model:</strong> <code>${model}</code></p>`;
        } else if (line.includes('URL:')) {
            const url = line.replace('URL:', '').trim();
            productHTML += `<p class="mb-1"><a href="${url}" target="_blank" class="btn btn-sm btn-outline-primary"><i class="fas fa-external-link-alt me-1"></i>Ürün Sayfası</a></p>`;
        } else if (line.includes('Özellikler:')) {
            const features = line.replace('Özellikler:', '').trim();
            productHTML += `<p class="mb-0"><small class="text-muted">${features}</small></p>`;
        }
    });
    
    productHTML += '</div>';
    return productHTML;
}

function formatInstructionList(content) {
    // Format step-by-step instructions with better styling
    return content
        .replace(/✅ (\d+\. .+?)(<br>|$)/g, '<div class="instruction-step mb-2"><span class="badge bg-success me-2">✅</span><strong>$1</strong></div>')
        .replace(/⚠️ (.+?):/g, '<div class="alert alert-warning py-2 mt-3 mb-2"><i class="fas fa-exclamation-triangle me-2"></i><strong>$1:</strong></div>')
        .replace(/📞 (.+?):/g, '<div class="contact-info mt-3 p-2 bg-light border-start border-primary border-3"><i class="fas fa-phone me-2 text-primary"></i><strong>$1:</strong></div>');
}

function startNewChat() {
    // Reset current session
    currentSessionId = null;
    messageCount = 0;
    
    // Clear chat
    initializeChat();
    
    // Update UI
    updateSessionInfo();
    updateMessageCount();
    
    // Request new session from server
    fetch('/api/chat/new', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentSessionId = data.session_id;
                updateSessionInfo();
            }
        })
        .catch(error => console.error('Error creating new session:', error));
}

function updateSessionInfo() {
    if (currentSessionId) {
        sessionIdDisplay.textContent = currentSessionId.substring(0, 8) + '...';
        document.getElementById('session-status').textContent = 'Aktif';
        document.getElementById('session-status').className = 'badge bg-success';
    } else {
        sessionIdDisplay.textContent = '-';
        document.getElementById('session-status').textContent = 'Bekliyor';
        document.getElementById('session-status').className = 'badge bg-secondary';
    }
}

function updateMessageCount() {
    messageCountDisplay.textContent = messageCount;
}

function updateLastActivity() {
    const now = new Date();
    const timeStr = now.toLocaleTimeString('tr-TR');
    lastActivityDisplay.textContent = timeStr;
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTyping(show) {
    typingIndicator.style.display = show ? 'block' : 'none';
    if (show) {
        scrollToBottom();
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
            } else {
                console.error('Session listesi yüklenemedi:', data.error);
            }
        })
        .catch(error => {
            console.error('Session listesi yüklenirken hata:', error);
        });
}

function renderSessionDropdown() {
    sessionList.innerHTML = '';
    
    if (sessions.length === 0) {
        sessionList.innerHTML = '<li><span class="dropdown-item-text text-muted">Henüz session bulunamadı</span></li>';
        return;
    }
    
    sessions.forEach(session => {
        const sessionName = session.session_name || `Chat ${session.session_id.substring(0, 8)}`;
        const isActive = session.session_id === currentSessionId;
        
        const li = document.createElement('li');
        li.innerHTML = `
            <a class="dropdown-item ${isActive ? 'active' : ''}" href="#" 
               onclick="switchToSession('${session.session_id}', '${sessionName}')">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${sessionName}</strong>
                        <br><small class="text-muted">${session.message_count || 0} mesaj</small>
                    </div>
                    <div class="text-end">
                        <small class="text-muted">${formatSessionDate(session.last_activity)}</small>
                    </div>
                </div>
            </a>
        `;
        sessionList.appendChild(li);
    });
    
    // Add divider and new session option
    sessionList.innerHTML += `
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item" href="#" onclick="startNewChat()">
            <i class="fas fa-plus text-primary me-2"></i>
            Yeni Session Başlat
        </a></li>
    `;
}

function switchToSession(sessionId, sessionName) {
    if (sessionId === currentSessionId) return;
    
    currentSessionId = sessionId;
    currentSessionName.textContent = sessionName;
    
    // Load session history
    loadSessionHistory(sessionId);
    
    // Update URL
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('session', sessionId);
    window.history.pushState({}, '', newUrl);
}

function loadSessionHistory(sessionId) {
    fetch(`/api/session/${sessionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear current chat
                chatMessages.innerHTML = '';
                
                // Load history
                if (data.history && data.history.length > 0) {
                    data.history.forEach(msg => {
                        if (msg.sender === 'user') {
                            addUserMessage(msg.content);
                        } else {
                            addBotMessage(msg.content);
                        }
                    });
                } else {
                    initializeChat();
                }
                
                // Update session info
                const sessionName = data.session_name || `Chat ${sessionId.substring(0, 8)}`;
                currentSessionName.textContent = sessionName;
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else {
                console.error('Session geçmişi yüklenemedi:', data.error);
                initializeChat();
            }
        })
        .catch(error => {
            console.error('Session geçmişi yüklenirken hata:', error);
            initializeChat();
        });
}

function startNewChat() {
    fetch('/api/chat/new', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            currentSessionId = data.session_id;
            
            // Initialize new chat
            initializeChat();
            
            // Update session name
            currentSessionName.textContent = `Yeni Chat ${data.session_id.substring(0, 8)}`;
            
            // Update URL
            const newUrl = new URL(window.location);
            newUrl.searchParams.set('session', data.session_id);
            window.history.pushState({}, '', newUrl);
            
            // Refresh session list
            loadSessionList();
        } else {
            console.error('Yeni chat oluşturulamadı:', data.error);
        }
    })
    .catch(error => {
        console.error('Yeni chat oluşturulurken hata:', error);
    });
}

function formatSessionDate(dateString) {
    if (!dateString || dateString === 'Bilinmiyor') return 'Bilinmiyor';
    
    try {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return 'Şimdi';
        if (diffMins < 60) return `${diffMins}d önce`;
        if (diffHours < 24) return `${diffHours}s önce`;
        if (diffDays < 7) return `${diffDays} gün önce`;
        
        return date.toLocaleDateString('tr-TR', {
            day: '2-digit',
            month: '2-digit'
        });
    } catch (e) {
        return dateString;
    }
}

// Socket event handlers
socket.on('connect', function() {
    connectionStatus.innerHTML = '<i class="fas fa-circle"></i> Bağlı';
    connectionStatus.className = 'badge bg-success me-2';
    console.log('Connected to server');
});

socket.on('disconnect', function() {
    connectionStatus.innerHTML = '<i class="fas fa-circle"></i> Bağlantı Kesildi';
    connectionStatus.className = 'badge bg-danger me-2';
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
messageInput.focus();

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

function renderSessionDropdown() {
    sessionList.innerHTML = '';
    
    if (sessions.length === 0) {
        sessionList.innerHTML = '<li><span class="dropdown-item-text text-muted">Session bulunamadı</span></li>';
        return;
    }
    
    sessions.forEach(session => {
        const sessionName = session.session_name || `Chat ${session.session_id.substring(0, 8)}`;
        const isActive = session.session_id === currentSessionId;
        
        sessionList.innerHTML += `
            <li><a class="dropdown-item ${isActive ? 'active' : ''}" href="#" 
                onclick="switchToSession('${session.session_id}', '${sessionName}')">
                <strong>${sessionName}</strong><br>
                <small class="text-muted">${session.message_count || 0} mesaj</small>
            </a></li>
        `;
    });
    
    sessionList.innerHTML += `
        <li><hr class="dropdown-divider"></li>
        <li><a class="dropdown-item" href="#" onclick="startNewChat()">
            <i class="fas fa-plus text-primary me-2"></i> Yeni Session
        </a></li>
    `;
}

function switchToSession(sessionId, sessionName) {
    if (sessionId === currentSessionId) return;
    
    currentSessionId = sessionId;
    currentSessionName.textContent = sessionName;
    loadSessionHistory(sessionId);
}

function loadSessionHistory(sessionId) {
    fetch(`/api/session/${sessionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                chatMessages.innerHTML = '';
                if (data.history && data.history.length > 0) {
                    data.history.forEach(msg => {
                        if (msg.sender === 'user') {
                            addUserMessage(msg.content);
                        } else {
                            addBotMessage(msg.content);
                        }
                    });
                } else {
                    initializeChat();
                }
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        })
        .catch(error => console.error('Session geçmişi yüklenemedi:', error));
}

function startNewChat() {
    fetch('/api/chat/new', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentSessionId = data.session_id;
                initializeChat();
                currentSessionName.textContent = `Yeni Chat ${data.session_id.substring(0, 8)}`;
                loadSessionList();
            }
        })
        .catch(error => console.error('Yeni chat oluşturulamadı:', error));
}
