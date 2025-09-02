#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    print("PDF Tool test başlıyor...")
    
    from agent_system.tools.pdf_tool import PDFAnalysisTool
    print("Tool import edildi")
    
    tool = PDFAnalysisTool()
    print("Tool oluşturuldu")
    
    result = tool._run('AD-6001 X')
    print("=== SONUÇ ===")
    print(result)
    print("=== SONUÇ SONU ===")
    
except Exception as e:
    print(f"HATA: {e}")
    import traceback
    traceback.print_exc()
