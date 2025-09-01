import argparse
import os
import re
from typing import List, Dict, Optional
import json
import urllib.parse
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import requests
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from aproject.config import (
    USER_AGENTS, MANUALS_DIR, SITEMAP_PRODUCT, SITEMAP_CATEGORY,
    REQUEST_TIMEOUT, CHUNK_SIZE, MANUAL_KEYWORDS, EXCLUDED_KEYWORDS
)
from aproject.db import (
    init_schema, upsert_product_basic, mark_manual,
    get_product_by_url, upsert_category, get_category_by_url,
    mark_category_summarized, update_manual_analysis
)
from aproject.utils import (
    ensure_dir, sanitize_filename,
    download_file, find_manual_links_from_html, extract_title
)

def _create_robust_session() -> requests.Session:
    """Create a session with retry strategy and connection pooling."""
    session = requests.Session()
    
    # Retry strategy
    retry_strategy = Retry(
        total=5,  # Total number of retries
        status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry
        backoff_factor=2,  # Wait time multiplier between retries
        raise_on_status=False  # Don't raise exception on final failure
    )
    
    # Mount adapter with retry strategy
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=20
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# Global session for connection reuse
_session = _create_robust_session()

def _get_random_user_agent() -> str:
    """Get a random user agent to avoid detection."""
    return random.choice(USER_AGENTS)

def _fetch(url: str, timeout: int = 30, method: str = "GET", allow_redirects: bool = True, max_retries: int = 3) -> requests.Response:
    """Fetch URL with robust retry mechanism for DNS and connection issues."""
    print(f"🔍 Fetching: {url}")  # DEBUG
    headers = {
        "User-Agent": _get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    for attempt in range(max_retries):
        try:
            # Add progressive delay between attempts 
            if attempt > 0:
                delay = random.uniform(2, 5) * (attempt + 1)
                print(f"    Retry {attempt}/{max_retries} after {delay:.1f}s delay...")
                time.sleep(delay)
            
            # Add small random delay before each request to avoid rate limiting
            time.sleep(random.uniform(0.3, 1.0))
            
            # Use simple requests
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=allow_redirects
            )
            
            # Check for rate limiting or ban
            if response.status_code == 429:  # Too Many Requests
                print(f"    Rate limited (429), waiting longer...")
                time.sleep(60)  # Wait 1 minute for rate limit
                continue
            elif response.status_code == 403:  # Forbidden - possible ban
                print(f"    Access forbidden (403) - possible IP ban")
                time.sleep(120)  # Wait 2 minutes for ban
                continue
            elif response.status_code in [200, 404]:
                return response
            else:
                print(f"    HTTP {response.status_code} on attempt {attempt + 1}")
                
        except requests.exceptions.ConnectionError as e:
            error_msg = str(e)
            print(f"    Connection error on attempt {attempt + 1}: {error_msg}")
            if attempt == max_retries - 1:
                raise  # Re-raise on final attempt
                
        except requests.exceptions.Timeout as e:
            print(f"    Timeout on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
                
        except requests.exceptions.RequestException as e:
            print(f"    Request error on attempt {attempt + 1}: {e}")
            if attempt == max_retries - 1:
                raise
    
    # Should not reach here, but just in case
    raise requests.exceptions.RequestException(f"Failed after {max_retries} attempts")

def parse_product_sitemap(url: str) -> List[str]:
    r = _fetch(url, timeout=40)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    out = []
    for u in root.findall(".//sm:url", ns):
        loc = u.find("sm:loc", ns)
        if loc is not None and loc.text:
            out.append(loc.text.strip())
    return out

def _norm_space(s: Optional[str]) -> str:
    if not s: return ""
    return re.sub(r"\s+", " ", s).strip()

def _sanitize_filename(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s.strip("_")[:200] or "manual"

def _best_manual_candidate(links: List[str]) -> Optional[str]:
    """Find the best manual PDF from a list of PDF URLs using smart scoring."""
    if not links:
        return None

    def score(url: str) -> int:
        url_lower = url.lower()
        parts = urlparse(url)
        filename = os.path.basename(parts.path).lower()
        
        # Immediate disqualifiers
        if not url_lower.endswith('.pdf'):
            return -100
        if any(x in url_lower for x in EXCLUDED_KEYWORDS):
            return -50
        
        pts = 0
        
        # Very strong manual indicators in filename
        if re.search(r"(kullan(i|ı)m|manual|instruction|guide).*\d+", filename):
            pts += 20  # Has manual keyword + numbers (likely model number)
        elif re.search(r"k(i|ı)lavuz.*\d+", filename):
            pts += 20  # Turkish manual name + numbers
            
        # Strong manual indicators
        if re.search(r"(^|\W)(kullan(i|ı)m|manual|instruction)(\W|$)", filename):
            pts += 15  # Manual word as whole word
        if re.search(r"(^|\W)(k(i|ı)lavuz)(\W|$)", filename):
            pts += 15  # Turkish manual word
            
        # Moderate indicators
        for kw in MANUAL_KEYWORDS:
            if kw in url_lower:
                pts += 5  # General manual keywords anywhere
        
        # Weak positive indicators
        if re.search(r"\d{4,}", url_lower):
            pts += 3  # Has 4+ digit number (likely product code)
        if "statics" in parts.netloc:
            pts += 2  # Vestel static content domain
            
        # URL format scoring
        pts += max(0, 60 - len(filename)) // 10  # Shorter filenames preferred
        if url.count("/") <= 6:
            pts += 2  # Simpler paths preferred
            
        return pts

    candidates = [(url, score(url)) for url in links]
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    best = candidates[0] if candidates else (None, -1)
    
    # Only return if it's a PDF and has a positive score
    if best[1] > 0 and best[0].lower().endswith('.pdf'):
        return best[0]
        
    return None

def _extract_url_from_js(js_text: str) -> Optional[str]:
    """Extract PDF URL from JavaScript content"""
    if not js_text:
        return None
        
    # Look for PDF URL in various formats
    patterns = [
        r'window\.open\([\'"]([^\'"\s]+\.pdf)[\'"]',
        r'location\.href\s*=\s*[\'"]([^\'"\s]+\.pdf)[\'"]',
        r'href:\s*[\'"]([^\'"\s]+\.pdf)[\'"]',
        r'url:\s*[\'"]([^\'"\s]+\.pdf)[\'"]',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, js_text, re.I)
        if match:
            return match.group(1)
    return None

def find_vestel_manual_links(product_url: str, html: Optional[str] = None) -> List[str]:
    """Find user manual PDF links from a Vestel product page."""
    if html is None:
        r = _fetch(product_url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        html = r.text

    soup = BeautifulSoup(html, "html.parser")
    base_url = product_url
    candidates = []
    
    # Look for manual buttons/links
    manual_texts = ["kullanım kılavuzu", "kullanma kılavuzu", "user manual", "manual"]
    
    # Try to find manual download section
    manual_section = None
    for section in soup.find_all(["div", "section"]):
        text = " ".join((section.get_text(" ") or "").split()).lower()
        if "dökümanlar" in text or "belgeler" in text or "kılavuzlar" in text:
            manual_section = section
            break
    
    # 1) Check buttons and links with manual-related text
    elements = []
    if manual_section:
        elements.extend(manual_section.find_all(["a", "button", "div", "span"]))
    elements.extend(soup.find_all(["a", "button"]))
    
    for elem in elements:
        text = " ".join((elem.get_text(" ") or "").split()).lower()
        if any(mt in text for mt in manual_texts):
            # Check for data attributes that might contain the PDF URL
            for attr in ["href", "data-href", "data-url", "data-file", "onclick", "data-download", "data-document"]:
                val = elem.get(attr, "")
                if not val:
                    continue
                    
                # 1. Direct PDF URLs
                if val.lower().endswith('.pdf'):
                    candidates.append(val)
                    continue
                
                # 2. JavaScript handlers
                if attr == "onclick" or attr.startswith("data-"):
                    # Try to extract PDF URL from JavaScript
                    pdf_url = _extract_url_from_js(val)
                    if pdf_url:
                        candidates.append(pdf_url)
                        continue
                        
                    # Look for function calls that might load the PDF
                    if any(x in val.lower() for x in ["manual", "kilavuz", "kılavuz", "download", "indir"]):
                        # This might be an AJAX call, try to follow it
                        ajax_url = None
                        # Look for API endpoint
                        api_match = re.search(r'["\']([^"\']+/api/[^"\']+)["\']', val)
                        if api_match:
                            ajax_url = api_match.group(1)
                        # Look for document ID
                        doc_match = re.search(r'["\']?docId["\']?\s*[:=]\s*["\']?(\d+)["\']?', val)
                        if doc_match:
                            ajax_url = f"https://www.vestel.com.tr/api/document/{doc_match.group(1)}"
                            
                        if ajax_url:
                            try:
                                # Try to get the actual PDF URL
                                ajax_url = urljoin(product_url, ajax_url)
                                r = _fetch(ajax_url, timeout=20)
                                r.raise_for_status()
                                # Parse JSON response
                                data = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
                                # Look for PDF URL in response
                                if isinstance(data, dict):
                                    for key in ['url', 'fileUrl', 'downloadUrl', 'path']:
                                        if key in data and isinstance(data[key], str) and data[key].lower().endswith('.pdf'):
                                            candidates.append(data[key])
                                            break
                            except Exception:
                                pass  # Failed to get PDF URL from AJAX call

    # 2) Look for elements with manual-related classes or IDs
    manual_elements = soup.find_all(class_=lambda x: x and any(word in x.lower() for word in ["manual", "kilavuz", "kılavuz"]))
    for elem in manual_elements:
        for link in elem.find_all("a", href=True):
            href = link["href"]
            if href.lower().endswith(".pdf"):
                candidates.append(href)
            
    # 3) Search for PDF links in script tags (might contain manual URLs)
    for script in soup.find_all("script"):
        if script.string:
            pdf_urls = re.findall(r"https?://[^\s'\"<>]+\.pdf", script.string, re.I)
            candidates.extend(url for url in pdf_urls if "manual" in url.lower() or "kilavuz" in url.lower())

    # 4) Special handling for statik.vestel.com.tr URLs
    # Try to find product code in the HTML first
    product_codes = set()
    
    # Look for product code in meta tags
    for meta in soup.find_all("meta", {"property": ["og:image", "og:url"]}):
        content = meta.get("content", "")
        if "webfiles" in content:
            code = re.search(r"/(\d{8})_", content)
            if code:
                product_codes.add(code.group(1))
    
    # Look for product code in script tags
    for script in soup.find_all("script"):
        if script.string:
            # Look for productId or similar variables
            codes = re.findall(r'["\']?productId["\']?\s*[:=]\s*["\']?(\d{8})["\']?', script.string)
            product_codes.update(codes)
            # Look for webfiles URLs
            codes = re.findall(r'webfiles/(\d{8})_', script.string)
            product_codes.update(codes)
    
    # Also try the URL pattern as fallback
    model_code = re.search(r"p-(\d+)", product_url)
    if model_code:
        product_codes.add(model_code.group(1))
        
    # 5) Handle language-specific PDFs
    langs = ["k", "m", "tr", "en"]  # Turkish and English variants
    patterns = [
        "webfiles/{code}_{lang}.pdf",  # Standard pattern
        "webfiles/{code}/{lang}.pdf",  # Subfolder pattern
        "webfiles/{lang}/{code}.pdf",  # Language folder pattern
        "{code}_{lang}.pdf",          # Simple pattern
        "{code}/{lang}.pdf"           # Another subfolder pattern
    ]

    # Try various product code formats
    code_formats = set()
    for code in product_codes:
        code_formats.add(code)
        # Add leading zeros if needed
        code_formats.add(code.zfill(8))
        # Try with and without year prefix
        if len(code) >= 6:
            code_formats.add("2023" + code[-4:])
            code_formats.add("2024" + code[-4:])

    # Try all combinations
    for code in code_formats:
        for pattern in patterns:
            for lang in langs:
                url = f"https://statik.vestel.com.tr/" + pattern.format(code=code, lang=lang)
                candidates.append(url)

    # Normalize & dedupe URLs
    normalized = [urljoin(base_url, u) for u in candidates]
    seen, ordered = set(), []
    for u in normalized:
        if u not in seen and u.lower().endswith(".pdf"):
            seen.add(u)
            # Verify the PDF exists and is accessible with retry
            try:
                # Try HEAD first for quick check
                r = _session.head(u, headers={"User-Agent": _get_random_user_agent()}, timeout=10)
                if r.status_code == 200 and "pdf" in r.headers.get("content-type", "").lower():
                    ordered.append(u)
                    continue
                    
                # If HEAD fails, try GET with Range to check file type
                r = _session.get(u, headers={
                    "User-Agent": _get_random_user_agent(),
                    "Range": "bytes=0-1024"  # Get first KB only
                }, timeout=10)
                if r.status_code in (200, 206) and (
                    "pdf" in r.headers.get("content-type", "").lower() or
                    r.content.startswith(b"%PDF")
                ):
                    ordered.append(u)
            except Exception:
                # Don't fail completely, just skip this URL
                continue
    
    return ordered


def download_manual_pdf(manual_url: str, product_url: str) -> str:
    """Save manual as ./manuals/<product_slug>__<pdf_name>.pdf and return absolute path."""
    # Generate safe filename: product_slug + pdf_name
    p = urlparse(product_url)
    slug = sanitize_filename(os.path.basename(p.path) or "product")
    pdf_name = sanitize_filename(os.path.basename(urlparse(manual_url).path) or "manual") + ".pdf"
    file_basename = f"{slug}__{pdf_name}"
    
    # First check if the PDF exists and looks valid
    try:
        r = _session.head(manual_url, headers={"User-Agent": _get_random_user_agent()}, timeout=15)
        print(f"  ↪ HEAD response: {r.status_code}, Content-Type: {r.headers.get('content-type')}")
        
        if r.status_code != 200:
            print(f"  ↪ manual URL not accessible (status {r.status_code})")
            return None
    except Exception as e:
        print(f"  ↪ Failed to check manual URL: {e}")
        return None
        
    # Download the file
    try:
        from aproject.utils import download_file
        pdf_path = download_file(manual_url, file_basename=file_basename, timeout=REQUEST_TIMEOUT)
        
        # Log file size
        size_kb = os.path.getsize(pdf_path) / 1024
        print(f"  ↪ downloaded PDF size: {size_kb:.1f} KB")
        
        # Quick size check only (no Gemini validation for speed)
        if size_kb < 20:
            print("  ↪ PDF too small (< 20KB)")
            os.remove(pdf_path)
            return None
            
        return pdf_path
        
    except Exception as e:
        print(f"  ↪ Failed to download PDF: {e}")
        return None

# ---------- product runner ----------
def run_products(limit: int, skip_done: bool, verbose: bool):
    init_schema()

    # 1) sitemap ürün URL'lerini çek
    try:
        urls = parse_product_sitemap(SITEMAP_PRODUCT)
    except Exception as e:
        print(f"❌ Failed to fetch product sitemap: {e}")
        return
        
    if limit and limit > 0:
        urls = urls[:limit]

    done = 0
    failed = 0
    dns_failures = 0
    
    for i, url in enumerate(urls, 1):
        try:
            if verbose:
                print(f"[PROD {i}/{len(urls)}] {url}")

            # daha önce yapıldıysa atla
            row = get_product_by_url(url)
            if skip_done and row and row.get("manual_done") == 1:
                if verbose:
                    print("  ↪ skipped (manual_done=1)")
                continue

            # ürün sayfası - with robust retry
            try:
                r = _fetch(url, timeout=40, max_retries=3)
                r.raise_for_status()
                html = r.text
            except requests.exceptions.ConnectionError as e:
                if "NameResolutionError" in str(e) or "Failed to resolve" in str(e):
                    dns_failures += 1
                    print(f"  ❌ DNS resolution failed for {url}")
                    if dns_failures >= 5:  # Reduced threshold
                        print(f"  ⚠️ Too many DNS failures ({dns_failures}), pausing for 2 minutes...")
                        time.sleep(120)  # Longer pause
                        dns_failures = 0  # Reset counter
                    continue
                else:
                    failed += 1
                    print(f"  ❌ Connection error: {e}")
                    # Check if it might be a ban
                    if "Connection refused" in str(e) or "403" in str(e):
                        print(f"  ⚠️ Possible IP ban detected, pausing for 5 minutes...")
                        time.sleep(300)  # 5 minute pause for potential ban
                    continue
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    print(f"  ❌ 403 Forbidden - IP might be banned, pausing for 10 minutes...")
                    time.sleep(600)  # 10 minutes for 403
                    continue
                elif e.response.status_code == 429:
                    print(f"  ❌ 429 Rate Limited - pausing for 5 minutes...")
                    time.sleep(300)  # 5 minutes for rate limit
                    continue
                else:
                    failed += 1
                    print(f"  ❌ HTTP error: {e}")
                    continue
            except Exception as e:
                failed += 1
                print(f"  ❌ Request failed: {e}")
                continue

            # ürün adı (title/h1)
            soup = BeautifulSoup(html, "html.parser")
            title = _norm_space(soup.find("h1").get_text(" ")) if soup.find("h1") else None
            if not title:
                t = soup.find("title")
                title = _norm_space(t.get_text(" ")) if t else None

            upsert_product_basic(url, name=title)

            # Find manual candidates
            try:
                manual_links = find_vestel_manual_links(url, html)
            except Exception as e:
                if verbose:
                    print(f"  ⚠️ Failed to find manual links: {e}")
                manual_links = []
            
            # Sort candidates by score
            best_url = None
            for link in manual_links:
                # Try each link until we find a valid manual
                try:
                    if verbose:
                        print(f"  ↪ trying manual URL: {link}")
                        
                    pdf_path = download_manual_pdf(link, product_url=url)
                    if pdf_path:  # Validation passed
                        best_url = link
                        break
                except Exception as e:
                    if verbose:
                        print(f"  ↪ failed to download/validate: {e}")
                    continue

            if not best_url:
                if verbose:
                    print("  ↪ no valid user manual PDF found")
                continue

            # Save to DB
            mark_manual(product_url=url, manual_url=best_url, manual_path=pdf_path)

            done += 1
            if verbose:
                print(f"  ✅ manual saved -> {pdf_path}")

        except Exception as e:
            failed += 1
            if verbose:
                print(f"  ❌ product fail {url}: {e}")
            
            # If we have too many consecutive failures, pause longer
            if failed > 0 and failed % 10 == 0:  # Every 10 failures
                pause_minutes = min(failed // 10 * 5, 30)  # Progressive pause, max 30 min
                print(f"  ⚠️ Many failures ({failed}), pausing for {pause_minutes} minutes...")
                time.sleep(pause_minutes * 60)
                
            # Add delay between products to avoid overwhelming server
            if i % 50 == 0:  # Every 50 products
                print(f"  ⏱️ Processed {i} products, taking a 2-minute break...")
                time.sleep(120)

    if verbose:
        print(f"✅ products processed (manuals): {done}/{len(urls)} (failed: {failed}, dns_failures: {dns_failures})")

# ---------- category runner ----------
def run_categories(limit: int, skip_done: bool, start_after: Optional[str], force_llm: bool, verbose: bool):
    init_schema()

    # 1) Parse category sitemap
    urls = parse_product_sitemap(SITEMAP_CATEGORY)
    if limit and limit > 0:
        urls = urls[:limit]
        
    # Handle start_after
    if start_after:
        try:
            idx = urls.index(start_after)
            urls = urls[idx + 1:]
        except ValueError:
            if verbose:
                print(f"Warning: start-after URL not found: {start_after}")

    done = 0
    for i, url in enumerate(urls, 1):
        try:
            if verbose:
                print(f"[CAT {i}/{len(urls)}] {url}")

            # Skip if already summarized
            row = get_category_by_url(url)
            if skip_done and row and row.get("short_desc_done") == 1 and not force_llm:
                if verbose:
                    print("  ↪ skipped (short_desc_done=1)")
                continue

            # Fetch category page
            r = _fetch(url, timeout=40)
            r.raise_for_status()
            html = r.text
            soup = BeautifulSoup(html, "html.parser")

            # Extract title and description
            title = _norm_space(soup.find("h1").get_text(" ")) if soup.find("h1") else None
            if not title:
                t = soup.find("title")
                title = _norm_space(t.get_text(" ")) if t else None

            # Get meta description and other descriptive text
            meta_desc = ""
            meta = soup.find("meta", {"name": "description"})
            if meta:
                meta_desc = meta.get("content", "")

            # Get first few paragraphs
            paras = []
            for p in soup.find_all("p")[:3]:  # first 3 paragraphs
                text = _norm_space(p.get_text(" "))
                if len(text) > 50:  # only meaningful paragraphs
                    paras.append(text)

            desc_text = "\\n".join(filter(None, [meta_desc] + paras))

            if not title and not desc_text:
                if verbose:
                    print("  ↪ no content found to summarize")
                continue

            # Save basic info first
            upsert_category(url=url, name=title)

            # Send to LLM for summarization
            from aproject.analyzer import summarize_category
            short_desc, keywords = summarize_category(title=title, description=desc_text)
            
            # Save LLM results
            mark_category_summarized(url=url, short_desc=short_desc, keywords=keywords)
            done += 1

            if verbose:
                print(f"  ✅ category summarized")

        except Exception as e:
            if verbose:
                print(f"  ❌ category fail {url}: {e}")

    if verbose:
        print(f"✅ categories processed: {done}/{len(urls)}")

# ---------- CLI ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--products", action="store_true", help="Scrape products and download manuals")
    ap.add_argument("--categories", action="store_true", help="Scrape categories and summarize")
    ap.add_argument("--limit", type=int, default=200, help="Maximum items to process")
    ap.add_argument("--skip-done", action="store_true", help="Skip already processed items")
    ap.add_argument("--start-after", help="Resume processing after this URL")
    ap.add_argument("--force-llm", action="store_true", help="Force re-run LLM even if done")
    ap.add_argument("--verbose", action="store_true", help="More logging")
    ap.add_argument("--url", help="Process a single product URL")
    args = ap.parse_args()

    if args.url:
        run_products(limit=1, skip_done=False, verbose=True)
    elif args.products:
        run_products(
            limit=args.limit,
            skip_done=args.skip_done,
            verbose=args.verbose
        )
    elif args.categories:
        run_categories(
            limit=args.limit,
            skip_done=args.skip_done,
            start_after=args.start_after,
            force_llm=args.force_llm,
            verbose=args.verbose
        )
    else:
        print("Usage: python -m aproject.scraper [--products|--categories|--url URL] [OPTIONS]")
        print("\nOptions:")
        print("  --limit N          Maximum items to process")
        print("  --skip-done        Skip already processed items")
        print("  --start-after URL  Resume processing after this URL")
        print("  --force-llm        Force re-run LLM even if done")
        print("  --verbose          More logging")
        print("  --url URL          Process a single product URL")
        return

if __name__ == "__main__":
    main()
