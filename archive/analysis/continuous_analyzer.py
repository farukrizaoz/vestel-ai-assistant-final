#!/usr/bin/env python3
"""
Continuous LLM Analyzer
Continuously monitors database for new PDFs and analyzes them with LLM
Runs parallel to the main scraper
"""

import os
import time
import logging
import random
from typing import List, Tuple, Dict, Any
from aproject.db import get_conn, update_manual_analysis
from aproject.analyzer import summarize_product_from_pdf

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('continuous_analyzer.log'),
        logging.StreamHandler()
    ]
)

def get_unanalyzed_products():
    """Get products that have PDFs but no LLM analysis."""
    conn = get_conn()
    cursor = conn.cursor()
    
    # Products with manual but no analysis - same as analyze_existing_pdfs.py
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
    """Analyze a single PDF with LLM - same logic as analyze_existing_pdfs.py"""
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
        import random
        delay = random.uniform(2, 5)
        print(f"   ⏱️ Waiting {delay:.1f}s before API call...")
        time.sleep(delay)
        
        # Analyze with LLM - same parameters as analyze_existing_pdfs.py
        analysis = summarize_product_from_pdf(
            product['manual_path'],
            product['name'] or "Ürün",
            product['url']
        )
        
        if not analysis:
            print(f"   ❌ LLM analysis returned empty")
            return False
        
        # Clean and validate analysis - same logic as analyze_existing_pdfs.py
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
        
        # Update database - same call as analyze_existing_pdfs.py
        from aproject.db import update_manual_analysis
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
        logging.error(f"Analysis error: {e}")
        return False

def main():
    """Main continuous analysis loop."""
    print("🤖 Starting Continuous LLM Analysis")
    print("   This will run continuously, analyzing new PDFs as they appear")
    print("   Press Ctrl+C to stop")
    
    # Set API key
    if not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = "AIzaSyDmg6APFLNxDmcCMeDJxvW9dWCSTpiqpqU"
        print("✅ API key configured")
    
    success_count = 0
    failure_count = 0
    round_number = 1
    
    print("🔄 Starting continuous analysis - will check for new products every 60 seconds")
    
    while True:
        try:
            print(f"\n{'='*80}")
            print(f"🔍 Analysis Round {round_number} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
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
            round_success = 0
            round_failures = 0
            
            for i, product in enumerate(products, 1):
                print(f"\n{'='*60}")
                print(f"Product {i}/{len(products)} (Round {round_number})")
                
                try:
                    success = analyze_single_pdf(product)
                    if success:
                        success_count += 1
                        round_success += 1
                    else:
                        failure_count += 1
                        round_failures += 1
                        
                except KeyboardInterrupt:
                    print(f"\n⚠️ Interrupted by user")
                    print(f"📊 Final Stats: Success: {success_count}, Failed: {failure_count}")
                    return
                except Exception as e:
                    print(f"   ❌ Unexpected error: {e}")
                    logging.error(f"Unexpected error in main loop: {e}")
                    failure_count += 1
                    round_failures += 1
            
            # Round summary
            print(f"\n✅ Round {round_number} complete!")
            print(f"   This Round: Success: {round_success}, Failed: {round_failures}")
            print(f"   Total Success: {success_count}")
            print(f"   Total Failed: {failure_count}")
            if (success_count + failure_count) > 0:
                print(f"   Overall Success Rate: {success_count/(success_count + failure_count)*100:.1f}%")
            
            round_number += 1
            
            # Break between rounds
            if products:  # Only wait if we processed products this round
                print("⏱️ Waiting 30 seconds before next round...")
                time.sleep(30)
            
        except KeyboardInterrupt:
            print(f"\n⚠️ Continuous analysis stopped by user")
            print(f"📊 Final Stats: Success: {success_count}, Failed: {failure_count}")
            logging.info(f"Analysis stopped by user. Final stats: Success: {success_count}, Failed: {failure_count}")
            break
        except Exception as e:
            print(f"❌ Error in main loop: {e}")
            logging.error(f"Main loop error: {e}")
            print("⏱️ Waiting 60 seconds before retry...")
            time.sleep(60)

if __name__ == "__main__":
    main()
