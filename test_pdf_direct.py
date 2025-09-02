#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Önce config yolunu ayarla
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent

# Config oluştur
sys.path.insert(0, str(PROJECT_ROOT))

print("=== PDF TOOL TEST ===")
print(f"Project root: {PROJECT_ROOT}")

try:
    # PDF tool'u import et
    from agent_system.tools.pdf_tool import PDFAnalysisTool
    print("✅ PDF Tool import edildi")
    
    # Tool'u oluştur
    tool = PDFAnalysisTool()
    print("✅ Tool oluşturuldu")
    
    # AD-6001 X ile test et
    result = tool._run('AD-6001 X')
    print("✅ Tool çalıştırıldı")
    print("\n" + "="*80)
    print("SONUÇ:")
    print("="*80)
    print(result)
    print("="*80)
    
except Exception as e:
    print(f"❌ HATA: {e}")
    import traceback
    traceback.print_exc()
