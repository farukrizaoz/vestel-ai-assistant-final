"""
PDF Analysis Agent - Kullanım kılavuzu uzmanı
"""

from crewai import Agent, LLM
from agent_system.config import GOOGLE_API_KEY
from agent_system.tools import PDFAnalysisTool

# LLM instance
llm = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=GOOGLE_API_KEY,
    temperature=0.0  # Deterministik sonuçlar için
)

def create_pdf_agent():
    """PDF analiz uzmanı agent'i oluşturur"""
    return Agent(
        role="Vestel Kullanım Kılavuzu Uzmanı",
        goal="Ürün kullanım kılavuzları ve teknik detaylar hakkında yardım sağlamak",
        backstory=(
            "Vestel ürünlerinin kullanım kılavuzları ve teknik detayları konusunda uzman bir danışmansın. "
            "Kullanıcıların ürün kullanımı, sorun giderme, bakım ve teknik özellikler hakkındaki "
            "sorularını yanıtlarsın. Sadece resmi Vestel dokümanlarından bilgi verirsin."
        ),
        tools=[PDFAnalysisTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2
    )
