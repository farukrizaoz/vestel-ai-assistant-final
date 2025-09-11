"""
Basit ve Etkili Ürün Arama Aracı
Agent karar versin, biz sadece ham veri sağlayalım
"""

import sqlite3
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from agent_system.config import PRODUCTS_DATABASE_PATH


class VestelProductSearchToolInput(BaseModel):
    """Input schema for Vestel Product Search Tool"""
    query: str = Field(description="Aranacak ürün veya özellik")


class VestelProductSearchTool(BaseTool):
    name: str = "Vestel Ürün Arama"
    description: str = """
    Vestel ürün veritabanında esnek arama yapar.
    Keywords ve description alanlarından ürün bilgilerini döndürür.
    Agent kendisi hangi ürünlerin uygun olduğuna karar verir.
    """
    args_schema = VestelProductSearchToolInput

    def _run(self, query: str) -> str:
        """Gelişmiş esnek ürün arama"""
        try:
            conn = sqlite3.connect(PRODUCTS_DATABASE_PATH)
            cursor = conn.cursor()
            
            # Arama terimlerini kelimelere ayır ve temizle
            search_terms = [term.strip().lower() for term in query.lower().split() if len(term) > 1]
            
            if not search_terms:
                return f"'{query}' için geçerli arama terimi bulunamadı."
            
            # Create LIKE condition for each word
            conditions = []
            params = []
            
            for term in search_terms:
                term_pattern = f"%{term}%"
                conditions.append("""
                    (LOWER(name) LIKE ? 
                     OR LOWER(model_number) LIKE ?
                     OR LOWER(manual_keywords) LIKE ?
                     OR LOWER(manual_desc) LIKE ?)
                """)
                params.extend([term_pattern, term_pattern, term_pattern, term_pattern])
            
            # Search for products containing all keywords
            sql = f"""
            SELECT model_number, name, manual_keywords, manual_desc, url
            FROM products 
            WHERE {' AND '.join(conditions)}
            LIMIT 50
            """
            
            cursor.execute(sql, params)
            results = cursor.fetchall()
            
            # If no results are found with all keywords, search for products containing at least half of them
            if not results and len(search_terms) > 1:
                half_conditions = conditions[:max(1, len(conditions)//2)]
                # Each condition uses 4 parameters (name, model_number, manual_keywords, manual_desc)
                params_per_condition = 4
                half_params = params[:len(half_conditions) * params_per_condition]
                
                sql = f"""
                SELECT model_number, name, manual_keywords, manual_desc, url
                FROM products 
                WHERE {' AND '.join(half_conditions)}
                LIMIT 50
                """
                
                cursor.execute(sql, half_params)
                results = cursor.fetchall()
            
            conn.close()
            
            if not results:
                return f"'{query}' için hiç ürün bulunamadı."
            
            # Agent'ın karar verebilmesi için tüm bilgileri ver
            output = f"'{query}' arama sonuçları ({len(results)} ürün):\n\n"
            
            for i, (model, name, keywords, desc, url) in enumerate(results, 1):
                output += f"=== ÜRÜN {i} ===\n"
                output += f"Model: {model or 'Belirtilmemiş'}\n"
                output += f"İsim: {name or 'Belirtilmemiş'}\n"
                output += f"URL: {url or 'URL mevcut değil'}\n"
                output += f"Özellikler: {keywords[:300] if keywords else 'Belirtilmemiş'}...\n"
                output += f"Açıklama: {desc or 'Açıklama yok'}\n\n"
            
            output += "Bu ürünler arasından kullanıcının isteğine en uygun olanları seç ve öner."
            output += "\n\n📌 NOT: Fiyat sorgusu için URL'si olan ürünlerde 'Vestel Fiyat ve Stok Sorgulama' tool'unu kullanabilirsin."
            
            return output
            
        except Exception as e:
            return f"Arama hatası: {str(e)}"


# Agent sistemine export et
ImprovedProductSearchTool = VestelProductSearchTool
