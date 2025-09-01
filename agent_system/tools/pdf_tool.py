"""
PDF Analysis Tool - Basit PDF okuma
"""

import os
from pathlib import Path
import PyPDF2
from crewai.tools import BaseTool

# Proje kök dizinini doğrudan belirle
PROJECT_ROOT = Path(__file__).parent.parent.parent

class PDFAnalysisTool(BaseTool):
    name: str = "PDF Kılavuz Analizi"
    description: str = "Belirtilen ürünün PDF kılavuzunu okur ve tam içeriğini döndürür"

    def _run(self, product_name: str) -> str:
        """PDF dosyasını bulup tam içeriğini okur"""
        
        manuals_path = os.path.join(PROJECT_ROOT, "manuals")
        
        if not os.path.exists(manuals_path):
            return f"Manuals klasörü bulunamadı: {manuals_path}"
        
        # PDF dosyasını bul - daha gelişmiş arama
        files = os.listdir(manuals_path)
        pdf_files = [f for f in files if f.endswith('.pdf')]
        
        matching_pdf = None
        
        # Önce tam ürün adıyla ara
        for pdf_file in pdf_files:
            if product_name.lower() in pdf_file.lower():
                matching_pdf = pdf_file
                break
        
        # Eğer bulamazsa, model numarasını çıkar ve ara
        if not matching_pdf:
            # Model numarasını çıkar (örn: "Vestel 40FA9740 40'' ..." -> "40fa9740")
            import re
            model_match = re.search(r'(\w+\d+\w*)', product_name)
            if model_match:
                model_number = model_match.group(1).lower()
                for pdf_file in pdf_files:
                    if model_number in pdf_file.lower():
                        matching_pdf = pdf_file
                        break
        
        # Son çare: ürün adındaki anahtar kelimeleri ara
        if not matching_pdf:
            keywords = product_name.lower().split()
            for pdf_file in pdf_files:
                pdf_lower = pdf_file.lower()
                match_count = sum(1 for keyword in keywords if keyword in pdf_lower)
                if match_count >= 2:  # En az 2 kelime eşleşmesi
                    matching_pdf = pdf_file
                    break
        
        if not matching_pdf:
            return f"'{product_name}' için PDF bulunamadı. Mevcut PDF'ler: {pdf_files[:5]}"
        
        # PDF'i oku
        pdf_path = os.path.join(manuals_path, matching_pdf)
        
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                full_text = ""
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                
                if full_text.strip():
                    return f"PDF bulundu: {matching_pdf}\n\nİçerik:\n{full_text}"
                else:
                    return f"PDF bulundu ({matching_pdf}) ancak metin çıkarılamadı."
                
        except Exception as e:
            return f"PDF okuma hatası: {e}"

# Export için alias oluştur
__all__ = ['PDFAnalysisTool']
