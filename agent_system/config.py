"""
Vestel Agent Sistemi için Yapılandırma Dosyası
"""
print("🔧 Loading config...")

import os
from pathlib import Path
from dotenv import load_dotenv

# Proje kök dizinini belirle (bu dosyanın iki üst dizini)
PROJECT_ROOT = Path(__file__).parent.parent
print(f"📁 Project root: {PROJECT_ROOT}")

# .env dosyasını proje kök dizininden yükle
dotenv_path = PROJECT_ROOT / '.env'
print(f"🔐 Loading .env from: {dotenv_path}")
load_dotenv(dotenv_path=dotenv_path)

# --- API Anahtarları ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
print(f"✅ Google API Key loaded: {GOOGLE_API_KEY[:12] if GOOGLE_API_KEY else 'None'}...")

# --- Dosya Yolları ---
DATABASE_PATH = PROJECT_ROOT / "vestel_sessions.db"  # Session veritabanı
PRODUCTS_DATABASE_PATH = PROJECT_ROOT / "vestel_products.db"  # Ana ürün veritabanı
MANUALS_DIR = PROJECT_ROOT / "manuals"
print("📂 Paths configured")

# --- LLM Ayarları ---
GEMINI_MODEL = "gemini/gemini-2.5-flash"

# CrewAI LLM instance - tüm agent'ler için ortak
from crewai import LLM
llm = LLM(
    model="gemini/gemini-2.5-flash",
    api_key=GOOGLE_API_KEY,
    temperature=0.0
)

# LangChain versiyonu da mevcut (ihtiyaç halinde)
from langchain_google_genai import ChatGoogleGenerativeAI
langchain_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=GOOGLE_API_KEY, temperature=0.0)


# --- Memory Sistem Ayarları ---
# CrewAI memory için ayrı bir API key gerekebilir, aynı API key'i kullanmayı dene
MEMORY_API_KEY = GOOGLE_API_KEY  # Aynı API key'i kullan
MEMORY_MODEL = "gemini/gemini-2.5-flash"
print("🧠 Memory system configured")

print("🤖 LLM settings configured")
print("✅ Config loaded successfully!")