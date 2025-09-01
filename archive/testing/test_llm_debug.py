#!/usr/bin/env python3
"""
Test LLM Analysis with Debug Output
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from aproject.analyzer import summarize_product_from_pdf

def test_single_pdf():
    """Test LLM analysis with debug output."""
    
    # Set API key
    if not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = "AIzaSyDmg6APFLNxDmcCMeDJxvW9dWCSTpiqpqU"
    
    # Test PDF path
    pdf_path = "/home/vestel/Desktop/aproject/manuals/vestel-mf-42-mb-mini-firin-p-428__20261660_k.pdf"
    
    if not os.path.exists(pdf_path):
        print("❌ Test PDF not found!")
        return
    
    print("🧪 Testing LLM Analysis...")
    print(f"📄 PDF: {os.path.basename(pdf_path)}")
    
    try:
        result = summarize_product_from_pdf(pdf_path, "Test Mini Fırın", "test-url")
        
        print("✅ Analysis successful!")
        print(f"\n📝 Description: {result['short_desc']}")
        print(f"\n🏷️ Model: {result['model_number']}")
        print(f"\n🔧 Keywords ({len(result['keywords'])}):")
        
        for i, keyword in enumerate(result['keywords'], 1):
            print(f"   {i:2d}. {keyword}")
            
        # Check for character separation issue
        has_char_separation = any(',' in k and len(k.split(',')) > 3 for k in result['keywords'])
        if has_char_separation:
            print("\n❌ DETECTED CHARACTER SEPARATION ISSUE!")
            for keyword in result['keywords']:
                if ',' in keyword and len(keyword.split(',')) > 3:
                    print(f"   Problem keyword: {keyword}")
        else:
            print("\n✅ No character separation issues detected")
            
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

if __name__ == "__main__":
    test_single_pdf()
