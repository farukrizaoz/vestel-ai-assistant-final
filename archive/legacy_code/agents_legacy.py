"""
Legacy agents.py - yönlendirme dosyası
Modüler yapıya geçiş için backward compatibility
"""

from agent_system.agents import create_router_agent, create_pdf_agent, create_quickstart_agent

# Backward compatibility için export
__all__ = [
    'create_router_agent',
    'create_pdf_agent', 
    'create_quickstart_agent'
]
