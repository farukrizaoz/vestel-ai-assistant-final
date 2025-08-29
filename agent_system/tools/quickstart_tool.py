"""
Quickstart Tool - Hızlı başlangıç rehberi
"""

from crewai.tools import BaseTool

class QuickstartTool(BaseTool):
    name: str = "Hızlı Başlangıç Rehberi"
    description: str = "Ürünler için hızlı kurulum ve kullanım rehberi sağlar"

    def _run(self, product_name: str) -> str:
        """Quickstart guide placeholder"""
        guide = f"""
🚀 {product_name} - HIZLI BAŞLANGIÇ REHBERİ

� İlk Adımlar:
1. Kutu içeriğini kontrol edin
2. Kurulum kılavuzunu okuyun
3. Güvenlik önlemlerine dikkat edin

⚡ Hızlı Kurulum:
1. Cihazı düz bir yüzeye yerleştirin
2. Elektrik bağlantısını yapın
3. İlk çalıştırma ayarlarını yapın

🔧 Temel Kullanım:
- Ana kontrol panelini öğrenin
- Güvenlik özelliklerini aktifleştirin
- İlk kullanım testini yapın

💡 Önemli ipuçları için tam kılavuzu inceleyin.
"""
        return guide
