"""
Agent initialization module
"""

from .router_agent import create_router_agent
from .pdf_agent import create_pdf_agent  
from .quickstart_agent import create_quickstart_agent

__all__ = [
    'create_router_agent',
    'create_pdf_agent',
    'create_quickstart_agent'
]
