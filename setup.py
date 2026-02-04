#!/usr/bin/env python
"""
WALMART ANALYTICS - Setup & Orchestration
Single consolidated script for database setup and initialization
"""

import pyodbc
import sys
import logging
from pathlib import Path
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration (from environment or defaults)
SERVER: str = 'localhost'
DATABASE: str = 'WalmartAnalytics'
DRIVER: str = '{ODBC Driver 17 for SQL Server}'


def get_connection(database: str = 'master') -> Optional[pyodbc.Connection]:
    """Get database connection with error handling"""
    try:
        conn_str = f'Driver={DRIVER};Server={SERVER};Database={database};Trusted_Connection=yes;'
        conn = pyodbc.connect(conn_str, autocommit=True)
        logger.info(f"Connected to {database}")
        return conn
    except pyodbc.Error as e:
        logger.error(f"Connection error: {e}")
        sys.exit(1)


def execute_sql_file(conn: pyodbc.Connection, filepath: Path) -> bool:
    """Execute SQL file with proper error handling"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        cursor = conn.cursor()
        
        # Split by GO statements
        batches = sql_content.split('\nGO\n')
        
        for batch in batches:
            batch = batch.strip()
            if batch:
                try:
                    cursor.execute(batch)
                except pyodbc.ProgrammingError as e:
                    # Ignore "already exists" errors
                    if 'already exists' not in str(e).lower():
                        raise
        
        logger.info(f"✅ {filepath.name} executed successfully")
        return True
    except Exception as e:
        logger.error(f"Error executing {filepath}: {e}")
        return False


def main() -> None:
    """Main orchestration"""
    logger.info("="*70)
    logger.info("WALMART ANALYTICS - DATABASE SETUP")
    logger.info("="*70)
    
    # Use master database for initial setup (includes DROP DATABASE)
    conn_master = get_connection('master')
    
    try:
        # Step 1: Initialize database schema & base data
        logger.info("Step 1: Creating schema and base data...")
        base_dir = Path(__file__).parent
        db_dir = base_dir / 'database'
        setup_sql = db_dir / '01_setup.sql'
        if not execute_sql_file(conn_master, setup_sql):
            raise Exception("Failed to create schema")
        
        conn_master.close()
        
        # Now connect to the newly created database
        conn = get_connection(DATABASE)
        
        # Step 2: Load customers & RFM
        logger.info("Step 2: Loading customers and RFM analysis...")
        customers_sql = db_dir / '02_customers.sql'
        if not execute_sql_file(conn, customers_sql):
            raise Exception("Failed to load customers")
        
        # Verify setup
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Customers")
        customer_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM CustomerRFM")
        rfm_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM CustomerChurnRisk")
        churn_count = cursor.fetchone()[0]
        
        logger.info(f"✅ Setup Complete!")
        logger.info(f"   • Customers: {customer_count}")
        logger.info(f"   • RFM Records: {rfm_count}")
        logger.info(f"   • Churn Risk Records: {churn_count}")
        
        logger.info("="*70)
        logger.info("Next steps:")
        logger.info("   1. Run: streamlit run src/analytics/dashboard.py")
        logger.info("   2. Open: http://localhost:8501")
        logger.info("="*70)
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            logger.info("Database connection closed")


if __name__ == '__main__':
    main()
