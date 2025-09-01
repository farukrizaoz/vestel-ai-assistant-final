#!/usr/bin/env python3
"""
Simple Fast Scraper - Bypass Session Management Issues
"""

import requests
import sqlite3
import xml.etree.ElementTree as ET
import time
import re
import os
from urllib.parse import urljoin
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

# Global lock for database operations
db_lock = Lock()

def simple_fetch(url, timeout=10, max_retries=3):
    """Simple fetch function without session management"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"❌ Failed to fetch {url} after {max_retries} attempts: {e}")
                return None
            time.sleep(1)  # Brief pause between retries
    return None

def extract_products_from_sitemap():
    """Extract product URLs from sitemap"""
    sitemap_url = "https://statics.vestel.com.tr/vstlsitemap/product.xml"
    print(f"� Fetching sitemap: {sitemap_url}")
    
    response = simple_fetch(sitemap_url)
    if not response:
        return []
    
    print(f"✅ Sitemap fetched: {len(response.content)} bytes")
    
    try:
        root = ET.fromstring(response.content)
        urls = []
        
        for url in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
            loc = url.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc is not None and '-p-' in loc.text:
                urls.append(loc.text)
        
        print(f"🔍 Found {len(urls)} product URLs")
        return urls
        
    except Exception as e:
        print(f"❌ Error parsing sitemap: {e}")
        return []

def save_product_url(url):
    """Save product URL to database"""
    with db_lock:
        try:
            conn = sqlite3.connect('vestel_products.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR IGNORE INTO products (url) 
                VALUES (?)
            ''', (url,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False

def process_product_url(args):
    """Process a single product URL"""
    url, index, total = args
    
    try:
        # Save URL to database
        if save_product_url(url):
            print(f"✅ [{index}/{total}] Saved: {url}")
            return True
        else:
            print(f"⚠️ [{index}/{total}] Failed to save: {url}")
            return False
            
    except Exception as e:
        print(f"❌ [{index}/{total}] Error processing {url}: {e}")
        return False

def get_existing_products():
    """Get count of existing products in database"""
    try:
        conn = sqlite3.connect('vestel_products.db')
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM products')
        count = cursor.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def main():
    """Main execution function"""
    print("=== Simple Fast Scraper ===")
    
    # Check existing products
    existing_count = get_existing_products()
    print(f"📊 Existing products in database: {existing_count}")
    
    # Extract products from sitemap
    product_urls = extract_products_from_sitemap()
    
    if not product_urls:
        print("❌ No product URLs found. Exiting.")
        return
    
    print(f"🎯 Processing {len(product_urls)} product URLs")
    
    # Process URLs with threading
    with ThreadPoolExecutor(max_workers=10) as executor:
        args_list = [(url, i+1, len(product_urls)) for i, url in enumerate(product_urls)]
        results = list(executor.map(process_product_url, args_list))
    
    # Summary
    successful = sum(1 for r in results if r)
    print(f"\n📊 Summary:")
    print(f"   Total URLs: {len(product_urls)}")
    print(f"   Successfully saved: {successful}")
    print(f"   Failed: {len(product_urls) - successful}")
    
    # Final count
    final_count = get_existing_products()
    print(f"   Final database count: {final_count}")

if __name__ == "__main__":
    main()
