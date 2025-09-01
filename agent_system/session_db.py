"""
Session Database Management
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from agent_system.config import DATABASE_PATH

class SessionDB:
    """Session metadata veritabanı yöneticisi"""
    
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_db()
    
    def init_db(self):
        """Session tablosunu oluştur"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    session_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_activity TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    product_count INTEGER DEFAULT 0,
                    metadata TEXT DEFAULT '{}',
                    is_active INTEGER DEFAULT 1
                )
            """)
            conn.commit()
    
    def create_session(self, session_id: str, session_name: str = None) -> str:
        """Yeni session oluştur"""
        if not session_name:
            session_name = f"Chat {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions 
                (session_id, session_name, created_at, last_activity)
                VALUES (?, ?, ?, ?)
            """, (session_id, session_name, datetime.now().isoformat(), datetime.now().isoformat()))
            conn.commit()
        
        return session_id
    
    def update_session_activity(self, session_id: str, message_count: int = None, product_count: int = None, last_activity: str = None):
        """Session aktivitesini güncelle"""
        with sqlite3.connect(self.db_path) as conn:
            activity_time = last_activity or datetime.now().isoformat()
            
            if message_count is not None and product_count is not None:
                conn.execute("""
                    UPDATE sessions 
                    SET last_activity = ?, message_count = ?, product_count = ?
                    WHERE session_id = ?
                """, (activity_time, message_count, product_count, session_id))
            else:
                conn.execute("""
                    UPDATE sessions 
                    SET last_activity = ?
                    WHERE session_id = ?
                """, (activity_time, session_id))
            conn.commit()
    
    def rename_session(self, session_id: str, new_name: str) -> bool:
        """Session adını değiştir"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE sessions 
                SET session_name = ?
                WHERE session_id = ?
            """, (new_name, session_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Session bilgilerini al"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM sessions WHERE session_id = ?
            """, (session_id,))
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def list_all_sessions(self) -> List[Dict]:
        """Tüm session'ları listele"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM sessions 
                ORDER BY last_activity DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_session(self, session_id: str) -> bool:
        """Session'ı sil"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM sessions WHERE session_id = ?
            """, (session_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def archive_session(self, session_id: str) -> bool:
        """Session'ı arşivle"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE sessions 
                SET is_active = 0
                WHERE session_id = ?
            """, (session_id,))
            conn.commit()
            return cursor.rowcount > 0

# Global instance
session_db = SessionDB()
