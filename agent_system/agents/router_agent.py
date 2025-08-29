"""
Router Agent - Ana koordinatör agent
"""

from crewai import Agent, LLM
from agent_system.config import GOOGLE_API_KEY
from agent_system.tools import ImprovedProductSearchTool

# LLM instance
llm = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=GOOGLE_API_KEY,
    temperature=0.0  # Deterministik sonuçlar için
)

def create_router_agent():
    """Ana router agent'i oluşturur"""
    return Agent(
        role="Vestel Müşteri Hizmetleri Router",
        goal="Kullanıcı sorularını doğru biçimde yanıtla ve gerektiğinde uzman agentlere yönlendir",
        backstory=(
            "Sen Vestel müşteri hizmetleri koordinatörüsün. Görevlerin:\n\n"
            "ÜRÜN ARAMALAR:\n"
            "• Enerji sınıfı, özellik, model aramaları için search tool kullan\n"
            "• Tool sonucu varsa: bulunan ürünleri liste halinde göster\n"
            "• Tool sonucu yoksa: 'Aradığınız kriterlere uygun ürün bulunamadı' de\n\n"
            "MANUEL SORULARI:\n"
            "• Kurulum, kullanım, bağlantı noktası soruları için PDF Agent'a yönlendir\n"
            "• 'Bu konuda uzmanımız size yardımcı olacak...' diyerek devret\n\n"
            "SATIN ALMA:\n"
            "• Fiyat, mağaza, taksit soruları için Quickstart Agent'a yönlendir\n"
            "• 'Satış uzmanımız detayları paylaşacak...' diyerek devret\n\n"
            "ÖNEMLİ: Search tool kullandığında sonucu direkt müşteriye sun!"
        ),
        tools=[ImprovedProductSearchTool()],
        llm=llm,
        verbose=True,
        allow_delegation=True,
        max_iter=3
    )
