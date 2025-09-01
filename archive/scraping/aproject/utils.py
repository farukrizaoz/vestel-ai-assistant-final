import os, re, json
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from typing import List, Optional
from aproject.config import UA, MANUALS_DIR

def ensure_dir(path: str) -> None:
    """Create directory and any missing parent directories."""
    os.makedirs(path, exist_ok=True)

def sanitize_filename(name: str) -> str:
    name = re.sub(r"[^\w\-.]+", "_", name.strip())
    return name[:120] or "file"

def parse_sitemap_urls(xml_bytes: bytes) -> List[str]:
    # XML parser varsa onu kullan; yoksa regex fallback
    try:
        soup = BeautifulSoup(xml_bytes, "xml")
        urls = [loc.get_text(strip=True) for loc in soup.select("url > loc")]
        if urls:
            return urls
    except Exception:
        pass
    # fallback
    text = xml_bytes.decode("utf-8", errors="ignore")
    return re.findall(r"<loc>\s*(.*?)\s*</loc>", text, flags=re.I)

def http_get(url: str, timeout=30) -> str:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": UA})
    r.raise_for_status()
    return r.text

def find_manual_links_from_html(html: str, base_url: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    cands: List[str] = []

    # <a href="*.pdf">
    for a in soup.find_all("a", href=True):
        href = a["href"]
        txt   = " ".join((a.get_text(" ") or "").split()).lower()
        label = " ".join([(a.get("aria-label") or ""), (a.get("title") or "")]).lower()
        if ".pdf" in href.lower():
            cands.append(urljoin(base_url, href))
        if any(k in txt or k in label for k in ["kullanma", "kullanım", "kılavuz", "kilavuz", "indir", "manual"]):
            if ".pdf" in href.lower():
                cands.append(urljoin(base_url, href))

    # onclick / data-*
    for tag in soup.find_all(True):
        for attr in ["onclick","data-href","data-url","data-file","data-download"]:
            v = tag.get(attr)
            if not v: continue
            for m in re.findall(r"https?://[^\s'\"<>]+\.pdf", str(v), flags=re.I):
                cands.append(m)

    # raw fallback
    for m in re.findall(r"https?://[^\s'\"<>]+\.pdf", html, flags=re.I):
        cands.append(m)

    # uniq + aynı domain zorunlu değil; ama Vestel çoğu https://statics... olur
    seen, out = set(), []
    for u in [urljoin(base_url, u) for u in cands]:
        if u not in seen:
            seen.add(u); out.append(u)
    return out

def download_file(url: str, file_basename: Optional[str]=None, timeout=60) -> str:
    ensure_dir(MANUALS_DIR)
    base = file_basename or os.path.basename(urlparse(url).path) or "manual.pdf"
    if not base.lower().endswith(".pdf"):
        base += ".pdf"
    base = sanitize_filename(base)
    out_path = os.path.abspath(os.path.join(MANUALS_DIR, base))
    with requests.get(url, headers={"User-Agent": UA}, timeout=timeout, stream=True) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(65536):
                if chunk:
                    f.write(chunk)
    return out_path

def extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    if h1:
        t = " ".join(h1.get_text(" ").split()).strip()
        if t: return t
    t = soup.find("title")
    return (" ".join(t.get_text(" ").split()).strip() if t else "Ürün")
