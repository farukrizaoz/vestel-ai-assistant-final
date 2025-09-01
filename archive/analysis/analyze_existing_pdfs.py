#!/usr/bin/env python3
"""
LLM Analysis for Existing PDFs
Analyze already downloaded PDFs with improved LLM prompts
"""

import os
import time
import random
from typing import Dict, Any

from aproject.db import get_conn, update_manual_analysis
from aproject.analyzer import summarize_product_from_pdf

def get_unanalyzed_products():
    """Get products that have PDFs but no LLM analysis."""
    conn = get_conn()
    cursor = conn.cursor()
    
    # Products with manual but no analysis
    cursor.execute("""
        SELECT url, name, manual_path, manual_url 
        FROM products 
        WHERE manual_path IS NOT NULL 
        AND manual_path != ''
        AND (manual_keywords IS NULL OR manual_keywords = '')
        ORDER BY id
    """)
    
    results = cursor.fetchall()
    conn.close()
    
    return [
        {
            "url": row[0],
            "name": row[1], 
            "manual_path": row[2],
            "manual_url": row[3]
        }
        for row in results
    ]

def analyze_single_pdf(product: Dict[str, str]) -> bool:
    """Analyze a single PDF with LLM."""
    try:
        print(f"\n🔍 Analyzing: {product['name'][:50]}...")
        print(f"   PDF: {os.path.basename(product['manual_path'])}")
        
        # Check if PDF file exists
        if not os.path.exists(product['manual_path']):
            print(f"   ❌ PDF file not found: {product['manual_path']}")
            return False
        
        # Get file size
        size_kb = os.path.getsize(product['manual_path']) / 1024
        print(f"   📄 PDF size: {size_kb:.1f}KB")
        
        if size_kb < 20:
            print(f"   ⚠️ PDF too small, skipping")
            return False
        
        # Add delay to avoid API rate limits
        delay = random.uniform(2, 5)
        print(f"   ⏱️ Waiting {delay:.1f}s before API call...")
        time.sleep(delay)
        
        # Analyze with LLM
        analysis = summarize_product_from_pdf(
            product['manual_path'],
            product['name'] or "Ürün",
            product['url']
        )
        
        if not analysis:
            print(f"   ❌ LLM analysis returned empty")
            return False
        
        # Clean and validate analysis
        keywords = analysis.get("keywords", [])
        description = analysis.get("short_desc", "")
        model_number = analysis.get("model_number", "")
        
        # Ensure keywords is a list
        if isinstance(keywords, str):
            keywords = [k.strip() for k in keywords.split(",") if k.strip()]
        elif not isinstance(keywords, list):
            keywords = []
        
        # Clean and validate
        description_str = str(description) if description else ""
        model_number_str = str(model_number) if model_number else ""
        
        # Validate we have meaningful data
        if not description_str or len(description_str) < 10:
            print(f"   ⚠️ Description too short: '{description_str}'")
            return False
        
        if not keywords or len(keywords) < 3:
            print(f"   ⚠️ Not enough keywords: {keywords}")
            return False
        
        # Update database - send keywords as list
        update_manual_analysis(
            product_url=product['url'],
            keywords=keywords,  # Send as list
            description=description_str,
            model_number=model_number_str
        )
        
        print(f"   ✅ Analysis complete:")
        print(f"      Model: {model_number_str or 'N/A'}")
        print(f"      Keywords: {len(keywords)} found")
        print(f"      Description: {description_str[:60]}...")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Analysis failed: {e}")
        return False

def main():
    print("🤖 Starting Continuous LLM Analysis")
    
    # Set API key
    import os
    if not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = "AIzaSyDmg6APFLNxDmcCMeDJxvW9dWCSTpiqpqU"
        print("✅ API key configured")
    
    success_count = 0
    failure_count = 0
    round_number = 1
    
    print("🔄 Starting continuous analysis - will check for new products every 60 seconds")
    
    while True:
        try:
            print(f"\n{'='*60}")
            print(f"🔍 Analysis Round {round_number}")
            
            # Get products to analyze
            products = get_unanalyzed_products()
            print(f"📊 Found {len(products)} products with unanalyzed PDFs")
            
            if not products:
                print("✅ All current products analyzed! Waiting for new ones...")
                print("⏱️ Sleeping for 60 seconds...")
                time.sleep(60)
                round_number += 1
                continue
            
            # Process each product
            for i, product in enumerate(products, 1):
                print(f"\n--- Product {i}/{len(products)} (Round {round_number}) ---")
                
                try:
                    success = analyze_single_pdf(product)
                    if success:
                        success_count += 1
                    else:
                        failure_count += 1
                        
                except KeyboardInterrupt:
                    print(f"\n⚠️ Interrupted by user")
                    print(f"📊 Final Stats: Success: {success_count}, Failed: {failure_count}")
                    return
                except Exception as e:
                    print(f"   ❌ Unexpected error: {e}")
                    failure_count += 1
            
            # Round summary
            print(f"\n✅ Round {round_number} complete!")
            print(f"   Total Success: {success_count}")
            print(f"   Total Failed: {failure_count}")
            print(f"   Overall Success Rate: {success_count/(success_count + failure_count)*100:.1f}%")
            
            round_number += 1
            
            # Small break between rounds
            print("⏱️ Waiting 30 seconds before next round...")
            time.sleep(30)
            
        except KeyboardInterrupt:
            print(f"\n⚠️ Continuous analysis stopped by user")
            print(f"📊 Final Stats: Success: {success_count}, Failed: {failure_count}")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            print("⏱️ Waiting 60 seconds before retry...")
            time.sleep(60)

if __name__ == "__main__":
    main()
