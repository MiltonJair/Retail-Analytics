"""
Database connection utilities for Walmart Analytics
"""

import pyodbc
import logging
from typing import Optional
from src.config.settings import DB_CONFIG

logger = logging.getLogger(__name__)


def get_connection(database: str = None) -> Optional[pyodbc.Connection]:
    """
    Get database connection with proper error handling.
    
    Args:
        database: Database name (uses SQL_DATABASE from settings if None)
    
    Returns:
        pyodbc.Connection or None if connection fails
    """
    try:
        db = database or DB_CONFIG['database']
        conn_str = (
            f"Driver={DB_CONFIG['driver']};"
            f"Server={DB_CONFIG['server']};"
            f"Database={db};"
            "Trusted_Connection=yes;"
        )
        conn = pyodbc.connect(conn_str)
        logger.info(f"Connected to {db}")
        return conn
    except pyodbc.Error as e:
        logger.error(f"Database connection failed: {e}")
        return None


def close_connection(conn: Optional[pyodbc.Connection]) -> None:
    """Close database connection safely."""
    if conn:
        try:
            conn.close()
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
