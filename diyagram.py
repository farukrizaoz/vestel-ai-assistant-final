import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import numpy as np

def create_architecture_diagram():
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis('off')
    
    # Renkler
    colors = {
        'user': '#3498db',
        'frontend': '#2ecc71', 
        'backend': '#e74c3c',
        'agents': '#f39c12',
        'data': '#9b59b6',
        'ai': '#1abc9c'
    }
    
    # Başlık
    ax.text(8, 11.5, 'Vestel AI Agent System Architecture', 
            fontsize=20, weight='bold', ha='center')
    
    # 1. User Layer
    user_box = FancyBboxPatch((1, 9.5), 3, 1, 
                              boxstyle="round,pad=0.1", 
                              facecolor=colors['user'], alpha=0.7)
    ax.add_patch(user_box)
    ax.text(2.5, 10, 'User\n(Web Browser)', ha='center', va='center', 
            fontsize=11, weight='bold', color='white')
    
    # 2. Frontend Layer
    frontend_box = FancyBboxPatch((6, 9.5), 4, 1,
                                  boxstyle="round,pad=0.1",
                                  facecolor=colors['frontend'], alpha=0.7)
    ax.add_patch(frontend_box)
    ax.text(8, 10, 'Frontend Layer\n(JavaScript + Socket.IO)', 
            ha='center', va='center', fontsize=11, weight='bold', color='white')
    
    # 3. Backend API Layer
    backend_box = FancyBboxPatch((12, 9.5), 3, 1,
                                 boxstyle="round,pad=0.1",
                                 facecolor=colors['backend'], alpha=0.7)
    ax.add_patch(backend_box)
    ax.text(13.5, 10, 'Backend API\n(Flask + WebSocket)', 
            ha='center', va='center', fontsize=11, weight='bold', color='white')
    
    # 4. Router Agent (Center)
    router_box = FancyBboxPatch((6.5, 7.5), 3, 1,
                                boxstyle="round,pad=0.1",
                                facecolor=colors['ai'], alpha=0.8)
    ax.add_patch(router_box)
    ax.text(8, 8, '🧠 Router Agent\n(Message Distribution)', 
            ha='center', va='center', fontsize=11, weight='bold', color='white')
    
    # 5. Specialist Agents
    agent_positions = [
        (1, 5.5, "🔍 Product Search\nAgent"),
        (4, 5.5, "📖 PDF Manual\nAgent"), 
        (7, 5.5, "🛠️ Technical Support\nAgent"),
        (10, 5.5, "ℹ️ General Info\nAgent"),
        (13, 5.5, "⚡ Quickstart\nAgent")
    ]
    
    for x, y, text in agent_positions:
        agent_box = FancyBboxPatch((x-0.7, y-0.4), 1.4, 0.8,
                                   boxstyle="round,pad=0.05",
                                   facecolor=colors['agents'], alpha=0.7)
        ax.add_patch(agent_box)
        ax.text(x, y, text, ha='center', va='center', 
                fontsize=9, weight='bold', color='white')
    
    # 6. Tools Layer
    tools_y = 3.5
    
    # Database Tool
    db_box = FancyBboxPatch((0.5, tools_y-0.4), 2.5, 0.8,
                            boxstyle="round,pad=0.05",
                            facecolor=colors['data'], alpha=0.7)
    ax.add_patch(db_box)
    ax.text(1.75, tools_y, '🗄️ Product Database\n(SQLite + Search)', 
            ha='center', va='center', fontsize=9, weight='bold', color='white')
    
    # PDF Tool
    pdf_box = FancyBboxPatch((6, tools_y-0.4), 4, 0.8,
                             boxstyle="round,pad=0.05",
                             facecolor=colors['data'], alpha=0.7)
    ax.add_patch(pdf_box)
    ax.text(8, tools_y, '📄 PDF Analysis Tool\n(1000+ Manuals, Multi-Strategy Search)', 
            ha='center', va='center', fontsize=9, weight='bold', color='white')
    
    # Session Management
    session_box = FancyBboxPatch((12.5, tools_y-0.4), 2.5, 0.8,
                                 boxstyle="round,pad=0.05",
                                 facecolor=colors['data'], alpha=0.7)
    ax.add_patch(session_box)
    ax.text(13.75, tools_y, '💾 Session Manager\n(JSON + SQLite)', 
            ha='center', va='center', fontsize=9, weight='bold', color='white')
    
    # 7. LLM Layer
    llm_box = FancyBboxPatch((6, 1.5), 4, 0.8,
                             boxstyle="round,pad=0.1",
                             facecolor=colors['ai'], alpha=0.8)
    ax.add_patch(llm_box)
    ax.text(8, 1.9, '🤖 Claude Sonnet 4\n(Language Model)', 
            ha='center', va='center', fontsize=11, weight='bold', color='white')
    
    # Bağlantı okları
    connections = [
        # User to Frontend
        ((2.5, 9.5), (8, 9.5)),
        # Frontend to Backend
        ((10, 10), (12, 10)),
        # Backend to Router
        ((13.5, 9.5), (8, 8.5)),
        # Router to Agents
        ((7, 7.5), (1, 6)),      # Product Search
        ((7.5, 7.5), (4, 6)),    # PDF Manual
        ((8, 7.5), (7, 6)),      # Technical Support
        ((8.5, 7.5), (10, 6)),   # General Info
        ((9, 7.5), (13, 6)),     # Quickstart
        # Agents to Tools
        ((1, 5), (1.75, 4)),     # Product Search to DB
        ((4, 5), (8, 4)),        # PDF Agent to PDF Tool
        ((7, 5), (8, 4)),        # Technical to PDF Tool
        ((10, 5), (8, 4)),       # General Info to PDF Tool
        ((13, 5), (8, 4)),       # Quickstart to PDF Tool
        ((13, 5), (13.75, 4)),   # Sessions
        # Tools to LLM
        ((8, 3), (8, 2.5))
    ]
    
    for start, end in connections:
        arrow = ConnectionPatch(start, end, "data", "data",
                                arrowstyle="->", shrinkA=5, shrinkB=5,
                                mutation_scale=20, fc="gray", alpha=0.6)
        ax.add_patch(arrow)
    
    # Data Flow Legend
    ax.text(14, 0.5, 'Data Flow: User Query → Router → Specialist Agent → Tools → LLM → Response', 
            fontsize=10, style='italic', ha='right')
    
    plt.tight_layout()
    plt.savefig('vestel_ai_architecture.png', dpi=300, bbox_inches='tight')
    plt.show()

# Diagramı oluştur
create_architecture_diagram()