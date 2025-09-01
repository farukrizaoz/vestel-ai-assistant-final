import os

# Database
DB_PATH = os.environ.get("APROJECT_DB", os.path.abspath("./vestel_products.db"))

# Download paths
MANUALS_DIR = os.path.abspath(os.environ.get("APROJECT_MANUALS", "./manuals"))

# Google Generative AI settings
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "AIzaSyDmg6APFLNxDmcCMeDJxvW9dWCSTpiqpqU")
MODEL = os.environ.get("APROJECT_LLM", "gemini-2.5-flash")

# Vestel sitemaps
SITEMAP_CATEGORY = "https://statics.vestel.com.tr/vstlsitemap/category.xml"
SITEMAP_PRODUCT = "https://statics.vestel.com.tr/vstlsitemap/product.xml"

# HTTP settings
# Rotate between different user agents to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
]
UA = USER_AGENTS[0]  # Default UA
REQUEST_TIMEOUT = 60  # seconds
CHUNK_SIZE = 65536   # bytes, for file downloads

# PDF filtering
MANUAL_KEYWORDS = [
    "kullanım", "kullanma", "kılavuz", "kilavuz",
    "user manual", "manual", "instruction", "guide"
]

EXCLUDED_KEYWORDS = [
    "cookie", "cerez", "privacy", "kvkk", 
    "garanti", "warranty", "kampanya",
    "catalog", "katalog", "brosur", "broşür", 
    "bulten", "bülten"
]

