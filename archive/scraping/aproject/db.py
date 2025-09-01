# aproject/db.py
import sqlite3
from typing import Optional, Dict, Any, List
from aproject.config import DB_PATH

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def _column_exists(cur: sqlite3.Cursor, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row["name"] == col for row in cur.fetchall())

def init_schema():
    conn = get_conn()
    cur = conn.cursor()

    # Create categories table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        name TEXT,
        short_desc TEXT,
        keywords TEXT,
        short_desc_done INTEGER DEFAULT 0
    )
    """)

    # Create products table with category_id foreign key
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE,
        name TEXT,
        category_id INTEGER,
        manual_url TEXT,
        manual_path TEXT,
        manual_done INTEGER DEFAULT 0,
        manual_keywords TEXT,
        manual_desc TEXT,
        model_number TEXT,
        FOREIGN KEY(category_id) REFERENCES categories(id)
    )
    """)

    # Add model_number column if it doesn't exist
    if not _column_exists(cur, "products", "model_number"):
        cur.execute("ALTER TABLE products ADD COLUMN model_number TEXT")

    # Enable foreign key support
    cur.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()

def upsert_category(url: str, name: Optional[str] = None, short_desc: Optional[str] = None, keywords: Optional[str] = None) -> int:
    """Insert or update a category, returns category id"""
    conn = get_conn()
    cur = conn.cursor()
    
    cur.execute("SELECT id FROM categories WHERE url=?", (url,))
    row = cur.fetchone()
    
    if row:
        updates = []
        params = []
        if name is not None:
            updates.append("name=?")
            params.append(name)
        if short_desc is not None:
            updates.append("short_desc=?")
            params.append(short_desc)
        if keywords is not None:
            updates.append("keywords=?")
            params.append(keywords)
        
        if updates:
            cur.execute(
                f"UPDATE categories SET {', '.join(updates)} WHERE id=?",
                tuple(params + [row["id"]])
            )
        cat_id = row["id"]
    else:
        cur.execute(
            "INSERT INTO categories (url, name, short_desc, keywords, short_desc_done) VALUES (?, ?, ?, ?, 0)",
            (url, name, short_desc, keywords)
        )
        cat_id = cur.lastrowid
    
    conn.commit()
    conn.close()
    return cat_id

def mark_category_summarized(url: str, short_desc: str, keywords: str):
    """Mark a category as summarized with LLM results"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE categories SET short_desc=?, keywords=?, short_desc_done=1 WHERE url=?",
        (short_desc, keywords, url)
    )
    conn.commit()
    conn.close()

def get_category_by_url(url: str) -> Optional[Dict[str, Any]]:
    """Get category by URL"""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM categories WHERE url=?", (url,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def upsert_product_basic(url: str, name: Optional[str] = None, category_id: Optional[int] = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id FROM products WHERE url=?", (url,))
    row = cur.fetchone()
    if row:
        updates = []
        params = []
        if name:
            updates.append("name=?")
            params.append(name)
        if category_id:
            updates.append("category_id=?")
            params.append(category_id)
        if updates:
            cur.execute(
                f"UPDATE products SET {', '.join(updates)} WHERE id=?",
                tuple(params + [row["id"]])
            )
    else:
        cur.execute(
            "INSERT INTO products (url, name, category_id, manual_done) VALUES (?, ?, ?, 0)",
            (url, name, category_id)
        )
    conn.commit()
    conn.close()

def mark_manual(product_url: str, manual_url: str, manual_path: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE products SET manual_url=?, manual_path=?, manual_done=1 WHERE url=?",
        (manual_url, manual_path, product_url)
    )
    if cur.rowcount == 0:
        cur.execute(
            "INSERT INTO products (url, manual_url, manual_path, manual_done) VALUES (?, ?, ?, 1)",
            (product_url, manual_url, manual_path)
        )
    conn.commit()
    conn.close()

def get_product_by_url(url: str) -> Optional[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM products WHERE url=?", (url,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def list_product_urls(limit: Optional[int] = None) -> List[str]:
    conn = get_conn()
    cur = conn.cursor()
    q = "SELECT url FROM products ORDER BY id ASC"
    if limit and limit > 0:
        q += " LIMIT ?"
        cur.execute(q, (limit,))
    else:
        cur.execute(q)
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows

def update_manual_analysis(product_url: str, keywords, description: str, model_number: Optional[str] = None):
    """Update manual analysis results for a product"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Handle keywords properly - convert to string if it's a list
    if isinstance(keywords, list):
        keywords_str = ", ".join(str(k) for k in keywords if k)
    else:
        keywords_str = str(keywords) if keywords else ""
    
    cur.execute(
        "UPDATE products SET manual_keywords=?, manual_desc=?, model_number=? WHERE url=?",
        (keywords_str, description, model_number, product_url)
    )
    conn.commit()
    conn.close()
