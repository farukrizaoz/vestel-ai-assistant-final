"""
Vestel Agent System - Test dosyası
"""

from main import run_vestel_system, VestelAgentSystem

# Test
if __name__ == "__main__":
    print("🚀 Vestel Modüler Agent Sistemi")
    print("="*50)
    
    # Sistem oluştur
    system = VestelAgentSystem()
    
    print(f"📱 Session ID: {system.session_id}")
    print("\n🎯 SİSTEM ÖZELLİKLERİ:")
    print("✅ Modüler yapı")
    print("✅ State management") 
    print("✅ PDF analizi")
    print("✅ Quickstart guide")
    print("✅ Session management")
    print("✅ Akıllı routing")
    
    # Test sorgusu
    test_query = "650 litre Wi-Fi buzdolabı arıyorum"
    print(f"\n💬 Test: {test_query}")
    
    result = system.process_query(test_query)
    
    print(f"\n✅ Test tamamlandı!")
