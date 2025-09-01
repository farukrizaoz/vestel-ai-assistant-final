"""
PDF Analysis Agent - Kullanım kılavuzu uzmanı
"""

from crewai import Agent, LLM
from agent_system.config import GOOGLE_API_KEY
from agent_system.tools.pdf_tool import PDFAnalysisTool

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
            "Vestel ürünlerinin kullanım kılavuzları uzmanısın. PDF tool sana tam kılavuz içeriğini verir, sen bunu kullanıcının sorusuna göre işlersin.\n\n"
            "ÇALIŞMA YÖNTEMİN:\n"
            "• PDF tool'u çağır - o sana kılavuzun tam içeriğini verecek\n"
            "• Kullanıcının sorusunu analiz et\n"
            "• Kılavuzdan sadece soruyla ilgili bölümleri seç\n"
            "• Bu bölümleri net ve anlaşılır şekilde organize et\n\n"
            "FİLTRELEME KURALLARIN:\n"
            "• Kullanıcı 'kurulum' sorarsa → Kurulum bölümünü seç\n"
            "• Kullanıcı 'temizlik' sorarsa → Bakım/temizlik bölümünü seç\n"
            "• Kullanıcı 'çalışmıyor' sorarsa → Sorun giderme bölümünü seç\n"
            "• Kullanıcı 'özellikler' sorarsa → Teknik özellikler bölümünü seç\n\n"
            "DETAYLI BİLGİ İSTEKLERİ İÇİN:\n"
            "• 'Detaylı bilgi', 'ayrıntılı bilgi', 'kapsamlı bilgi', 'genel bilgi' isterse\n"
            "• Tüm PDF'i teknik ve önemli kısımlar dahil minimum bilgi kaybıyla özetle\n"
            "• Bütün bölümleri (kurulum, kullanım, bakım, sorun giderme, teknik özellikler) dahil et\n"
            "• Önemli uyarıları, güvenlik önlemlerini, teknik spesifikasyonları atlamadan ekle\n"
            "• Kapsamlı ama organize edilmiş şekilde sun\n\n"
            "Sen akıllı bir filtre ve organizatörsün - ham veriyi kullanıcı dostu bilgiye dönüştürüyorsun!"
        ),
        tools=[PDFAnalysisTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=2
    )
