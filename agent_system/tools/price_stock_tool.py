"""
Vestel Product Price and Stock Tool - Gerçek zamanlı fiyat ve stok bilgisi
"""

import json
import re
from typing import Tuple, Optional
import requests
from bs4 import BeautifulSoup
from crewai.tools import BaseTool


class VestelPriceStockTool(BaseTool):
    """Vestel ürünlerinin güncel fiyat ve stok bilgisini alan tool"""
    
    name: str = "Vestel Fiyat ve Stok Sorgulama"
    description: str = (
        "Vestel.com.tr'den ürün fiyatı ve stok durumunu sorgular. "
        "Kullanıcı fiyat sorarsa veya 'kaç para', 'fiyat', 'stok' kelimelerini kullanırsa bu tool'u çağır. "
        "Input: Vestel ürün URL'i (https://vestel.com.tr/... formatında)"
    )
    
    def _run(self, product_url: str) -> str:
        """
        Vestel ürün sayfasından fiyat ve stok bilgisi çeker
        
        Args:
            product_url: Vestel ürün URL'i
            
        Returns:
            Fiyat ve stok bilgisi string formatında
        """
        try:
            # URL doğrulaması
            if not (product_url.startswith("https://vestel.com.tr/") or product_url.startswith("https://www.vestel.com.tr/")):
                return "❌ Hata: Sadece vestel.com.tr URL'leri desteklenmektedir."
            
            price_info = self._get_product_info(product_url)
            normal_price = price_info["normal_price"]
            member_price = price_info.get("member_price")
            in_stock = price_info["in_stock"]
            
            # Formatlanmış sonuç
            normal_price_formatted = f"{normal_price:,} TL".replace(",", ".")
            stock_status = "✅ Stokta var" if in_stock else "❌ Stokta yok"
            
            result = f"""
📊 **Güncel Fiyat ve Stok Bilgisi:**

💰 **Normal Fiyat:** {normal_price_formatted}"""
            
            if member_price and member_price != normal_price:
                member_price_formatted = f"{member_price:,} TL".replace(",", ".")
                savings = normal_price - member_price
                savings_formatted = f"{savings:,} TL".replace(",", ".")
                result += f"""
🎯 **Vestel Üyelerine Özel:** {member_price_formatted}
💸 **Tasarruf:** {savings_formatted}"""
            
            result += f"""
📦 **Stok:** {stock_status}

ℹ️ *Bu bilgiler vestel.com.tr'den gerçek zamanlı alınmıştır.*
⚠️ *Fiyat ve stok durumu değişebilir. Satın alma öncesi kontrol ediniz.*"""
            
            return result
            
        except requests.RequestException as e:
            return f"❌ İnternet bağlantısı hatası: {str(e)}"
        except ValueError as e:
            return f"❌ Ürün bilgisi alınamadı: {str(e)}"
        except Exception as e:
            return f"❌ Beklenmeyen hata: {str(e)}"
    
    def _get_product_info(self, url: str) -> dict:
        """Fetch product price and stock availability from a Vestel product page."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
            )
        }
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        
        # İlk önce JSON-LD'yi deneyelim
        script_tag = soup.find("script", type="application/ld+json")
        if script_tag:
            try:
                data = json.loads(script_tag.string)
                offers = data.get("offers", {})
                price_raw = offers.get("price", "")
                if price_raw:
                    match = re.search(r"[\d.,]+", price_raw)
                    if match:
                        price_numeric = int(match.group(0).replace(".", "").replace(",", ""))
                        availability = offers.get("availability", "")
                        in_stock = availability.endswith("InStock")
                        return {
                            "normal_price": price_numeric,
                            "member_price": None,
                            "in_stock": in_stock
                        }
            except (json.JSONDecodeError, ValueError):
                pass

        # JSON-LD yoksa, price class'larını arayayım
        price_elements = soup.find_all(class_=lambda x: x and ('price' in x.lower() or 'fiyat' in x.lower()))
        
        normal_price = None
        member_price = None
        
        for price_elem in price_elements:
            if price_elem and price_elem.get_text():
                price_text = price_elem.get_text().strip()
                # TL içeren ve sayı içeren metni ara
                if 'TL' in price_text:
                    # Tüm fiyatları bul
                    matches = re.findall(r'([\d.,]+)\s*TL', price_text)
                    if matches:
                        prices = []
                        for match in matches:
                            try:
                                price_num = int(match.replace(".", "").replace(",", ""))
                                prices.append(price_num)
                            except ValueError:
                                continue
                        
                        if prices:
                            # Eğer "Üyelerine Özel" metni varsa bu üye fiyatı
                            if 'üyelerine özel' in price_text.lower() or 'üye' in price_text.lower():
                                if len(prices) >= 2:
                                    normal_price = max(prices)  # Yüksek fiyat normal fiyat
                                    member_price = min(prices)  # Düşük fiyat üye fiyatı
                                else:
                                    member_price = prices[0]
                            else:
                                # Normal fiyat elementi
                                if normal_price is None:
                                    normal_price = prices[0]
        
        if normal_price is None and member_price is None:
            raise ValueError("Fiyat bilgisi bulunamadı")
        
        # Eğer sadece üye fiyatı varsa, onu normal fiyat olarak ata
        if normal_price is None:
            normal_price = member_price
            member_price = None
        
        # Stok durumu için sayfa içinde ara
        page_text = soup.get_text().lower()
        in_stock = not any(term in page_text for term in ['stokta yok', 'tükendi', 'satışta değil'])
        
        return {
            "normal_price": normal_price,
            "member_price": member_price,
            "in_stock": in_stock
        }
