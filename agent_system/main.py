"""
Vestel Agent System - Ana sistem
"""
print("🚀 Starting Vestel Agent System...")

import os
from crewai import Crew, Process
import google.generativeai as genai
print("📦 genai imported")

# Config'i import et ki .env yüklensin
from agent_system import config
print("📦 config imported")
from agent_system.agents.router_agent import create_router_agent
print("📦 router_agent imported")
from agent_system.agents.pdf_agent import create_pdf_agent  
print("📦 pdf_agent imported")
from agent_system.agents.quickstart_agent import create_quickstart_agent
print("📦 quickstart_agent imported")
from agent_system.tasks import create_routing_task
print("📦 tasks imported")
from agent_system.state_manager import get_conversation_manager, ConversationManager
print("📦 state_manager imported")
print("✅ All imports completed")

class VestelAgentSystem:
    """Vestel müşteri hizmetleri agent sistemi"""
    
    def __init__(self, session_id: str = None):
        self.conversation_manager = get_conversation_manager(session_id)
        
        # Google API konfigürasyonu
        if os.getenv('GOOGLE_API_KEY'):
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            self.conversation_manager.enable_google_embedding = True
            print(f"✅ Google API Key loaded: {os.getenv('GOOGLE_API_KEY')[:10]}...")
        else:
            print("❌ GOOGLE_API_KEY not found!")
            
        # Yeni storage dizini - Google embeddings için
        os.environ["CREWAI_STORAGE_DIR"] = "./crewai_storage_gemini"
        
        # Agent'ları oluştur
        self.router_agent = create_router_agent()
        self.pdf_agent = create_pdf_agent()
        self.quickstart_agent = create_quickstart_agent()
    
    def process_query(self, user_query: str, session_id: str = None) -> str:
        """Kullanıcı sorgusu işle"""
        
        # Session ID değişmişse conversation manager'ı güncelle
        if session_id and session_id != self.conversation_manager.session_id:
            self.conversation_manager = get_conversation_manager(session_id)
        
        print(f"💬 Kullanıcı: {user_query}")
        print(f"📱 Session: {self.conversation_manager.session_id}")
        
        # Mesajı kaydet (düzeltilmiş format)
        self.conversation_manager.add_message(self.conversation_manager.session_id, 'user', user_query)
        
        # Routing task oluştur
        routing_task = create_routing_task(user_query, self.router_agent, self.conversation_manager.session_id)
        
        # Crew oluştur ve çalıştır
        crew = Crew(
            agents=[self.router_agent, self.pdf_agent, self.quickstart_agent],
            tasks=[routing_task],
            process=Process.sequential,
            memory=False,  # Memory'yi kapat - session bazında kendi memory'miz var
            verbose=True
        )
        
        result = crew.kickoff()
        
        # Sonucu kaydet (düzeltilmiş format)
        self.conversation_manager.add_message(self.conversation_manager.session_id, 'assistant', str(result))
        
        return str(result)
    
    @property
    def session_id(self) -> str:
        """Mevcut session ID"""
        return self.conversation_manager.session_id
    
    def get_conversation_history(self) -> list:
        """Konuşma geçmişini al"""
        return self.conversation_manager.conversation_history
    
    def get_current_products(self) -> list:
        """Mevcut ürünleri al"""
        return self.conversation_manager.current_products
    
    @staticmethod
    def list_sessions() -> list:
        """Tüm oturumları listele"""
        return ConversationManager.list_sessions()

# Basit interface
def run_vestel_system(user_query: str, session_id: str = None) -> str:
    """Sistemi çalıştır"""
    
    system = VestelAgentSystem(session_id)
    
    print("🚀 Vestel Agent Sistemi")
    print(f"📱 Session: {system.session_id}")
    print("="*50)
    
    result = system.process_query(user_query)
    
    print("\n✅ Sonuç:")
    print("="*50)
    print(result)
    print("="*50)
    
    return result

# Web server başlat
if __name__ == "__main__":
    print("🌐 Starting web server...")
    import subprocess
    import sys
    import os
    
    # Web interface klasöründeki app.py'yi çalıştır
    project_root = "/home/vestel/Desktop/aproject"
    web_interface_path = os.path.join(project_root, "web_interface", "app.py")
    print(f"📁 Web interface path: {web_interface_path}")
    
    try:
        subprocess.run([sys.executable, web_interface_path], cwd=project_root)
    except KeyboardInterrupt:
        print("\n👋 Web server stopped")
