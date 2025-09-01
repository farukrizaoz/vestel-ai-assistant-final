#!/usr/bin/env python3
"""
Debug sitemap fetch issue
"""

import requests
from aproject.config import SITEMAP_PRODUCT

def test_simple_requests():
    """Test with simple requests"""
    print(f"Testing with simple requests: {SITEMAP_PRODUCT}")
    
    try:
        response = requests.get(SITEMAP_PRODUCT, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Content length: {len(response.content)}")
        print(f"URL after redirects: {response.url}")
        
        if response.status_code == 200:
            print("✅ Simple requests works!")
            return True
        else:
            print(f"❌ Failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_with_session():
    """Test with session (like original scraper)"""
    print(f"\nTesting with session: {SITEMAP_PRODUCT}")
    
    try:
        session = requests.Session()
        
        # Add headers like original scraper
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        response = session.get(SITEMAP_PRODUCT, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"URL after redirects: {response.url}")
        print(f"Content length: {len(response.content)}")
        
        if response.status_code == 200:
            print("✅ Session works!")
            return True
        else:
            print(f"❌ Failed with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

if __name__ == "__main__":
    print("=== Sitemap Debug ===")
    
    # Test simple requests
    simple_works = test_simple_requests()
    
    # Test with session
    session_works = test_with_session()
    
    print(f"\n=== Results ===")
    print(f"Simple requests: {'✅' if simple_works else '❌'}")
    print(f"Session: {'✅' if session_works else '❌'}")
