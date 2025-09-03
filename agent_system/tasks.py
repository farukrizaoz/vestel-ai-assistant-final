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
        description=f"Kullanıcının şu isteğini analiz et: '{user_query}'\n\n{context_info}",
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
            f"'{product_name}' ürünü için hızlı başlangıç ve genel bilgileri sun.\n\n"
            "İÇERİK:\n"
            "• Kutu açılışı ve ilk kurulum\n"
            "• Temel kullanım ipuçları\n"
            "• Önemli güvenlik uyarıları\n"
            "• Garanti bilgileri\n"
            "• Temizlik ve bakım\n"
            "• Yaygın sorunlar ve çözümler\n\n"
            "AMAÇ: Kullanıcının ürünü güvenli ve etkili şekilde kullanmaya başlamasını sağla."
        ),
        expected_output="Hızlı başlangıç kılavuzu ve genel bilgiler",
        agent=quickstart_agent
    )

def create_technical_support_task(user_query: str, product_name: str, technical_agent) -> Task:
    """Teknik destek görevi"""
    return Task(
        description=(
            f"'{product_name}' ürünü için şu teknik sorunu çöz: '{user_query}'\n\n"
            "YAKLAŞIM:\n"
            "1. Sorunu analiz et ve olası nedenleri belirle\n"
            "2. Adım adım çözüm önerileri sun\n"
            "3. Güvenlik uyarılarını dahil et\n"
            "4. Profesyonel servis gerekliliğini değerlendir\n\n"
            "ODAK: Kullanıcının sorunu güvenli ve etkili şekilde çözmesi."
        ),
        expected_output="Teknik sorun analizi ve çözüm önerileri",
        agent=technical_agent
    )

def create_product_search_task(user_query: str, product_agent) -> Task:
    """Ürün arama görevi"""
    return Task(
        description=(
            f"Şu ürün aramasını gerçekleştir: '{user_query}'\n\n"
            "ARAMA STRATEJİSİ:\n"
            "• Akıllı anahtar kelime seçimi yap\n"
            "• Veritabanından en uygun ürünleri bul\n"
            "• Sonuçları kullanıcı dostu şekilde düzenle\n"
            "• Karşılaştırma imkanı sun\n\n"
            "HEDEF: Kullanıcının ihtiyacına en uygun ürün seçeneklerini sun."
        ),
        expected_output="Ürün arama sonuçları ve öneriler",
        agent=product_agent
    )
