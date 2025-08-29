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
        data = {
            'session_id': self.session_id,
            'created_at': datetime.now().isoformat(),
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
