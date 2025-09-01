# aproject/pdf_reader.py
import os, re, logging
from typing import List
from urllib.parse import urljoin, urlparse
import requests

from bs4 import BeautifulSoup

for name in ("pdfminer","pdfplumber","PyPDF2"):
    try: logging.getLogger(name).setLevel(logging.ERROR)
    except: pass

try:
    import pdfplumber
except Exception:
    pdfplumber = None

try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None

from .config import UA, MANUALS_DIR
from .utils import ensure_dir

# Use UA directly from config

def _sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\-.]+", "_", name.strip())
    return name[:200] or "manual"

def _ensure_manuals_dir():
    """Create the manuals directory if it doesn't exist."""
    ensure_dir(MANUALS_DIR)

def get_html(url: str, timeout_sec: int) -> str:
    r = requests.get(url, headers={"User-Agent": UA}, timeout=timeout_sec)
    r.raise_for_status()
    return r.text

def find_vestel_manual_links(product_url: str, timeout_sec: int) -> List[str]:
    """
    Vestel PDP sayfasından PDF linklerini çıkar (kullanım kılavuzu vb)
    """
    html = get_html(product_url, timeout_sec)
    soup = BeautifulSoup(html, "html.parser")
    base = product_url
    candidates: List[str] = []

    # 1) direct <a href="*.pdf">
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = " ".join((a.get_text(" ") or "").split()).lower()
        label = " ".join([(a.get("aria-label") or ""), (a.get("title") or "")]).lower()
        if ".pdf" in href.lower():
            candidates.append(urljoin(base, href))
        if any(k in text or k in label for k in ["kullanma", "kullanım", "kılavuz", "kilavuz", "indir", "user manual", "manual"]):
            if ".pdf" in href.lower():
                candidates.append(urljoin(base, href))

    # 2) onclick / data-* with .pdf
    for tag in soup.find_all(True):
        for attr in ["onclick", "data-href", "data-url", "data-file", "data-download"]:
            val = tag.get(attr)
            if not val:
                continue
            for m in re.findall(r"https?://[^\s'\"<>]+\.pdf", str(val), flags=re.I):
                candidates.append(m)

    # 3) raw HTML fallback
    for m in re.findall(r"https?://[^\s'\"<>]+\.pdf", html, flags=re.I):
        candidates.append(m)

    # Normalize & dedupe
    normalized = [urljoin(base, u) for u in candidates]
    seen, ordered = set(), []
    for u in normalized:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered

def download_file(url: str, file_basename: str, timeout_sec: int) -> str:
    """
    PDF'i ./manuals/<file_basename>.pdf olarak indir ve dosya yolunu döndür.
    """
    _ensure_manuals_dir()
    base = _sanitize_filename(file_basename or os.path.basename(urlparse(url).path) or "manual")
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    out_path = os.path.abspath(os.path.join(MANUALS_DIR, base))
    with requests.get(url, headers={"User-Agent": UA}, timeout=timeout_sec, stream=True) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
    return out_path

def extract_pdf_text(file_path: str) -> str:
    """
    PDF'ten metin çıkar (LLM'e göndermek için).
    """
    if not os.path.exists(file_path):
        return ""
    text = ""

    if pdfplumber:
        try:
            with pdfplumber.open(file_path) as pdf:
                parts = []
                for page in pdf.pages:
                    t = page.extract_text() or ""
                    if t.strip():
                        parts.append(t)
                text = "\n".join(parts).strip()
        except Exception:
            text = text or ""

    if not text and PdfReader:
        try:
            reader = PdfReader(file_path)
            parts = []
            for p in reader.pages:
                t = p.extract_text() or ""
                if t.strip():
                    parts.append(t)
            text = "\n".join(parts).strip()
        except Exception:
            text = text or ""

    return text
