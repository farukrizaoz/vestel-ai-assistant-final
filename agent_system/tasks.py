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
    
    context_info = detailed_context
    if last_product and ("bu" in user_query.lower() or "bu ürün" in user_query.lower() or "alayım" in user_query.lower()):
        context_info += f"\n🎯 ÜRÜN REFERANSI: Kullanıcı muhtemelen '{last_product}' ürününden bahsediyor.\n"
    
    return Task(
        description=(
            f"Kullanıcının şu isteğini analiz et: '{user_query}'\n\n"
            f"{context_info}\n\n"
            "Hangi aksiyonu alacağına karar ver:\n"
            "1. ÜRÜN ARAMA: Ürün araması gerekiyorsa Product Search kullan\n"
            "2. MANUEL SORU: Teknik detay/kullanım sorunu varsa PDF Agent'a yönlendir\n" 
            "3. SATIN ALMA: Satın alma niyeti varsa Quickstart Agent'a yönlendir\n\n"
            "SATIN ALMA BELİRTİLERİ:\n"
            "- 'alayım', 'satın alma', 'satın al', 'fiyat', 'ne kadar'\n"
            "- 'nereden alabilirim', 'mağaza', 'kurulum', 'teslimat'\n\n"
            "ÖNEMLİ KURALLAR:\n"
            "- Kullanıcı 'bu', 'bu ürün', 'bunu' derse context'teki son ürünü kullan\n"
            "- Database'den gelen ürünleri listele\n"
            "- Kullanıcının ihtiyacına göre uygun ve yeterli bilgi ver"
        ),
        expected_output="Kullanıcının ihtiyacına uygun yanıt",
        agent=routing_agent
    )

def create_pdf_task(user_query: str, product_name: str, pdf_agent) -> Task:
    """PDF analizi görevi"""
    return Task(
        description=(
            f"'{product_name}' ürünü için şu soruya yanıt ver: '{user_query}'\n\n"
            "GÖREV ADIMLARIN:\n"
            "1. PDF Analysis tool'unu '{product_name}' parametresiyle çağır\n"
            "2. Tool sana kılavuzun TAM İÇERİĞİNİ verecek\n"
            "3. Bu tam içerikten kullanıcının sorusuna uygun bölümleri seç\n"
            "4. Seçtiğin bölümleri düzenle ve kullanıcıya sun\n\n"
            "FİLTRELEME MANTIGI:\n"
            "• Sadece soruyla ilgili kısımları al\n"
            "• Gereksiz detayları çıkar\n"
            "• Önemli uyarıları dahil et\n"
            "• Adım adım açıkla\n\n"
            "Sen PDF'in tam içeriğini alacaksın ama kullanıcıya sadece ihtiyacı olan kısmı vereceksin!"
        ),
        expected_output="Kullanıcının sorusuna göre filtrelenmiş ve organize edilmiş kılavuz bilgisi",
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
