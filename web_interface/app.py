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
from agent_system.state_manager import ConversationManager, get_conversation_manager, hydrate_sessions_from_disk

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vestel-agent-secret-key-2025'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables
agent_system = VestelAgentSystem()
conversation_manager = ConversationManager()

# UYGULAMA BAŞLANGICINDA HYDRATE ET
try:
    hydrated_count = hydrate_sessions_from_disk()
    if hydrated_count > 0:
        print(f"🧩 {hydrated_count} session DB'ye hydrate edildi.")
except Exception as e:
    print(f"⚠️ Başlangıçta hydrate işlemi başarısız: {e}")

@app.route('/')
def index():
    """Ana sayfa - Chat arayüzü"""
    try:
        hydrate_sessions_from_disk()  # HYDRATE ET
        sessions = conversation_manager.list_sessions()
        sorted_sessions = sorted(sessions, 
                                 key=lambda x: x.get('last_activity', '1970-01-01T00:00:00'), 
                                 reverse=True)
        
        if sorted_sessions:
            # En son aktif olan session'ı seç
            latest_session_id = sorted_sessions[0].get('session_id')
            print(f"🎯 Varsayılan session seçildi: {latest_session_id}")
            return render_template('index.html', 
                                   session_id=latest_session_id, 
                                   sessions=sorted_sessions)
        else:
            # Hiç session yoksa, boş bir sayfa göster
            print("🚫 Hiç session bulunamadı. Boş başlangıç sayfası gösteriliyor.")
            return render_template('index.html', 
                                   session_id=None, 
                                   sessions=[])
    except Exception as e:
        print(f"❌ Session yükleme hatası: {e}")
        # Hata durumunda da boş sayfa göster
        return render_template('index.html', 
                               session_id=None, 
                               sessions=[])

# Admin route'unu kaldırıyoruz
# @app.route('/admin')
# def admin():
#     """Admin paneli - Session yönetimi"""
#     return render_template('admin.html')

@app.route('/sessions')
@app.route('/api/sessions')
def get_sessions():
    """Mevcut session'ları listele - LAST_ACTIVITY'YE GÖRE SIRALI"""
    try:
        hydrate_sessions_from_disk()  # HYDRATE ET
        sessions = conversation_manager.list_sessions()
        # Session'ları last_activity'ye göre sırala (en yeni en başta)
        sorted_sessions = sorted(sessions, 
                               key=lambda x: x.get('last_activity', '1970-01-01T00:00:00'), 
                               reverse=True)
        
        print(f"📋 {len(sorted_sessions)} session listelendi (activity sıralı)")
        return jsonify({
            'success': True, 
            'sessions': sorted_sessions
        })
    except Exception as e:
        print(f"❌ Session listing error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
    print('✅ Client connected')
    emit('status', {'message': 'Vestel AI Assistant\'a bağlandınız', 'connected': True})

@socketio.on('disconnect')
def handle_disconnect():
    """WebSocket bağlantısı kesildi"""
    print('❌ Client disconnected')

@socketio.on('send_message')
def handle_message(data):
    """Kullanıcı mesajını işle"""
    message_id = str(uuid.uuid4())  # Her mesaj için unique ID
    
    try:
        user_message = data.get('message', '')
        session_id = data.get('session_id', '')
        thinking_id = data.get('thinking_id', '')  # Frontend'ten gelen thinking bubble ID
        
        print(f"📨 Mesaj alındı: '{user_message}' (session: {session_id})")
        
        # Mesaj alındı onayı gönder
        emit('message_received', {
            'message_id': message_id,
            'status': 'received'
        })
        
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
        
        # Processing başladı - thinking bubble çalışıyor
        emit('typing', {'status': True})
        emit('message_status', {
            'message_id': message_id,
            'status': 'processing'
        })
        
        print(f"🤖 Agent system'e gönderiliyor...")
        
        # Agent'a gönder ve cevap al (session-specific) - SIMPLE TIMEOUT
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
        import time
        
        def run_agent_query():
            return agent_system.process_query(user_message, session_id)
        
        try:
            # ThreadPool ile timeout kontrol et
            with ThreadPoolExecutor() as executor:
                future = executor.submit(run_agent_query)
                try:
                    response = future.result(timeout=45)  # 45 saniye timeout - çok kısa
                    print(f"✅ Agent cevabı alındı: '{response[:100]}...'")
                except FutureTimeoutError:
                    response = "⏱️ İşlem çok uzun sürdü. Lütfen sorunuzu daha basit bir şekilde tekrar sorun veya daha sonra tekrar deneyin."
                    print("⏱️ Agent işlemi timeout'a uğradı")
        except Exception as agent_error:
            response = f"🚫 Sistem hatası: {str(agent_error)}. Lütfen tekrar deneyin."
            print(f"❌ Agent hatası: {str(agent_error)}")
        
        # Agent cevabını kaydet
        session_manager.add_message(session_id, 'assistant', response)
        
        # Session activity'yi manuel olarak da güncelle
        session_manager.save_session()
        
        # Processing bitti
        emit('typing', {'status': False})
        emit('message_status', {
            'message_id': message_id,
            'status': 'completed'
        })
        
        # Cevabı gönder - thinking_id'yi de ekle
        emit('message_response', {
            'message': response,
            'session_id': session_id,
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'message_id': message_id,
            'thinking_id': thinking_id  # Thinking bubble'ı kaldırmak için
        })
        print(f"📤 Cevap gönderildi")
        
    except Exception as e:
        print(f"❌ Hata oluştu: {str(e)}")
        emit('typing', {'status': False})
        emit('message_status', {
            'message_id': message_id,
            'status': 'error'
        })
        emit('error', {
            'message': f'🚫 Sistem hatası: {str(e)}. Lütfen tekrar deneyin.',
            'message_id': message_id,
            'thinking_id': thinking_id  # Error durumunda da thinking bubble'ı kaldır
        })

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
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)
