// WebSocket bağlantısı - Enhanced reliability with longer timeout
const socket = io({
    reconnection: true,
    reconnectionDelay: 2000,      // 2 saniye bekle
    reconnectionDelayMax: 10000,  // Maksimum 10 saniye bekle  
    reconnectionAttempts: 10,     // 10 kez dene
    timeout: 120000,              // 2 dakika timeout
    transports: ['websocket', 'polling'],
    forceNew: true                // Her zaman yeni bağlantı
});

// Global variables
let currentSessionId = null;
let messageCount = 0;
let sessions = [];
let isConnected = false;
let pendingMessages = [];
let messageTimeouts = new Map(); // Message timeout tracking
let isProcessing = false; // MESAJ İŞLEME DURUMU

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
const sessionSidebar = document.getElementById('session-sidebar');
const currentSessionDisplay = document.getElementById('current-session-display');
const sessionDropdown = document.getElementById('session-dropdown');
const sessionList = document.getElementById('session-list');
const currentSessionName = currentSessionDisplay;
const sidebarContainer = document.getElementById('session-sidebar-container');
const toggleSidebarBtn = document.getElementById('toggle-sidebar');

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Sunucudan gelen session ID'yi al (template'ten)
    if (typeof window.sessionId !== 'undefined' && window.sessionId) {
        currentSessionId = window.sessionId;
        updateSessionDisplay();
        
        // Existing session ise hemen yükle, yeni ise welcome göster
        if (typeof window.existingSession !== 'undefined' && window.existingSession === true) {
            loadSessionHistory(currentSessionId);
        } else {
            initializeChat();
        }
    } else {
        initializeChat();
    }
    
    setupEventListeners();
    // Session list'i paralel olarak yükle - blocking etmesin
    setTimeout(loadSessionList, 100);
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
    
    // Session dropdown events (optional)
    if (sessionDropdown) {
        sessionDropdown.addEventListener('click', loadSessionList);
    }
    
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

    if (toggleSidebarBtn && sidebarContainer) {
        toggleSidebarBtn.addEventListener('click', () => {
            sidebarContainer.classList.toggle('d-none');
        });
    }
}

function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    // MESAJ İŞLENİYORSA YENİ MESAJ GÖNDERİLMESİNİ ENGELLE
    if (isProcessing) {
        console.log('🚫 Mesaj işleniyor, yeni mesaj gönderilemez');
        return;
    }
    
    // Check connection
    if (!isConnected) {
        addMessage('assistant', '❌ Bağlantı yok. Lütfen bekleyin...');
        return;
    }
    
    // MESAJ İŞLEME BAŞLADI
    isProcessing = true;
    disableInput();
    
    // Clear welcome message if exists
    const welcomeMessage = document.getElementById('welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    // Generate unique message ID
    const messageId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    // Add user message to chat
    addMessage('user', message);
    
    // Show thinking bubble - Ajan düşünmeye başladı
    const thinkingId = showThinkingBubble();
    
    // Clear input
    messageInput.value = '';
    
    const messageData = {
        message: message,
        session_id: currentSessionId,
        message_id: messageId,
        thinking_id: thinkingId  // Thinking bubble ID'sini gönder
    };
    
    // Send to server
    if (isConnected) {
        socket.emit('send_message', messageData);
        
        // Timeout'u kaldırıyoruz - Thinking bubble agent cevabı gelene kadar dönecek
        // Agent ne kadar uzun süre düşünürse düşünsün, kullanıcı bunu görecek
        console.log('📤 Message sent, thinking bubble active until response');
    } else {
        // Add to pending messages
        pendingMessages.push(messageData);
        addMessage('assistant', '📡 Bağlantı bekleniyor, mesajınız kuyruğa alındı...');
        // Bağlantı yoksa da input'u tekrar aktif et
        isProcessing = false;
        enableInput();
    }
    
    updateLastActivity();
}

// Input kontrolü fonksiyonları
function disableInput() {
    messageInput.disabled = true;
    sendBtn.disabled = true;
    messageInput.placeholder = "Cevap bekleniyor...";
    sendBtn.innerHTML = '<i class="fas fa-hourglass-half"></i>';
    sendBtn.classList.add('btn-secondary');
    sendBtn.classList.remove('btn-primary');
    disableSessionSwitching();
}

function enableInput() {
    messageInput.disabled = false;
    sendBtn.disabled = false;
    messageInput.placeholder = "Mesajınızı yazın...";
    sendBtn.innerHTML = '<i class="fas fa-paper-plane"></i>';
    sendBtn.classList.remove('btn-secondary');
    sendBtn.classList.add('btn-primary');
    messageInput.focus();
    enableSessionSwitching();
}

function disableSessionSwitching() {
    if (sessionSidebar) {
        sessionSidebar.style.pointerEvents = 'none';
        sessionSidebar.style.opacity = '0.6';
    }
    if (newChatBtn) {
        newChatBtn.disabled = true;
    }
    const newSessionButton = document.getElementById('new-session-btn') ||
        document.querySelector('button[onclick="newSession()"]');
    if (newSessionButton) {
        newSessionButton.disabled = true;
    }
}

function enableSessionSwitching() {
    if (sessionSidebar) {
        sessionSidebar.style.pointerEvents = 'auto';
        sessionSidebar.style.opacity = '1';
    }
    if (newChatBtn) {
        newChatBtn.disabled = false;
    }
    const newSessionButton = document.getElementById('new-session-btn') ||
        document.querySelector('button[onclick="newSession()"]');
    if (newSessionButton) {
        newSessionButton.disabled = false;
    }
}

// Process pending messages when connection is restored
function processPendingMessages() {
    if (pendingMessages.length > 0 && isConnected) {
        console.log('📤 Processing', pendingMessages.length, 'pending messages');
        pendingMessages.forEach(messageData => {
            socket.emit('send_message', messageData);
        });
        pendingMessages = [];
        addMessage('assistant', '✅ Bekleyen mesajlar gönderildi.');
    }
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
    if (isProcessing) {
        alert('Lütfen yanıt gelene kadar bekleyin.');
        return;
    }
    fetch('/api/chat/new', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentSessionId = data.session_id;
                initializeChat();
                updateSessionDisplay();

                // Update URL
                const newUrl = new URL(window.location);
                newUrl.searchParams.set('session', data.session_id);
                window.history.pushState({}, '', newUrl);

                loadSessionList();
            }
        })
        .catch(error => console.error('Yeni chat oluşturulamadı:', error));
}

function newSession() {
    if (isProcessing) {
        alert('Lütfen yanıt gelene kadar bekleyin.');
        return;
    }
    fetch('/api/chat/new', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentSessionId = data.session_id;
                chatMessages.innerHTML = '';
                messageCount = 0;
                initializeChat();
                loadSessionList();
                updateSessionDisplay();
            } else {
                alert('Yeni session oluşturulamadı: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Yeni session oluşturma hatası:', error);
            alert('Yeni session oluşturulamadı');
        });
}

function updateSessionDisplay() {
    if (currentSessionDisplay && currentSessionId) {
        const session = sessions.find(s => s.session_id === currentSessionId);
        if (session && session.session_name) {
            currentSessionDisplay.textContent = session.session_name;
        } else {
            const shortId = currentSessionId.substring(0, 8);
            currentSessionDisplay.textContent = `Session ${shortId}`;
        }
    }
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

// Thinking bubble göster - Ajan düşünürken
function showThinkingBubble(agentName = 'Asistan') {
    const thinkingId = 'thinking-' + Date.now();
    const thinkingMessages = [
        'Düşünüyorum',
        'Analiz ediyorum', 
        'Araştırıyorum',
        'Çözüm buluyorum',
        'Bilgileri kontrol ediyorum'
    ];
    
    const randomMessage = thinkingMessages[Math.floor(Math.random() * thinkingMessages.length)];
    
    const thinkingHtml = `
        <div class="chat-message message-assistant" id="${thinkingId}">
            <div class="avatar avatar-assistant">
                <i class="fas fa-robot"></i>
            </div>
            <div class="thinking-bubble">
                <div class="thinking-content">
                    <i class="fas fa-brain thinking-icon"></i>
                    <span class="thinking-text">${randomMessage}</span>
                    <div class="thinking-dots">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    chatMessages.insertAdjacentHTML('beforeend', thinkingHtml);
    scrollToBottom();
    return thinkingId;
}

// Thinking bubble'ı kaldır
function hideThinkingBubble(thinkingId) {
    if (thinkingId) {
        const element = document.getElementById(thinkingId);
        if (element) {
            element.style.transition = 'opacity 0.3s ease';
            element.style.opacity = '0';
            setTimeout(() => {
                element.remove();
            }, 300);
        }
    }
}

function showTyping(show) {
    if (typingIndicator) {
        typingIndicator.style.display = show ? 'block' : 'none';
        if (show) {
            scrollToBottom();
        }
    }
}

// Progress indicator with step-by-step feedback
function updateTypingIndicatorWithProgress(step, message) {
    if (typingIndicator) {
        typingIndicator.style.display = 'block';
        
        // Progress mesajını güncelle
        const progressText = typingIndicator.querySelector('small');
        if (progressText) {
            progressText.innerHTML = `<i class="fas fa-cog fa-spin"></i> ${message}`;
        }
        
        scrollToBottom();
    }
}

// Session Management Functions
function loadSessionList() {
    console.log('🔄 Loading session list...');
    fetch('/api/sessions')
        .then(response => response.json())
        .then(data => {
            console.log('📋 Session list response:', data);
            if (data.success) {
                sessions = data.sessions;
                console.log(`✅ ${sessions.length} sessions loaded`);
                renderSessionSidebar();
                updateSessionDisplay();
            } else {
                console.error('❌ Session loading failed:', data.error);
            }
        })
        .catch(error => {
            console.error('❌ Session listesi yüklenemedi:', error);
        });
}

function renderSessionSidebar() {
    if (!sessionSidebar) return;
    
    if (sessions.length === 0) {
        sessionSidebar.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-inbox fa-2x mb-2"></i>
                <div>Henüz session yok</div>
                <small>Yeni bir konuşma başlatın</small>
            </div>
        `;
        return;
    }

    const sessionHTML = sessions.map(session => {
        const isActive = session.session_id === currentSessionId;
        const shortId = session.session_id.substring(0, 8);
        const sessionName = session.session_name || `Session ${shortId}`;
        const lastActivity = new Date(session.last_activity).toLocaleDateString('tr-TR', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        return `
            <div class="session-item ${isActive ? 'active' : ''}" 
                 style="cursor: pointer; padding: 12px; margin: 4px 0; border-radius: 8px; 
                        ${isActive ? 'background: #007bff; color: white;' : 'background: #f8f9fa; border: 1px solid #dee2e6;'}
                        transition: all 0.2s ease;"
                 onclick="loadSession('${session.session_id}')"
                 onmouseover="if(!this.classList.contains('active')) this.style.background='#e9ecef'"
                 onmouseout="if(!this.classList.contains('active')) this.style.background='#f8f9fa'">
                
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div style="font-weight: 600; font-size: 0.9em;" class="mb-1">
                            <i class="fas fa-comments me-1"></i>
                            ${sessionName}
                        </div>
                        <div style="font-size: 0.75em; opacity: 0.8;" class="mb-1">
                            <i class="fas fa-clock me-1"></i>
                            ${lastActivity}
                        </div>
                        <div style="font-size: 0.75em; opacity: 0.8;">
                            <i class="fas fa-message me-1"></i>
                            ${session.message_count || 0} mesaj
                        </div>
                    </div>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-secondary"
                                style="padding: 2px 6px; font-size: 0.7em;"
                                onclick="event.stopPropagation(); renameSession('${session.session_id}')"
                                title="Session adını değiştir">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn ${isActive ? 'btn-light' : 'btn-outline-danger'}"
                                style="padding: 2px 6px; font-size: 0.7em;"
                                onclick="event.stopPropagation(); deleteSession('${session.session_id}')"
                                title="Session'ı sil">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }).join('');

    sessionSidebar.innerHTML = sessionHTML;
}

function renameSession(sessionId) {
    const session = sessions.find(s => s.session_id === sessionId);
    const currentName = session && session.session_name ? session.session_name : `Session ${sessionId.substring(0, 8)}`;
    const newName = prompt('Yeni session adı:', currentName);
    if (!newName || !newName.trim()) {
        return;
    }

    fetch(`/api/session/${sessionId}/rename`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ new_name: newName.trim() })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            loadSessionList();
        } else {
            alert('Session adı değiştirilemedi: ' + (data.error || 'Bilinmeyen hata'));
        }
    })
    .catch(error => {
        console.error('Session rename error:', error);
        alert('Session adı değiştirilemedi');
    });
}

function deleteSession(sessionId) {
    if (!confirm('Bu session\'ı silmek istediğinizden emin misiniz?')) {
        return;
    }
    
    fetch(`/api/session/${sessionId}/delete`, { method: 'DELETE' })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Eğer silinen session aktif session ise yeni bir tane oluştur
                if (sessionId === currentSessionId) {
                    newSession();
                }
                // Session listesini yenile
                loadSessionList();
            } else {
                alert('Session silinemedi: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Session silme hatası:', error);
            alert('Session silinemedi');
        });
}

function loadSession(sessionId) {
    if (isProcessing) {
        alert('Yanıt beklenirken session değiştirilemez.');
        return;
    }
    // Session değişiyor, her durumda yükle
    console.log(`🔄 Session yükleniyor: ${sessionId}`);

    currentSessionId = sessionId;

    // Sunucuya aktif session değişimini bildir
    fetch(`/api/session/${sessionId}/switch`, { method: 'POST' })
        .catch(error => console.error('Session switch error:', error));

    loadSessionHistory(sessionId);
    renderSessionSidebar(); // Aktif session'ı güncelle
    updateSessionDisplay();

    // Session listesi güncellensin
    loadSessionList();
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
    
    const sessionName = currentSessionDisplay ? currentSessionDisplay.textContent : currentSessionId.substring(0, 8);
    
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
    if (isProcessing) {
        alert('Yanıt beklenirken session değiştirilemez.');
        return;
    }
    if (sessionId === currentSessionId) return;

    currentSessionId = sessionId;
    if (currentSessionDisplay) {
        currentSessionDisplay.textContent = sessionName;
    }

    loadSessionHistory(sessionId);

    // Update URL
    const newUrl = new URL(window.location);
    newUrl.searchParams.set('session', sessionId);
    window.history.pushState({}, '', newUrl);
}

function loadSessionHistory(sessionId) {
    // Eğer sessionId yoksa çık
    if (!sessionId) {
        console.log('⚠️ Session ID yok, welcome ekranı gösteriliyor');
        initializeChat();
        return;
    }
    
    console.log(`📖 Session geçmişi yükleniyor: ${sessionId}`);
    
    // Mesajları temizle
    chatMessages.innerHTML = '';
    messageCount = 0;
    
    fetch(`/api/session/${sessionId}`)
        .then(response => {
            console.log(`📡 API yanıtı durumu: ${response.status}`);
            return response.json();
        })
        .then(data => {
            console.log('📄 Session verisi:', data);
            
            if (data.success) {
                if (data.history && data.history.length > 0) {
                    console.log(`💬 ${data.history.length} mesaj yükleniyor`);
                    data.history.forEach((msg, index) => {
                        console.log(`  ${index + 1}. ${msg.sender}: ${msg.content.substring(0, 50)}...`);
                        addMessage(msg.sender, msg.content, new Date(msg.timestamp));
                    });
                    messageCount = data.history.length;
                    updateMessageCount();
                } else {
                    console.log('📭 Session boş, welcome ekranı gösteriliyor');
                    initializeChat();
                }
                
                // Update session info
                updateSessionDisplay();
                
                chatMessages.scrollTop = chatMessages.scrollHeight;
                console.log('✅ Session geçmişi başarıyla yüklendi');
            } else {
                console.error('❌ Session yüklenemedi:', data.error);
                initializeChat();
            }
        })
        .catch(error => {
            console.error('🚨 Session geçmişi yüklenirken hata:', error);
            chatMessages.innerHTML = '';
            messageCount = 0;
            initializeChat();
        });
}

// Socket event handlers - Enhanced
socket.on('connect', function() {
    isConnected = true;
    if (connectionStatus) {
        connectionStatus.innerHTML = '<i class="fas fa-circle"></i> Bağlı';
        connectionStatus.className = 'badge bg-success me-2';
    }
    console.log('✅ Connected to server');
    
    // Process pending messages if any
    processPendingMessages();
});

socket.on('disconnect', function() {
    isConnected = false;
    if (connectionStatus) {
        connectionStatus.innerHTML = '<i class="fas fa-circle"></i> Bağlantı Kesildi';
        connectionStatus.className = 'badge bg-danger me-2';
    }
    console.log('❌ Disconnected from server');
});

socket.on('reconnect', function() {
    console.log('🔄 Reconnected to server');
    if (connectionStatus) {
        connectionStatus.innerHTML = '<i class="fas fa-circle"></i> Yeniden Bağlandı';
        connectionStatus.className = 'badge bg-success me-2';
    }
    processPendingMessages();
});

socket.on('status', function(data) {
    console.log('📊 Status:', data.message);
    if (data.connected) {
        isConnected = true;
    }
});

socket.on('new_session', function(data) {
    currentSessionId = data.session_id;
    updateSessionDisplay();
    console.log('🆕 New session created:', currentSessionId);
});

socket.on('message_received', function(data) {
    console.log('📨 Message received confirmation:', data.message_id);
    // Clear timeout for this message
    if (messageTimeouts.has(data.message_id)) {
        clearTimeout(messageTimeouts.get(data.message_id));
        messageTimeouts.delete(data.message_id);
    }
});

socket.on('message_status', function(data) {
    console.log('📊 Message status:', data.status, 'for:', data.message_id);
    // Handle different statuses: received, processing, completed, error
});

socket.on('typing', function(data) {
    showTyping(data.status);
});

// Progress update handler - Kullanıcıya işlem durumu hakkında bilgi verir
socket.on('progress_update', function(data) {
    updateTypingIndicatorWithProgress(data.step, data.message);
});

socket.on('message_response', function(data) {
    showTyping(false);
    
    // Hide thinking bubble if provided
    if (data.thinking_id) {
        hideThinkingBubble(data.thinking_id);
    }
    
    addMessage('assistant', data.message, new Date());
    updateLastActivity();
    
    // Update session ID if provided
    if (data.session_id && !currentSessionId) {
        currentSessionId = data.session_id;
        updateSessionDisplay();
    }
    
    // MESAJ İŞLEME BİTTİ - INPUT'U AKTİF ET
    isProcessing = false;
    enableInput();
    
    // Refresh session list to show updated activity
    setTimeout(loadSessionList, 1000);
    
    console.log('✅ Message response received');
});

socket.on('error', function(data) {
    showTyping(false);
    
    // Hide thinking bubble on error
    if (data.thinking_id) {
        hideThinkingBubble(data.thinking_id);
    }
    
    addMessage('assistant', `❌ Hata: ${data.message}`);
    console.error('🚨 Socket error:', data.message);
    
    // HATA DURUMUNDA DA INPUT'U AKTİF ET
    isProcessing = false;
    enableInput();
    
    // Clear timeout if message_id provided
    if (data.message_id && messageTimeouts.has(data.message_id)) {
        clearTimeout(messageTimeouts.get(data.message_id));
        messageTimeouts.delete(data.message_id);
    }
});

// Connection timeout handling
socket.on('connect_error', function(error) {
    console.error('🚨 Connection error:', error);
    if (connectionStatus) {
        connectionStatus.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Bağlantı Hatası';
        connectionStatus.className = 'badge bg-warning me-2';
    }
});

// Auto-focus message input
if (messageInput) {
    messageInput.focus();
}
