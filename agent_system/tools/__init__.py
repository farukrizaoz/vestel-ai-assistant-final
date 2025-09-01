"""
Tools Module Init - Import all tools
"""

from .search_tool import ImprovedProductSearchTool

try:
    from .pdf_tool import PDFAnalysisTool
    __all__ = ['ImprovedProductSearchTool', 'PDFAnalysisTool']
except ImportError as e:
    print(f"❌ PDFAnalysisTool import failed: {e}")
    __all__ = ['ImprovedProductSearchTool']
