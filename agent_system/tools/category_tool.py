"""
Kategori Arama ve Listeleme Aracı
"""

import sqlite3
from typing import Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from agent_system.config import PRODUCTS_DATABASE_PATH


class VestelCategoryToolInput(BaseModel):
    """Input schema for Vestel Category Tool"""
    category: str = Field(default="list", description="Kategori adı veya 'list' tüm kategoriler için")
    list_products: bool = Field(default=True, description="True ise ürünleri de listele, False ise sadece sayı göster")


class VestelCategoryTool(BaseTool):
    name: str = "Vestel Kategori Arama"
    description: str = """
    Vestel ürün kategorilerini listeler ve yönetir.
    
    ZORUNLU PARAMETRELER:
    - category: string (varsayılan: "list") - Kategori adı veya "list" tüm kategoriler için
    - list_products: boolean (varsayılan: true) - Ürünleri listele mi?
    
    DOĞRU KULLANIM:
    {"category": "list", "list_products": true} - Tüm kategoriler ve ürünler
    {"category": "list", "list_products": false} - Sadece kategori isimleri
    {"category": "Buzdolabı", "list_products": true} - Buzdolabı ürünleri
    {"category": "no frost", "list_products": true} - No frost ürünleri
    
    ⚠️ HER İKİ PARAMETRE DE ZORUNLU!
    """
    args_schema = VestelCategoryToolInput

    def _run(self, category: str = "list", list_products: bool = True) -> str:
        """İki aşamalı kategori arama: önce kategorileri göster, sonra spesifik arama yap"""
        try:
            conn = sqlite3.connect(PRODUCTS_DATABASE_PATH)
            cursor = conn.cursor()
            
            # Tüm ürünleri al ve kategorilere ayır
            sql = "SELECT model_number, name, manual_keywords, manual_desc FROM products"
            cursor.execute(sql)
            results = cursor.fetchall()
            
            # Kategorileri çıkar
            categories = {}
            for model, name, keywords, desc in results:
                if keywords:
                    import re
                    category_match = re.search(r'Ürün [Tt]ipi:\s*([^,\n]+)', keywords)
                    if category_match:
                        cat_name = category_match.group(1).strip()
                        cat_name = ' '.join(cat_name.split())  # Normalize et
                        if cat_name not in categories:
                            categories[cat_name] = []
                        categories[cat_name].append((model, name, keywords, desc))
            
            conn.close()
            
            # Kategori sıralama
            sorted_categories = dict(sorted(categories.items(), key=lambda x: len(x[1]), reverse=True))
            
            if category.lower() == "list":
                # AŞAMA 1: Tüm kategorileri göster (Agent'ın seçim yapması için)
                output = f"🏪 **VESTEL ÜRÜN KATEGORİLERİ** ({len(categories)} kategori, {len(results)} ürün)\n\n"
                
                if list_products:
                    # Kategoriler ve örnek ürünler
                    for i, (cat_name, products) in enumerate(sorted_categories.items(), 1):
                        output += f"{i}. **{cat_name}** ({len(products)} ürün)\n"
                        # İlk 2 ürünü örnek olarak göster
                        for j, (model, name, keywords, desc) in enumerate(products[:2], 1):
                            output += f"   {j}. {model} - {name[:50]}{'...' if len(name) > 50 else ''}\n"
                        if len(products) > 2:
                            output += f"   ... ve {len(products)-2} ürün daha\n"
                        output += "\n"
                else:
                    # Sadece kategori isimleri ve sayıları
                    for i, (cat_name, products) in enumerate(sorted_categories.items(), 1):
                        output += f"{i}. {cat_name}: {len(products)} ürün\n"
                
                output += f"\n💡 **Spesifik kategori için aracı tekrar çağır:**\n"
                output += f"Örnek: category='Buzdolabı', category='Çamaşır Makinesi' vs.\n"
                output += f"Özellik araması: category='no frost', category='wifi' vs."
                
                return output
            
            else:
                # AŞAMA 2: Spesifik kategori/özellik araması
                found_products = []
                search_term = category.lower()
                matched_category = None
                
                # Önce tam kategori adında ara
                for cat_name, products in categories.items():
                    if search_term in cat_name.lower():
                        found_products.extend(products)
                        matched_category = cat_name
                        break
                
                # Bulamazsa özellik/açıklamada ara
                if not found_products:
                    feature_matches = {}
                    for cat_name, products in categories.items():
                        for model, name, keywords, desc in products:
                            # Ürün adında, özelliklerinde veya açıklamasında ara
                            if (keywords and search_term in keywords.lower()) or \
                               (name and search_term in name.lower()) or \
                               (desc and search_term in desc.lower()):
                                if cat_name not in feature_matches:
                                    feature_matches[cat_name] = []
                                feature_matches[cat_name].append((model, name, keywords, desc))
                    
                    if feature_matches:
                        # Özellik eşleşmelerini birleştir
                        for cat_name, products in feature_matches.items():
                            found_products.extend(products)
                        matched_category = f"{search_term} özellikli ürünler"
                
                if not found_products:
                    # Benzer kategorileri öner
                    similar_cats = []
                    for cat_name in categories.keys():
                        if any(word in cat_name.lower() for word in search_term.split()):
                            similar_cats.append(cat_name)
                    
                    output = f"❌ '{category}' bulunamadı.\n\n"
                    if similar_cats:
                        output += f"🔍 **Benzer kategoriler:**\n"
                        for cat in similar_cats[:5]:
                            output += f"• {cat} ({len(categories[cat])} ürün)\n"
                        output += f"\n💡 Bu kategorilerden birini dene!"
                    else:
                        output += f"📋 **Mevcut kategoriler:**\n"
                        for cat in list(categories.keys())[:10]:
                            output += f"• {cat}\n"
                        output += f"... ve {len(categories)-10} kategori daha"
                    
                    return output
                
                if list_products:
                    # Bulunan ürünleri detaylı listele
                    output = f"🎯 **{matched_category.upper()}** ({len(found_products)} ürün bulundu)\n\n"
                    
                    for i, (model, name, keywords, desc) in enumerate(found_products, 1):
                        output += f"{i}. **{model}** - {name}\n"
                        if keywords:
                            # Önemli özellikleri çıkar
                            features = keywords[:150] + "..." if len(keywords) > 150 else keywords
                            output += f"   🔧 {features}\n"
                        output += "\n"
                    
                    return output
                else:
                    # Sadece özet bilgi
                    return f"✅ **{matched_category}** kategorisinde {len(found_products)} ürün bulundu."
        
        except Exception as e:
            return f"❌ Kategori arama hatası: {str(e)}"


# Agent sistemine export et
VestelCategorySearchTool = VestelCategoryTool
