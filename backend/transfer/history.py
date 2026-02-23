"""
SQLite Database for persisting Transfer History.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime
from config import DEFAULT_SAVE_DIR
import os

logger = logging.getLogger(__name__)

class TransferHistoryDB:
    def __init__(self, db_filename: str = "transfer_history.db"):
        os.makedirs(DEFAULT_SAVE_DIR, exist_ok=True)
        self.db_path = os.path.join(DEFAULT_SAVE_DIR, db_filename)
        self._init_db()

    def _init_db(self):
        """Creates the history table if it doesn't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transfers (
                        id TEXT PRIMARY KEY,
                        file_name TEXT,
                        file_size INTEGER,
                        peer_name TEXT,
                        direction TEXT,
                        status TEXT,
                        timestamp DATETIME
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize transfer history DB: {e}")

    def add_transfer(self, transfer_id: str, file_name: str, file_size: int, peer_name: str, direction: str, status: str):
        """Adds a new transfer record."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO transfers (id, file_name, file_size, peer_name, direction, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (transfer_id, file_name, file_size, peer_name, direction, status, datetime.now().isoformat()))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to add transfer history: {e}")

    def update_status(self, transfer_id: str, new_status: str):
        """Updates the status of an existing transfer."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE transfers SET status = ? WHERE id = ?
                """, (new_status, transfer_id))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update transfer history status: {e}")

    def get_history(self, limit: int = 50) -> list[dict]:
        """Retrieves recent transfer history."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM transfers ORDER BY timestamp DESC LIMIT ?
                """, (limit,))
                rows = cursor.fetchall()
                # Convert sqlite3.Row to dict
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch transfer history: {e}")
            return []
