"""
Tasks - Agent görevleri
"""
from crewai import Task

from agent_system.state_manager import get_conversation_manager

def create_routing_task(user_query: str, routing_agent, session_id: str = None) -> Task:
    """Ana routing görevi"""
    conversation_manager = get_conversation_manager(session_id)
    
    # Detaylı context al
    detailed_context = conversation_manager.get_detailed_context()
    last_product = conversation_manager.get_last_mentioned_product()
    
    # Son 5 mesajı al - daha kapsamlı context için
    recent_messages = conversation_manager.conversation_history[-5:] if conversation_manager.conversation_history else []
    
    context_info = detailed_context
    if last_product and ("bu" in user_query.lower() or "bu ürün" in user_query.lower() or "alayım" in user_query.lower()):
        context_info += f"\n🎯 ÜRÜN REFERANSI: Kullanıcı muhtemelen '{last_product}' ürününden bahsediyor.\n"
    
    # Son mesajlarda verilen teknik bilgileri kontrol et
    if recent_messages:
        context_info += "\n📋 **SON KONUŞMA DETAYLARI:**\n"
        for msg in recent_messages:
            if msg['sender'] == 'assistant' and len(msg['content']) > 100:
                # Eğer önceki cevap teknik detaylar içeriyorsa kısaca belirt
                if any(keyword in msg['content'].lower() for keyword in ['hdmi', 'usb', 'bağlantı', 'port', 'teknik', 'özellik']):
                    context_info += f"⚠️ ÖNCEDEN VERİLEN BİLGİ: Bu ürün için daha önce teknik detaylar verilmiştir.\n"
                    break
    
    return Task(
        description=(
            f"Kullanıcının şu isteğini analiz et: '{user_query}'\n\n"
            f"{context_info}\n"
            "⚠️ **ÖNEMLİ:** Eğer önceki mesajlarda bu konuda bilgi verdiysen, o bilgiyi tekrar kullan!\n\n"
            "Hangi aksiyonu alacağına karar ver:\n"
            "1. ÜRÜN ARAMA: Ürün araması gerekiyorsa Product Search kullan\n"
            "2. KOMPLEKS SORU: Teknik detay/kullanım sorunu varsa 'Vestel Kullanım Kılavuzu Uzmanı'na delege et\n"
            "3. SATIN ALMA: Satın alma niyeti varsa 'Vestel Kurulum Uzmanı'na delege et\n"
            "4. ÖNCEKİ BİLGİ TEKRARI: Eğer bu soruya daha önce cevap verdiysen, aynı cevabı tekrarla\n\n"
            "SATIN ALMA BELİRTİLERİ:\n"
            "- 'alayım', 'satın alma', 'satın al', 'siparişi ver', 'sipariş'\n"
            "- 'bu ürünü istiyorum', 'bunu alacağım', 'kaça mal olur'\n"
            "- 'fiyat', 'ne kadar', 'nereden alabilirim', 'mağaza'\n"
            "- 'kurulum', 'teslimat', 'garanti', 'montaj'\n\n"
            "ÖNEMLİ KURALLAR:\n"
            "- SADECE database'den gelen ürünleri listele!\n"
            "- Kullanıcı 'bu', 'bu ürün', 'bunu' derse context'teki son ürünü kullan\n"
            "- 'hangi ... alıyordum', 'hatırlat' sorularında context'i kontrol et\n"
            "- Önceki cevaplarında verdiğin bilgileri hatırla ve tutarlı ol!"
        ),
        expected_output="Uygun uzman seçimi ve yanıt",
        agent=routing_agent
    )

def create_pdf_task(user_query: str, product_name: str, pdf_agent) -> Task:
    """PDF analizi görevi"""
    return Task(
        description=(
            f"'{product_name}' ürünü için şu soruya yanıt ver: '{user_query}'\n"
            "PDF Analysis aracını kullanarak detaylı teknik bilgi sağla."
        ),
        expected_output="Kılavuzdan detaylı teknik bilgi",
        agent=pdf_agent
    )

def create_quickstart_task(product_name: str, quickstart_agent) -> Task:
    """Quickstart görevi"""
    return Task(
        description=(
            f"'{product_name}' ürünü için hızlı başlangıç rehberi oluştur.\n"
            "Kurulum, ilk kullanım, önemli ipuçları dahil et."
        ),
        expected_output="Hızlı başlangıç rehberi",
        agent=quickstart_agent
    )
