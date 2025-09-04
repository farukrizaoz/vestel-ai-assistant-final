"""
PDF Analysis Tool - OCR Destekli PDF okuma (Gelişmiş Sürüm)
"""

import os
import re
import time
import unicodedata
from pathlib import Path
import sqlite3
from typing import List, Tuple, Iterable, Optional
import PyPDF2
from crewai.tools import BaseTool

# OCR için gerekli import'lar
try:
    import pytesseract
    from pdf2image import convert_from_path
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

# Proje kök dizinini belirle
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Configuration
MAX_TEXT_LENGTH = 30000  # Çok daha büyük limit - 100K karakter
MAX_PROCESSING_TIME = 120  # 2 dakika - daha uzun süre


# ============== Yardımcılar ==============

def normalize_unicode(s: str) -> str:
    # NFKC: ligature/compat karakterlerini düzeltir
    return unicodedata.normalize("NFKC", s or "")

def clean_text(raw: str) -> str:
    """Satırsonu tirelerini kaldır, aşırı boşlukları sıkıştır, görünmezleri temizle."""
    if not raw:
        return ""
    s = normalize_unicode(raw)

    # 1) Satır sonu tire + newline -> kelimeyi birleştir
    s = re.sub(r"(\w)-\n(\w)", r"\1\2", s)

    # 2) Sert satırsonlarını paragrafa çevir (tablo sayfalarında aşırı kırılmayı azalt)
    #    Kural: tek newline'ları boşluk yap, ardışık 2+ newline paragraf kalsın
    s = s.replace("\r", "")
    s = re.sub(r"\n{3,}", "\n\n", s)           # 3+ newline -> 2 newline
    s = re.sub(r"(?<!\n)\n(?!\n)", " ", s)    # tek newline -> boşluk

    # 3) Boşlukları sadeleştir
    s = re.sub(r"[ \t\u200b\u00a0]+", " ", s)
    # Baş/son boşluk
    s = s.strip()
    return s

def is_text_meaningful(s: str, min_len: int = 150) -> bool:  # Daha düşük threshold
    """Sayfa metni yeterince zengin mi? (sadece rakam/başlık değil)"""
    if not s or len(s) < min_len:
        return False
    # Heuristik: harf oranı - daha toleranslı
    letters = sum(c.isalpha() for c in s)
    return (letters / max(len(s), 1)) > 0.20  # %20'ye düşürüldü

def extract_text_pypdf2_page(reader: PyPDF2.PdfReader, idx: int) -> str:
    try:
        page = reader.pages[idx]
        t = page.extract_text() or ""
        return clean_text(t)
    except Exception:
        return ""

def ocr_single_page(pdf_path: Path, page_no_1based: int, dpi: int = 140, lang: str = "tur+eng") -> str:
    """Sadece istenen sayfayı rasterize edip OCR uygula."""
    try:
        imgs = convert_from_path(pdf_path, first_page=page_no_1based, last_page=page_no_1based, dpi=dpi)
        if not imgs:
            return ""
        try:
            txt = pytesseract.image_to_string(imgs[0], lang=lang)
        except Exception:
            # Dil paketi yoksa en azından 'eng'
            txt = pytesseract.image_to_string(imgs[0], lang="eng")
        return clean_text(txt)
    except Exception:
        return ""

def page_text_hybrid(reader: PyPDF2.PdfReader, pdf_path: Path, idx: int,
                     ocr_if_needed: bool = True,
                     ocr_dpi: int = 120,  # Düşük DPI
                     min_len_for_ok: int = 150) -> Tuple[str, bool]:  # Düşük threshold
    """
    Tek sayfa: önce PyPDF2, yetmezse OCR. (text, ocr_used)
    """
    # 0-based -> 1-based
    p1 = idx + 1
    t = extract_text_pypdf2_page(reader, idx)
    if is_text_meaningful(t, min_len=min_len_for_ok):
        return (t, False)

    # OCR'a daha az başvur - sadece gerçekten boşsa
    if ocr_if_needed and OCR_AVAILABLE and len(t.strip()) < 50:  # Çok boşsa OCR yap
        t2 = ocr_single_page(pdf_path, p1, dpi=ocr_dpi)
        if t2 and len(t2.strip()) > 30:  # OCR'dan az bile olsa bir şey gelirse kullan
            return (t2, True)

    # pypdf2 metni azsa da döndür (boş kalmasın)
    return (t, False)

def iter_pdf_text_stream(pdf_path: Path,
                         max_seconds: Optional[int] = None,
                         ocr_dpi: int = 140,
                         ocr_if_needed: bool = True,
                         progress_cb: Optional[callable] = None) -> Iterable[str]:
    """
    Uzun PDF'lerde bile sayfa sayfa, hafıza-dostu metin üretir.
    - Zaman sınırı aşılırsa durur.
    - Her sayfada PYPDF2 -> gerekirse OCR.
    - progress_cb(page_index_1based, total_pages, used_ocr: bool, char_count: int) çağrılır.
    """
    start = time.monotonic()
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
            except Exception:
                raise RuntimeError("PDF şifreli ve açılamadı")

        total = len(reader.pages)
        for i in range(total):
            if max_seconds and (time.monotonic() - start) > max_seconds:
                # Kibarca kes
                yield f"\n\n[⏱️ Zaman sınırı nedeniyle {i}/{total} sayfada duruldu.]"
                break

            txt, used_ocr = page_text_hybrid(
                reader, pdf_path, i,
                ocr_if_needed=ocr_if_needed,
                ocr_dpi=ocr_dpi,
                min_len_for_ok=150  # Daha düşük threshold
            )

            # Sayfa başlığı ekle (uzun belgede sayfa sınırları anlaşılır olsun)
            page_banner = f"\n\n--- Sayfa {i+1}/{total} ---\n"
            out = page_banner + (txt if txt else "[Bu sayfadan anlamlı metin elde edilemedi]")
            if progress_cb:
                try:
                    progress_cb(i+1, total, used_ocr, len(txt))
                except Exception:
                    pass
            yield out


def extract_pdf_full_text(pdf_path: Path, prefer_speed: bool = True) -> str:
    """
    Uzun PDF'ler için tam metin çıkarır - TÜM SAYFALARI İŞLE
    """
    # Zaman sınırı kaldırıldı, tüm sayfalar işlenecek
    ocr_dpi = 120  # Düşük DPI
    max_secs = 30   # Zaman sınırı yok
    max_pages_to_process = 30  # Sayfa sınırı yok

    used_any_ocr = {"flag": False}
    processed_pages = {"count": 0}

    def progress(page_i, total, used_ocr, nchar):
        if used_ocr:
            used_any_ocr["flag"] = True
        processed_pages["count"] = page_i
        if page_i % 5 == 0 or used_ocr:  # Her 5 sayfada bir log
            print(f"📄 [{page_i}/{total}] {'🔍' if used_ocr else '📝'} {nchar}ch")

    parts = []
    total_chars = 0
    page_count = 0
    
    for chunk in iter_pdf_text_stream(
        pdf_path=pdf_path,
        max_seconds=max_secs,
        ocr_dpi=ocr_dpi,
        ocr_if_needed=True,
        progress_cb=progress
    ):
        parts.append(chunk)
        total_chars += len(chunk)
        page_count += 1
        
        # Sayfa limiti kontrolü kaldırıldı - tüm sayfalar işlenecek
        
        # Memory protection - daha büyük limit
        if total_chars > MAX_TEXT_LENGTH * 3:  # 90000 karakter limiti
            parts.append(f"\n\n[📄 Çok büyük dosya - içerik kısaltıldı.]")
            break

    body = "\n".join(parts).strip()
    
    # Final truncation - daha büyük limit
    if len(body) > MAX_TEXT_LENGTH * 3:  # 90000 karakter
        body = body[:MAX_TEXT_LENGTH * 3] + "\n\n[📄 Çok büyük dosya - kısaltıldı.]"
    
    header = f"📄 {pdf_path.name} - Tam Analiz"
    if used_any_ocr["flag"]:
        header += " [🔍 OCR]"
    header += f" ({processed_pages['count']} sayfa)"
    
    return f"{header}\n\n{body}"


def _normalize_text(s: str) -> str:
    # Karşılaştırmalar için sade normalize (aksan/küçük harf vs.)
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in s if not unicodedata.combining(ch)).lower()


def _score_match(product_text: str, terms: List[str]) -> int:
    # Basit skor: kaç terim geçtiyse + model eşleşmelerine küçük bonus
    score = 0
    for t in terms:
        if len(t) > 1 and t in product_text:
            score += 1
    # Model benzeri kısa tokenlar varsa ekstra puan (ör. "x600", "ad-6001" vs)
    if any(len(t) >= 3 and t in product_text for t in terms):
        score += 1
    return score


class PDFAnalysisTool(BaseTool):
    name: str = "PDF Kılavuz Analizi"
    description: str = "Belirtilen ürünün PDF kılavuzunu bulur ve içeriğini döndürür (DB'deki manual_path'e göre)."

    def _run(self, product_name: str) -> str:
        """
        Veritabanından manual_path'i güvenli şekilde bulur,
        PDF'i (gerekirse ilk N sayfa) okur ve metni döndürür.
        """
        try:
            from agent_system.config import PRODUCTS_DATABASE_PATH
        except Exception as e:
            return f"Yapılandırma hatası: PRODUCTS_DATABASE_PATH okunamadı ({e})"

        # 1) Arama terimlerini hazırla
        raw_terms = (
            product_name or ""
        ).replace("-", " ").replace("_", " ").split()
        terms = [_normalize_text(t) for t in raw_terms if t.strip()]
        if not terms:
            return "Geçerli bir ürün adı/terimi vermelisin."

        # 2) DB'den adayları çek (LIKE ile daralt, sonra skorla)
        candidates: List[Tuple[str, str, str]] = []
        try:
            conn = sqlite3.connect(PRODUCTS_DATABASE_PATH)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()

            # Dinamik LIKE koşulları
            # name/model_number alanlarında herhangi bir terim geçen ve manual_path'i dolu olanlar
            like_clauses = []
            params = []
            for t in terms:
                like_clauses.append("(LOWER(name) LIKE ? OR LOWER(model_number) LIKE ?)")
                like = f"%{t}%"
                params.extend([like, like])

            where_like = " OR ".join(like_clauses) if like_clauses else "1=1"
            sql = f"""
                SELECT name, model_number, manual_path
                FROM products
                WHERE manual_path IS NOT NULL
                  AND manual_path != ''
                  AND ({where_like})
            """
            cur.execute(sql, params)
            rows = cur.fetchall()
            for r in rows:
                candidates.append((r["name"] or "", r["model_number"] or "", r["manual_path"] or ""))
        except Exception as e:
            return f"Veritabanı arama hatası: {e}"
        finally:
            try:
                conn.close()
            except Exception:
                pass

        if not candidates:
            return f"'{product_name}' için veritabanında manuel kaydı bulunamadı."

        # 3) En iyi eşleşmeyi seç (skorla)
        best = None
        best_score = -1
        for name, model, path in candidates:
            product_text = _normalize_text(f"{name} {model}")
            score = _score_match(product_text, terms)
            if score > best_score:
                best = (name, model, path)
                best_score = score

        if not best:
            return f"'{product_name}' için uygun bir manuel bulunamadı."

        name, model, manual_path = best

        # 4) Yolu normalize et & varlık kontrolü
        pdf_path = Path(manual_path)
        if not pdf_path.is_absolute():
            # DB göreli yol tuttuysa proje köküne göre çöz
            pdf_path = (PROJECT_ROOT / pdf_path).resolve()

        if not pdf_path.exists():
            # Bazı kayıtlar 'manuals/xxx.pdf' gibi olabilir; alternatif kontrol
            alt_path = (PROJECT_ROOT / "manuals" / Path(manual_path).name).resolve()
            if alt_path.exists():
                pdf_path = alt_path
            else:
                return (
                    f"Manuel yolu bulundu ama dosya yok:\n"
                    f"- Ürün: {name} ({model})\n"
                    f"- Yol: {manual_path}"
                )

        matching_pdf = pdf_path.name

        # 5) Yeni gelişmiş PDF okuma sistemi
        try:
            print(f"🔍 PDF analiz başlıyor: {matching_pdf}")
            full_text = extract_pdf_full_text(pdf_path, prefer_speed=True)
            
            if full_text:
                return (
                    f"✅ PDF bulundu ve işlendi: {matching_pdf}\n"
                    f"📊 Ürün: {name} ({model})\n\n"
                    f"📄 İçerik:\n{full_text}"
                )
            else:
                return (
                    f"❌ PDF bulundu ({matching_pdf}) ancak metin çıkarılamadı.\n"
                    f"📊 Ürün: {name} ({model})"
                )

        except Exception as e:
            return f"❌ PDF okuma hatası: {e}"


# Export için alias
__all__ = ["PDFAnalysisTool"]
