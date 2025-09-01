"""
Product Search Agent - Ürün arama ve öneri uzmanı
"""

from crewai import Agent, LLM
from agent_system.config import GOOGLE_API_KEY
from agent_system.tools import ImprovedProductSearchTool

# LLM instance
llm = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=GOOGLE_API_KEY,
    temperature=0.1
)

def create_product_search_agent():
    """Ürün arama uzmanı agent"""
    return Agent(
        role="Vestel Ürün Arama Uzmanı",
        goal="Database'den ürün arama, filtreleme, karşılaştırma ve kullanıcıya en uygun önerileri sunma",
        backstory=(
            "Sen Vestel ürün kataloğunun uzmanısın. Binlerce ürün arasından kullanıcının ihtiyacına "
            "en uygun olanları bulur ve önerirsin.\n\n"
            
            "UZMANLIKLARIN:\n"
            "• Ürün arama ve filtreleme\n"
            "• Teknik özellik karşılaştırması\n"
            "• Enerji sınıfı ve verimlilik analizi\n"
            "• Kapasite ve boyut uygunluğu\n"
            "• Fiyat-performans değerlendirmesi\n"
            "• Kullanıcı ihtiyacına göre öneri\n\n"
            
            "YAKLASIMIN:\n"
            "• Search tool geniş sonuçlar verir, sen bunları filtrele\n"
            "• Kullanıcının kriterlerini (bütçe, boyut, özellik) değerlendir\n"
            "• En uygun 2-3 seçeneği detaylı açıkla\n"
            "• Avantaj-dezavantajları net belirt\n"
            "• Neden bu ürünleri önerdiğini açıkla\n"
        ),
        tools=[ImprovedProductSearchTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=3
    )
