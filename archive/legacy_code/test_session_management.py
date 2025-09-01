#!/usr/bin/env python3
"""
Session Management Test Script
Bu script yeni session management özelliklerini test eder:
- Session oluşturma ve isimlendirme
- Session'lar arası geçiş
- Context korunumu
- Session renaming
"""

import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'agent_system'))

from agent_system.state_manager import ConversationManager
from agent_system.session_db import SessionDB
from agent_system.main import VestelAgentSystem

def test_session_management():
    print("🧪 Session Management Test Başlatılıyor...")
    
    # ConversationManager'ı başlat
    conv_manager = ConversationManager()
    
    # 1. Yeni session oluştur
    print("\n1️⃣ Yeni session oluşturuluyor...")
    session1_id = conv_manager.create_new_session("Buzdolabı Sorularım")
    print(f"   ✅ Session oluşturuldu: {session1_id}")
    
    # 2. İkinci session oluştur
    session2_id = conv_manager.create_new_session("TV Rehberi")
    print(f"   ✅ İkinci session oluşturuldu: {session2_id}")
    
    # 3. Session listesini göster
    print("\n2️⃣ Mevcut sessionlar:")
    sessions = conv_manager.list_sessions()
    for session in sessions:
        print(f"   📁 {session['session_name']} ({session['session_id'][:8]}...)")
        print(f"      Oluşturulma: {session['created_at']}")
        print(f"      Mesaj sayısı: {session['message_count']}")
        print()
    
    # 4. Session renaming test
    print("3️⃣ Session yeniden isimlendirme...")
    conv_manager.rename_session(session1_id, "Beyaz Eşya Danışmanlığı")
    print("   ✅ Session ismi güncellendi")
    
    # 5. Güncellenmiş session bilgilerini göster
    session_info = conv_manager.get_session_info(session1_id)
    print(f"   📝 Yeni isim: {session_info['session_name']}")
    
    # 6. Session switching test
    print("\n4️⃣ Session switching test...")
    conv_manager.switch_session(session1_id)
    print(f"   🔄 Session değiştirildi: {session1_id[:8]}...")
    
    # 7. Mesaj ekleme ve context test
    print("\n5️⃣ Context preservation test...")
    conv_manager.add_message("user", "Buzdolabım çok ses yapıyor")
    conv_manager.add_message("assistant", "Buzdolabınızın ses sorunu için birkaç kontrol yapabiliriz...")
    
    # Diğer session'a geç
    conv_manager.switch_session(session2_id)
    conv_manager.add_message("user", "Smart TV kurulumu nasıl yapılır?")
    conv_manager.add_message("assistant", "Smart TV kurulumu için şu adımları takip edebilirsiniz...")
    
    # Tekrar ilk session'a dön
    conv_manager.switch_session(session1_id)
    history = conv_manager.get_conversation_history()
    
    print(f"   📚 Session {session1_id[:8]} conversation history:")
    for msg in history:
        role = "👤" if msg['role'] == 'user' else "🤖"
        content = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
        print(f"      {role} {content}")
    
    print("\n6️⃣ Final session durumu:")
    sessions = conv_manager.list_sessions()
    for session in sessions:
        print(f"   📁 {session['session_name']}")
        print(f"      ID: {session['session_id'][:8]}...")
        print(f"      Mesaj sayısı: {session['message_count']}")
        print(f"      Son güncelleme: {session['updated_at']}")
        print()
    
    print("✅ Session Management Test Tamamlandı!")
    return True

if __name__ == "__main__":
    try:
        test_session_management()
    except Exception as e:
        print(f"❌ Test hatası: {e}")
        import traceback
        traceback.print_exc()
