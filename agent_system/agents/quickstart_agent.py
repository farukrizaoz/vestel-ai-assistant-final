"""
Quickstart Agent - Satın alma rehberi uzmanı
"""

from crewai import Agent, LLM
from agent_system.config import GOOGLE_API_KEY
from agent_system.tools import QuickstartTool

# LLM instance
llm = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=GOOGLE_API_KEY,
    temperature=0.0  # Deterministik sonuçlar için
)

def create_quickstart_agent():
    """Hızlı başlangıç uzmanı agent'i oluşturur"""
    return Agent(
        role="Vestel Kurulum Uzmanı",
        goal="Ürün satın alma, kurulum ve ilk kullanım konularında rehberlik sağlamak",
        backstory=(
            "Vestel ürünlerinin satın alınması, kurulumu ve ilk kullanımı konusunda uzman bir "
            "teknisyensin. Müşterilere satış noktaları, fiyatlar, kurulum süreçleri, garanti "
            "koşulları ve ürünlerin ilk kurulum adımları hakkında detaylı bilgi verirsin."
        ),
        tools=[QuickstartTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2
    )
