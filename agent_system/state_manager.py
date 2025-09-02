"""
State Management - Konuşma geçmişi ve session yönetimi
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from agent_system.config import PROJECT_ROOT
from agent_system.session_db import session_db

# Session dosyaları için klasör
SESSIONS_DIR = Path(PROJECT_ROOT) / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

class ConversationManager:
    """Konuşma durumunu yönetir"""
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.sessions_dir = SESSIONS_DIR
        self.session_file = SESSIONS_DIR / f"{self.session_id}.json"
        self.conversation_history = []
        self.current_products = []
        self.load_session()
        
        # DB'ye session kaydı oluştur
        session_db.create_session(self.session_id)
    
    def load_session(self):
        """Oturum verilerini yükle"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.conversation_history = data.get('history', [])
                    self.current_products = data.get('products', [])
            except:
                # Dosya bozuksa yeni başla
                self.conversation_history = []
                self.current_products = []
    
    def save_session(self):
        """Oturum verilerini kaydet"""
        # Eğer session dosyası mevcutsa created_at'i koru
        created_at = datetime.now().isoformat()
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                    created_at = existing_data.get('created_at', created_at)
            except:
                pass  # Hata durumunda yeni tarih kullan
        
        data = {
            'session_id': self.session_id,
            'created_at': created_at,
            'last_activity': datetime.now().isoformat(),
            'history': self.conversation_history,
            'products': self.current_products,
            'metadata': {
                'message_count': len(self.conversation_history),
                'product_count': len(self.current_products)
            }
        }
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # DB'yi güncelle
        session_db.update_session_activity(
            self.session_id,
            len(self.conversation_history),
            len(self.current_products)
        )
    
    def create_session(self, session_id: str = None):
        """Yeni session oluştur"""
        if session_id:
            self.session_id = session_id
        else:
            self.session_id = str(uuid.uuid4())
        
        self.session_file = SESSIONS_DIR / f"{self.session_id}.json"
        self.conversation_history = []
        self.current_products = []
        self.save_session()
        
        # DB'ye kaydet
        session_db.create_session(self.session_id)
        
        return self.session_id
    
    def add_message(self, session_id: str, sender: str, content: str):
        """Belirli session'a mesaj ekle"""
        if session_id != self.session_id:
            # Farklı session ise yükle
            self.session_id = session_id
            self.session_file = SESSIONS_DIR / f"{self.session_id}.json"
            self.load_session()
        
        # Akıllı duplike mesaj kontrolü - sadece 5 saniye içinde aynı mesaj gönderilirse engelleyelim
        if self.conversation_history:
            last_message = self.conversation_history[-1]
            if (last_message['sender'] == sender and 
                last_message['content'] == content):
                # Son mesajın zamanını kontrol et
                try:
                    last_time = datetime.fromisoformat(last_message['timestamp'])
                    current_time = datetime.now()
                    time_diff = (current_time - last_time).total_seconds()
                    
                    # Sadece 5 saniye içinde aynı mesaj gönderilirse engelle
                    if time_diff < 5:
                        print(f"⚠️ Duplike mesaj tespit edildi (5sn içinde), eklenmedi: {sender}: {content[:50]}...")
                        return
                except Exception as e:
                    # Timestamp parse hatası durumunda devam et
                    print(f"⚠️ Timestamp parse hatası: {e}")
                    pass
        
        message = {
            'timestamp': datetime.now().isoformat(),
            'sender': sender,
            'content': content
        }
        self.conversation_history.append(message)
        self.save_session()
    
    def get_conversation_history(self, session_id: str = None):
        """Belirli session'ın konuşma geçmişini al"""
        if session_id and session_id != self.session_id:
            # Geçici olarak o session'ı yükle
            temp_file = SESSIONS_DIR / f"{session_id}.json"
            if temp_file.exists():
                try:
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        return data.get('history', [])
                except:
                    return []
            return []
        return self.conversation_history
    
    def add_products(self, products: list):
        """Bulunan ürünleri kaydet"""
        self.current_products.extend(products)
        self.save_session()
    
    def clear_products(self):
        """Ürün listesini temizle"""
        self.current_products = []
        self.save_session()
    
    def get_context(self) -> str:
        """Son konuşma bağlamını al"""
        if not self.conversation_history:
            return "Yeni konuşma."
        
        recent = self.conversation_history[-3:]
        context = "Son konuşma:\n"
        for msg in recent:
            role = "👤" if msg['sender'] == 'user' else "🤖"
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            context += f"{role} {content}\n"
        return context
    
    def get_detailed_context(self) -> str:
        """Detaylı konuşma bağlamını al - product memory dahil"""
        context = ""
        
        # Son 5 mesajı al
        if self.conversation_history:
            recent = self.conversation_history[-5:]
            context += "📋 Konuşma Geçmişi:\n"
            for msg in recent:
                role = "👤" if msg['sender'] == 'user' else "🤖"
                content = msg['content'][:150] + "..." if len(msg['content']) > 150 else msg['content']
                context += f"{role} {content}\n"
            context += "\n"
        
        # Akdaki ürünleri ekle
        if self.current_products:
            context += "🛍️ Session'da Bahsedilen Ürünler:\n"
            for product in self.current_products[-3:]:  # Son 3 ürün
                context += f"• {product.get('name', 'Bilinmeyen ürün')}\n"
            context += "\n"
        
        # Product intent memory - Ürün seçimi detect et
        mentioned_products = self.extract_mentioned_products()
        if mentioned_products:
            context += "🎯 Kullanıcının İlgilendiği Ürünler:\n"
            for product in mentioned_products[-2:]:  # Son 2 ilgi
                context += f"• {product}\n"
            context += "\n"
        
        return context if context else "Yeni konuşma başlıyor."
    
    def extract_mentioned_products(self) -> List[str]:
        """Konuşmalardan bahsedilen ürünleri çıkar"""
        mentioned = []
        keywords = ['buzdolabı', 'fırın', 'çamaşır makinesi', 'televizyon', 'tv', 'mikrodalga', 'dishwasher', 'bulaşık makinesi']
        
        for msg in self.conversation_history:
            if msg['sender'] == 'user':
                content = msg['content'].lower()
                for keyword in keywords:
                    if keyword in content:
                        mentioned.append(keyword.title())
                        break
        
        return list(set(mentioned))  # Unique products
    
    def add_product_context(self, product_name: str, product_details: dict = None):
        """Ürün context'ini ekle - session memory için"""
        product_info = {
            'name': product_name,
            'timestamp': datetime.now().isoformat(),
            'details': product_details or {}
        }
        
        # Ürünü current_products'a ekle
        self.current_products.append(product_info)
        
        # Son 5 ürünü tut
        if len(self.current_products) > 5:
            self.current_products = self.current_products[-5:]
        
        self.save_session()
    
    def get_last_mentioned_product(self) -> str:
        """Son bahsedilen ürünü al"""
        if self.current_products:
            return self.current_products[-1].get('name', '')
        
        # History'den de bak
        mentioned = self.extract_mentioned_products()
        return mentioned[-1] if mentioned else ''
    
    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Session adını değiştir"""
        return session_db.rename_session(session_id, new_name)
    
    def get_session_info(self, session_id: str):
        """Session bilgilerini al"""
        # DB'den meta bilgileri al
        db_info = session_db.get_session_info(session_id)
        
        # JSON dosyasından konuşma geçmişini al
        history = self.get_conversation_history(session_id)
        
        # Products'ları al
        temp_file = SESSIONS_DIR / f"{session_id}.json"
        products = []
        if temp_file.exists():
            try:
                with open(temp_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    products = data.get('products', [])
            except:
                pass
        
        if db_info:
            return {
                **db_info,
                'history': history,
                'products': products
            }
        
        return {
            'session_id': session_id,
            'session_name': f"Chat {session_id[:8]}",
            'created_at': 'Bilinmiyor',
            'last_activity': 'Bilinmiyor',
            'message_count': len(history),
            'product_count': len(products),
            'history': history,
            'products': products
        }
    
    @staticmethod
    def list_sessions() -> List[Dict]:
        """Tüm oturumları listele"""
        return session_db.list_all_sessions()

# Global session cache
_session_cache = {}

def get_conversation_manager(session_id: str = None):
    """Global conversation manager'ı al veya oluştur - session cache ile"""
    global _session_cache
    
    # Default session
    if session_id is None:
        session_id = "default"
    
    # Cache'den kontrol et
    if session_id in _session_cache:
        manager = _session_cache[session_id]
        # Session file'ı tekrar yükle (persistence için)
        manager.load_session()
        return manager
    
    # Yeni manager oluştur ve cache'e ekle
    manager = ConversationManager(session_id)
    _session_cache[session_id] = manager
    
    # Cache boyutunu sınırla (son 10 session)
    if len(_session_cache) > 10:
        # En eski session'ı sil
        oldest_session = next(iter(_session_cache))
        del _session_cache[oldest_session]
    
    return manager

def hydrate_sessions_from_disk() -> int:
    """
    sessions/ klasöründeki JSON dosyalarını tarar,
    DB'de kaydı olmayanları ekler ve metadata/sayaçları senkronize eder.
    Dönüş: eklenen/güncellenen kayıt sayısı
    """
    added_or_updated = 0
    if not SESSIONS_DIR.exists():
        return 0
        
    for json_path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            sid = data.get("session_id") or json_path.stem
            created_at = data.get("created_at") or datetime.now().isoformat()
            last_activity = data.get("last_activity") or created_at
            history = data.get("history", [])
            products = data.get("products", [])
            metadata = data.get("metadata", {})
            session_name = metadata.get("session_name")

            # DB'de var mı?
            row = session_db.get_session_info(sid)
            if not row:
                # Yoksa oluştur
                session_db.create_session(sid, session_name)
                added_or_updated += 1

            # Aktivite ve sayaçları senkronize et
            session_db.update_session_activity(
                sid,
                message_count=len(history),
                product_count=len(products),
                last_activity=last_activity
            )

            # İsim senkronizasyonu (eğer JSON'da varsa ve DB'dekinden farklıysa)
            if session_name and (not row or row.get('session_name') != session_name):
                session_db.rename_session(sid, session_name)
                if not row: # Zaten eklendi sayıldı
                    pass
                else:
                    added_or_updated +=1

        except Exception as e:
            print(f"[hydrate] {json_path.name} senkronize edilemedi: {e}")
            
    return added_or_updated
