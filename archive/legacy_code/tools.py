"""
Tools - Agent'ların kullanacağı araçlar
"""
import sqlite3
import re
from crewai.tools import BaseTool

from agent_system.config import DATABASE_PATH
from agent_system.state_manager import get_conversation_manager

class ProductSearchTool(BaseTool):
    name: str = "Vestel Ürün Arama"
    description: str = "Vestel ürün veritabanında arama yapar. SADECE database'den gelen sonuçları döndürür."

    def _run(self, query: str) -> str:
        """Veritabanında ürün arama"""
        
        print(f"🔍 Arama: '{query}'")
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()
            
            # Kelime normalize
            word_mapping = {
                'televizyon': 'TV',
                'buzdolabı': 'buzdolabı',
                'çamaşır': 'çamaşır',
                'makinesi': 'makinesi'
            }
            
            normalized_query = query.lower()
            for user_word, db_word in word_mapping.items():
                normalized_query = normalized_query.replace(user_word, db_word)
            
            # Güç normalize (800W -> 800 W)
            normalized_query = re.sub(r'(\d+)([wW])', r'\1 \2', normalized_query)
            
            search_terms = normalized_query.split()
            
            if len(search_terms) == 1:
                search_term = f"%{normalized_query}%"
                cursor.execute("""
                    SELECT name, url, manual_keywords, model_number
                    FROM products 
                    WHERE model_number LIKE ? OR name LIKE ? OR manual_keywords LIKE ?
                    ORDER BY 
                        CASE 
                            WHEN model_number LIKE ? THEN 1
                            WHEN name LIKE ? THEN 2
                            ELSE 3
                        END
                    LIMIT 10
                """, (search_term, search_term, search_term, search_term, search_term))
            else:
                where_conditions = []
                params = []
                
                for term in search_terms:
                    term_pattern = f"%{term}%"
                    where_conditions.append("(model_number LIKE ? OR name LIKE ? OR manual_keywords LIKE ?)")
                    params.extend([term_pattern, term_pattern, term_pattern])
                
                where_clause = " AND ".join(where_conditions)
                
                cursor.execute(f"""
                    SELECT name, url, manual_keywords, model_number
                    FROM products 
                    WHERE {where_clause}
                    ORDER BY 
                        CASE 
                            WHEN model_number LIKE ? THEN 1
                            WHEN name LIKE ? THEN 2
                            ELSE 3
                        END
                    LIMIT 10
                """, params + [f"%{search_terms[0]}%", f"%{search_terms[0]}%"])
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return "Belirtilen kriterlere uygun ürün bulunamadı."
            
            # Sonuçları state'e kaydet
            conversation_manager = get_conversation_manager()
            products = []
            formatted_results = []
            
            for row in results:
                product = {
                    'name': row[0],
                    'url': row[1],
                    'model': row[3] if row[3] else 'Belirtilmemiş',
                    'features': row[2] if row[2] else 'Özellik bilgisi yok'
                }
                products.append(product)
                
                product_info = (
                    f"- Ürün: {product['name']}\n"
                    f"  Model: {product['model']}\n"
                    f"  URL: {product['url']}\n"
                    f"  Özellikler: {product['features'][:150]}..."
                )
                formatted_results.append(product_info)
            
            conversation_manager.add_products(products)
            return "\n\n".join(formatted_results)

        except Exception as e:
            return f"Veritabanı hatası: {e}"

class PDFAnalysisTool(BaseTool):
    name: str = "PDF Kılavuz Analizi"
    description: str = "Ürün kullanım kılavuzlarından spesifik sorulara yanıt bulur"

    def _run(self, product_name: str, question: str) -> str:
        """PDF analizi"""
        print(f"📋 PDF Analizi: '{product_name}' - '{question}'")
        
        conversation_manager = get_conversation_manager()
        
        # İlgili ürünü bul
        relevant_product = None
        for product in conversation_manager.current_products:
            if product_name.lower() in product['name'].lower():
                relevant_product = product
                break
        
        if not relevant_product:
            return f"'{product_name}' ürünü bulunamadı. Önce ürün arama yapın."
        
        analysis = f"""
📋 {relevant_product['name']} - Kullanım Kılavuzu

❓ Soru: {question}

📖 Ürün Bilgileri:
{relevant_product['features']}

🔍 Kılavuzdan İlgili Bölümler:
- Kurulum ve İlk Çalıştırma
- Kullanım Talimatları
- Bakım ve Temizlik
- Sorun Giderme
- Teknik Özellikler

💡 Detaylı bilgi için ürün kılavuzunu inceleyebilirsiniz.
"""
        return analysis

class QuickstartTool(BaseTool):
    name: str = "Hızlı Başlangıç Rehberi"
    description: str = "Satın alma sonrası kurulum ve kullanım rehberi oluşturur"

    def _run(self, product_name: str) -> str:
        """Quickstart guide"""
        print(f"🚀 Quickstart: '{product_name}'")
        
        # Önce ürün ara
        if 'buzdolabı' in product_name.lower():
            # Genel buzdolabı kurulum rehberi
            return self._get_general_quickstart('buzdolabı')
        elif 'tv' in product_name.lower() or 'televizyon' in product_name.lower():
            return self._get_general_quickstart('tv')
        elif 'çamaşır' in product_name.lower():
            return self._get_general_quickstart('çamaşır_makinesi')
        elif 'bulaşık' in product_name.lower():
            return self._get_general_quickstart('bulaşık_makinesi')
        else:
            # Conversation manager'dan ara
            conversation_manager = get_conversation_manager()
            
            # Ürünü bul
            relevant_product = None
            for product in conversation_manager.current_products:
                if product_name.lower() in product['name'].lower():
                    relevant_product = product
                    break
            
            if not relevant_product:
                return f"'{product_name}' ürünü bulunamadı. Önce ürün arama yapın."
            
            # Ürün tipi tespit
            product_type = self._detect_product_type(relevant_product['name'])
            
            return self._build_quickstart_guide(relevant_product, product_type)
        
        quickstart = f"""
🚀 {relevant_product['name']} - HIZLI BAŞLANGIÇ

✅ 1. KUTU AÇMA
- Ürünü dikkatli çıkarın
- Aksesuarları kontrol edin  
- Kılavuzu okuyun

✅ 2. KURULUM
{self._get_setup_steps(product_type)}

✅ 3. İLK KULLANIM
{self._get_first_use(product_type)}

✅ 4. İPUÇLARI
{self._get_tips(product_type)}

📞 Destek: 08502224123
🌐 vestel.com.tr
"""
        return quickstart
    
    def _build_quickstart_guide(self, product, product_type):
        """Ürün bilgili quickstart rehberi oluştur"""
        quickstart = f"""
🚀 {product['name']} - HIZLI BAŞLANGIÇ

✅ 1. KUTU AÇMA
- Ürünü dikkatli çıkarın
- Aksesuarları kontrol edin  
- Kılavuzu okuyun

✅ 2. KURULUM
{self._get_setup_steps(product_type)}

✅ 3. İLK KULLANIM
{self._get_first_use(product_type)}

✅ 4. İPUÇLARI
{self._get_tips(product_type)}

📞 Destek: 08502224123
🌐 vestel.com.tr
"""
        return quickstart
    
    def _get_general_quickstart(self, product_category):
        """Genel ürün kategorisi için quickstart rehberi"""
        guides = {
            'buzdolabı': """
🚀 VESTEL BUZDOLABI - HIZLI BAŞLANGIÇ

✅ 1. KUTU AÇMA VE KONTROL
- Ürünü dikkatli şekilde kutudan çıkarın
- Görünür hasar olup olmadığını kontrol edin
- Aksesuarları (raflar, çekmeceler) kontrol edin
- Garanti belgesi ve kullanım kılavuzunu saklayın

✅ 2. YERLEŞTİRME VE KURULUM
- Düz ve sağlam zemine yerleştirin
- Duvara minimum 5cm mesafe bırakın
- Üst kısımda 30cm boşluk olsun
- Ayak vidalarını seviye ayarı için kullanın
- 2-3 saat beklettikten sonra elektriğe bağlayın

✅ 3. İLK ÇALIŞTIRMA
- Sıcaklık ayarını buzdolabı +4°C, dondurucu -18°C yapın
- İlk 4-6 saat boş çalıştırın
- Gıda koymadan önce temizleyin

✅ 4. KULLANIM İPUÇLARI
- Sıcak yemekleri soğuttuktan sonra koyun
- Kapıyı gereksiz açmayın
- Rafları düzenli kullanın
- Ayda bir temizlik yapın

⚠️ DİKKAT EDİLMESİ GEREKENLER:
- İlk çalıştırmada ses çıkarabilir (normal)
- Elektrik kesintisinde 5 dakika bekleyin
- Dondurucu buzunu düzenli temizleyin

📞 Teknik Destek: 08502224123
🌐 www.vestel.com.tr
""",
            'tv': """
🚀 VESTEL SMART TV - HIZLI BAŞLANGIÇ

✅ 1. KUTU AÇMA VE KONTROL
- TV'yi dikkatli çıkarın
- Kumanda, piller, kablolar kontrol edin
- Ayak montajı için vidaları hazırlayın

✅ 2. KURULUM
- TV ayaklarını monte edin
- Duvar askısı için profesyonel yardım alın
- Anteni ve HDMI kablolarını bağlayın
- Elektrik kablosunu takın

✅ 3. İLK AYAR
- Dil seçimi yapın
- Wi-Fi ağına bağlanın
- Kanal tarama yapın
- Smart TV uygulamalarını indirin

✅ 4. KULLANIM İPUÇLARI
- Ekran parlaklığını odaya göre ayarlayın
- Ses seviyesini komşulara saygılı tutun
- Düzenli yazılım güncellemesi yapın

📞 Teknik Destek: 08502224123
🌐 www.vestel.com.tr
""",
            'çamaşır_makinesi': """
🚀 VESTEL ÇAMAŞIR MAKİNESİ - HIZLI BAŞLANGIÇ

✅ 1. KURULUM
- Nakliye vidalarını çıkarın
- Su girişini bağlayın
- Tahliye hortumunu bağlayın
- Seviye ayarını yapın

✅ 2. İLK KULLANIM
- İlk yıkamayı deterjan ile boş yapın
- Deterjan bölümlerini öğrenin
- Su sıcaklığını ayarlayın

✅ 3. KULLANIM İPUÇLARI
- Uygun program seçin
- Aşırı deterjan kullanmayın
- Düzenli temizlik yapın

📞 Teknik Destek: 08502224123
🌐 www.vestel.com.tr
""",
            'bulaşık_makinesi': """
🚀 VESTEL BULAŞIK MAKİNESİ - HIZLI BAŞLANGIÇ

✅ 1. KURULUM
- Su ve elektrik bağlantısı
- Tahliye hortumu bağlantısı
- Test çalıştırması

✅ 2. İLK KULLANIM
- Deterjan ve parlatıcı ekleyin
- Boş çalıştırın
- Program seçimini öğrenin

✅ 3. KULLANIM İPUÇLARI
- Bulaşıkları ön temizleyin
- Düzenli bakım yapın
- Filtreler temizleyin

📞 Teknik Destek: 08502224123
🌐 www.vestel.com.tr
"""
        }
        return guides.get(product_category, "Ürün rehberi bulunamadı.")

    def _detect_product_type(self, name: str) -> str:
        name_lower = name.lower()
        if 'buzdolabı' in name_lower:
            return 'refrigerator'
        elif 'mikrodalga' in name_lower:
            return 'microwave'
        elif 'çamaşır' in name_lower:
            return 'washing_machine'
        elif 'bulaşık' in name_lower:
            return 'dishwasher'
        else:
            return 'general'

    def _get_setup_steps(self, product_type: str) -> str:
        steps = {
            'refrigerator': "- Düz zemine yerleştirin\n- Duvara 5cm mesafe\n- 2-3 saat bekleyin",
            'microwave': "- Tezgaha yerleştirin\n- 15cm boşluk\n- Elektriğe bağlayın",
            'washing_machine': "- Su bağlantısı\n- Seviyeyi ayarlayın\n- Test yapın",
            'dishwasher': "- Su ve elektrik bağlantısı\n- Boş çalıştırın"
        }
        return steps.get(product_type, "- Kılavuzu takip edin")

    def _get_first_use(self, product_type: str) -> str:
        steps = {
            'refrigerator': "- +4°C ayarlayın\n- 4-6 saat boş çalıştırın",
            'microwave': "- Boş bardakla 1dk test\n- Güç ayarlarını öğrenin",
            'washing_machine': "- Deterjan bölümlerini öğrenin\n- İlk yıkama boş",
            'dishwasher': "- Deterjan ekleyin\n- Boş çalıştırın"
        }
        return steps.get(product_type, "- Kılavuzu okuyun")

    def _get_tips(self, product_type: str) -> str:
        tips = {
            'refrigerator': "- Sık kapı açmayın\n- Sıcak yemek koymayın",
            'microwave': "- Metal koymayın\n- Düzenli temizleyin",
            'washing_machine': "- Az deterjan kullanın\n- Kapıyı açık bırakın",
            'dishwasher': "- Filtreyi temizleyin\n- Doğru deterjan"
        }
        return tips.get(product_type, "- Güvenlik önlemleri")

# Tool instances
product_search_tool = ProductSearchTool()
pdf_analysis_tool = PDFAnalysisTool()
quickstart_tool = QuickstartTool()
