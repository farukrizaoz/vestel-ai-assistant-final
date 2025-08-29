from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import sys
import os
import uuid
from datetime import datetime
import json

# Agent system path ekle
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from agent_system.main import VestelAgentSystem
from agent_system.state_manager import ConversationManager, get_conversation_manager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vestel-agent-secret-key-2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
agent_system = VestelAgentSystem()
conversation_manager = ConversationManager()

@app.route('/')
def index():
    """Ana sayfa - Chat arayüzü"""
    return render_template('index.html')

@app.route('/admin')
def admin():
    """Admin paneli - Session yönetimi"""
    return render_template('admin.html')

@app.route('/api/sessions')
def get_sessions():
    """Tüm session'ları getir"""
    try:
        sessions = conversation_manager.list_sessions()
        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/session/<session_id>')
def get_session_details(session_id):
    """Belirli bir session'ın detaylarını getir"""
    try:
        # Session history al
        history = conversation_manager.get_conversation_history(session_id)
        
        # Session dosyası varsa JSON'dan oku
        session_file = os.path.join(conversation_manager.sessions_dir, f"{session_id}.json")
        session_data = {}
        
        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'history': history,
            'metadata': session_data.get('metadata', {}),
            'products': session_data.get('products', []),
            'created_at': session_data.get('created_at', 'Bilinmiyor'),
            'last_activity': session_data.get('last_activity', 'Bilinmiyor')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/chat/new', methods=['POST'])
def new_chat_session():
    """Yeni chat session başlat"""
    try:
        session_id = conversation_manager.create_session()
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Yeni chat session başlatıldı'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@socketio.on('connect')
def handle_connect():
    """WebSocket bağlantısı kuruldu"""
    print('Client connected')
    emit('status', {'message': 'Vestel AI Assistant\'a bağlandınız'})

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket bağlantısı kesildi"""
    print('Client disconnected')

@socketio.on('send_message')
def handle_message(data):
    """Kullanıcı mesajını işle"""
    try:
        user_message = data.get('message', '')
        session_id = data.get('session_id', '')
        
        print(f"📨 Mesaj alındı: '{user_message}' (session: {session_id})")
        
        if not session_id:
            # Yeni session oluştur
            temp_manager = get_conversation_manager()
            session_id = temp_manager.create_session()
            emit('new_session', {'session_id': session_id})
            print(f"🆕 Yeni session oluşturuldu: {session_id}")
        
        # Session-specific manager al
        session_manager = get_conversation_manager(session_id)
        
        # Kullanıcı mesajını kaydet
        session_manager.add_message(session_id, 'user', user_message)
        
        # Typing indicator
        emit('typing', {'status': True})
        
        print(f"🤖 Agent system'e gönderiliyor...")
        # Agent'a gönder ve cevap al (session-specific)
        response = agent_system.process_query(user_message, session_id)
        print(f"✅ Agent cevabı alındı: '{response[:100]}...'")
        
        # Agent cevabını kaydet
        session_manager.add_message(session_id, 'assistant', response)
        
        # Cevabı gönder
        emit('typing', {'status': False})
        emit('message_response', {
            'message': response,
            'session_id': session_id,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        print(f"📤 Cevap gönderildi")
        
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")
        emit('typing', {'status': False})
        emit('error', {'message': f'Hata oluştu: {str(e)}'})

@app.route('/api/session/<session_id>/rename', methods=['POST'])
def rename_session(session_id):
    """Session adını değiştir"""
    try:
        data = request.get_json()
        new_name = data.get('new_name', '')
        
        if not new_name:
            return jsonify({
                'success': False,
                'error': 'Yeni isim boş olamaz'
            })
        
        success = conversation_manager.rename_session(session_id, new_name)
        
        return jsonify({
            'success': success,
            'message': 'Session adı güncellendi' if success else 'Session adı güncellenemedi'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/session/<session_id>/delete', methods=['DELETE'])
def delete_session(session_id):
    """Session'ı sil"""
    try:
        # JSON dosyasını sil
        session_file = os.path.join(conversation_manager.sessions_dir, f"{session_id}.json")
        if os.path.exists(session_file):
            os.remove(session_file)
        
        # DB'den sil
        from agent_system.session_db import session_db
        session_db.delete_session(session_id)
        
        return jsonify({
            'success': True,
            'message': 'Session başarıyla silindi'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/session/<session_id>/clear', methods=['POST'])
def clear_session(session_id):
    """Session'daki mesajları temizle"""
    try:
        from agent_system.state_manager import get_conversation_manager
        conv_manager = get_conversation_manager(session_id)
        
        # Mesajları temizle
        conv_manager.conversation_history = []
        conv_manager.save_session()
        
        return jsonify({
            'success': True,
            'message': 'Session mesajları temizlendi'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/session/<session_id>/switch', methods=['POST'])
def switch_session(session_id):
    """Session'a geç"""
    try:
        global conversation_manager
        conversation_manager.session_id = session_id
        conversation_manager.session_file = conversation_manager.sessions_dir / f"{session_id}.json"
        conversation_manager.load_session()
        
        # Session bilgilerini al
        session_info = conversation_manager.get_session_info(session_id)
        
        return jsonify({
            'success': True,
            'session_info': session_info,
            'message': f'Session {session_id[:8]} aktif edildi'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@socketio.on('get_session_info')
def handle_session_info(data):
    """Session bilgilerini getir"""
    try:
        session_id = data.get('session_id', '')
        if session_id:
            history = conversation_manager.get_conversation_history(session_id)
            emit('session_info', {
                'session_id': session_id,
                'message_count': len(history),
                'history': history[-10:] if len(history) > 10 else history  # Son 10 mesaj
            })
    except Exception as e:
        emit('error', {'message': f'Session bilgisi alınamadı: {str(e)}'})

if __name__ == '__main__':
    # Templates klasörü oluştur
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    print("🚀 Vestel AI Assistant Web Interface başlatılıyor...")
    print("📱 Ana sayfa: http://localhost:5000")
    print("⚙️ Admin paneli: http://localhost:5000/admin")
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
