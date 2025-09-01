import os, json, re, time
from typing import Dict, Any, Tuple, Optional, Union
from functools import wraps
from aproject.config import GOOGLE_API_KEY, MODEL
import google.generativeai as genai

# Configure API key
if not GOOGLE_API_KEY:
    # Try environment variable as fallback
    api_key = os.environ.get("GOOGLE_API_KEY", "AIzaSyDmg6APFLNxDmcCMeDJxvW9dWCSTpiqpqU")
    os.environ["GOOGLE_API_KEY"] = api_key
    genai.configure(api_key=api_key)
else:
    genai.configure(api_key=GOOGLE_API_KEY)

def retry_on_error(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry functions on error with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (2 ** attempt))  # Exponential backoff
            raise last_error
        return wrapper
    return decorator

def _extract_first_json(text: str) -> Dict[str, Any]:
    """Extract the first JSON object from text, handling various formats."""
    if not text: 
        return {}
        
    # Try to find JSON in code blocks first
    patterns = [
        r"```json\s*(\{.*?\})\s*```",  # JSON in code block
        r"```\s*(\{.*?\})\s*```",      # JSON in generic code block
        r"(\{[^{]*\"short_desc\"[^}]*\})",  # JSON with expected keys
        r"(\{.*\})",                   # Any JSON object
    ]
    
    for pattern in patterns:
        try:
            m = re.search(pattern, text, flags=re.S|re.M)
            if m:
                return json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
            
    return {}

def _ensure_llm_ready() -> bool:
    """Configure Gemini API and verify it's ready to use."""
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY is not set. Please set it in environment variables.")
        
    genai.configure(api_key=GOOGLE_API_KEY)
    
    try:
        # Test the configuration with a simple prompt
        model = genai.GenerativeModel(MODEL)
        resp = model.generate_content("test")
        return bool(resp and resp.text)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Gemini: {e}")

@retry_on_error(max_retries=3)
def _safe_generate_content(*args, **kwargs) -> str:
    """Safely generate content from Gemini with retries and validation."""
    model = genai.GenerativeModel(MODEL)
    resp = model.generate_content(*args, **kwargs)
    
    if not resp or not resp.text:
        raise ValueError("Empty response from Gemini")
        
    return resp.text.strip()

def summarize_category(title: str, description: str) -> Tuple[str, str]:
    """
    Create a short description and keywords for a category.
    Returns (short_desc, comma-separated-keywords)
    """
    _ensure_llm_ready()
    
    # Prepare input text (combine title and description)
    text = f"""
Başlık: {title}
    
Açıklama: {description}
""".strip()

    if len(text) > 12000:  # Gemini has ~30k token limit
        text = text[:12000]

    prompt = f"""
Vestel ürün kategorisi için özet hazırla. Metne bakarak:

1. En fazla iki cümlelik kısa, doğal bir Türkçe özet yaz.
2. En fazla 8 tane önemli anahtar kelime belirle.

Metin:
\"\"\"{text}\"\"\"

SADECE JSON formatında yanıt ver:
{{
  "short_desc": "iki cümlelik özet",
  "keywords": ["kelime1", "kelime2", "..."]
}}
"""
    
    # Get response with retry
    response_text = _safe_generate_content(prompt)
    
    # Parse response
    result = _extract_first_json(response_text)
    
    # Validate and clean response
    short_desc = (result.get("short_desc") or "").strip()
    keywords = [k.strip() for k in result.get("keywords", []) if k.strip()]
    
    if not short_desc or not keywords:
        raise ValueError("Failed to generate valid summary or keywords")
        
    return short_desc, ",".join(keywords[:8])

def summarize_category_from_text(page_text: str, url: str) -> Dict[str, Any]:
    """
    Generate a summary and keywords from raw category page text.
    """
    _ensure_llm_ready()
    
    text = page_text.strip()
    if len(text) > 12000:
        text = text[:12000]

    prompt = f"""
Vestel ürün kategorisi için özet çıkart. Metinden yararlanarak:

1. En fazla iki cümlelik kısa, doğal bir Türkçe özet yaz.
2. En fazla 8 tane önemli anahtar kelime belirle (ürün/özellik/amaç odaklı).

Sayfa: {url}

Metin:
\"\"\"{text}\"\"\"

SADECE JSON formatında yanıt ver:
{{
  "short_desc": "iki cümlelik özet",
  "keywords": ["kelime1","kelime2","..."]
}}
"""
    # Get response with retry
    response_text = _safe_generate_content(prompt)
    
    # Parse and validate
    result = _extract_first_json(response_text)
    short_desc = (result.get("short_desc") or "").strip()
    keywords = [k.strip() for k in result.get("keywords", []) if k.strip()]
    
    if not short_desc or not keywords:
        raise ValueError("Failed to generate valid summary or keywords")
        
    return {
        "short_desc": short_desc, 
        "keywords": keywords[:8]
    }

@retry_on_error(max_retries=2)
def _upload_and_wait_file(file_path: str, timeout: int = 30) -> Any:
    """Upload a file to Gemini and wait for it to be processed."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    # Upload file
    file_data = genai.upload_file(file_path)
    start_time = time.time()
    
    # Wait for processing with timeout
    while time.time() - start_time < timeout:
        status = genai.get_file(file_data.name)
        if status.state.name == "ACTIVE":
            return file_data
        elif status.state.name == "FAILED":
            raise RuntimeError(f"File processing failed: {status.error}")
        time.sleep(1)
        
    raise TimeoutError(f"File processing timed out after {timeout}s")

def summarize_product_from_pdf(file_path: str, product_name: str, product_url: str) -> Dict[str, Any]:
    """
    Analyze a product manual PDF using Gemini to extract summary, model number and keywords.
    Uploads the actual PDF file for better analysis.
    """
    _ensure_llm_ready()

    try:
        # Upload and process the file
        file_data = _upload_and_wait_file(file_path)
        
        prompt = f"""
Sen bir teknik ürün analisti olarak bu PDF kılavuzunu inceleyeceksin.

GÖREV: {product_name} ürününün kılavuzundan bilgi çıkar.

1. ÖZET (tek paragraf):
Ürünün tipini, kapasitesini ve önemli özelliğini belirt.

2. MODEL:
Kılavuzda geçen model numarasını bul.

3. TEKNİK LİSTE:
Şu kategorilerden 10-15 özellik listele:
- Ürün tipi (fırın/buzdolabı/çamaşır makinesi vb)
- Kapasite bilgileri (litre/kg/watt)
- Boyut bilgileri (cm/mm)
- Enerji bilgileri (A++/watt/volt)
- Teknoloji özellikleri (wifi/no-frost/turbo fan vb)
- Program ve fonksiyonlar

FORMAT:
Yanıtını tam olarak şu şekilde ver:

ÖZET: [tek cümle açıklama]
MODEL: [model numarası]
LİSTE:
- [özellik 1]
- [özellik 2]
- [özellik 3]
- [özellik 4]
- [özellik 5]
- [özellik 6]
- [özellik 7]
- [özellik 8]
- [özellik 9]
- [özellik 10]

UYARI: Listedeki her satır tek bir özellik olmalı. JSON KULLANMA!
"""
        
        # Generate with retry
        response_text = _safe_generate_content([prompt, file_data])
        
        # Parse the structured response
        lines = response_text.strip().split('\n')
        
        short_desc = ""
        model_number = ""
        keywords = []
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith("ÖZET:"):
                short_desc = line.replace("ÖZET:", "").strip()
            elif line.startswith("MODEL:"):
                model_number = line.replace("MODEL:", "").strip()
            elif line.startswith("LİSTE:"):
                current_section = "liste"
            elif line.startswith("- ") and current_section == "liste":
                keyword = line.replace("- ", "").strip()
                if keyword and len(keyword) > 2:
                    keywords.append(keyword)
        
        # Validation
        if not short_desc or len(short_desc) < 15:
            raise ValueError(f"Description too short: '{short_desc}'")
        
        if not keywords or len(keywords) < 5:
            raise ValueError(f"Not enough keywords: {keywords}")
            
        return {
            "short_desc": short_desc,
            "model_number": model_number,
            "keywords": keywords[:15]  # Limit to 15 keywords
        }
        
    except Exception as e:
        print(f"❌ LLM analysis failed for {file_path}: {e}")
        
        # Return placeholder values for problematic PDFs
        fallback_desc = f"{product_name} kullanım kılavuzu"
        fallback_model = product_url.split('-p-')[-1] if '-p-' in product_url else "Unknown"
        fallback_keywords = [
            "Vestel ürünü",
            "Kullanım kılavuzu", 
            "Teknik özellikler",
            "Kurulum bilgileri",
            "Bakım bilgileri"
        ]
        
        return {
            "short_desc": fallback_desc,
            "model_number": fallback_model,
            "keywords": fallback_keywords
        }
        
    finally:
        # Clean up the uploaded file
        try:
            if 'file_data' in locals():
                genai.delete_file(file_data.name)
        except Exception:
            pass  # Best effort cleanup
