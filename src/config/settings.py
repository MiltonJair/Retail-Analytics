"""
Configuración centralizada para Walmart Analytics
"""

import os
from pathlib import Path

# Rutas base
BASE_DIR = Path(__file__).resolve().parent.parent.parent
SRC_DIR = BASE_DIR / 'src'
DOCS_DIR = BASE_DIR / 'docs'
DATABASE_DIR = BASE_DIR / 'database'

# SQL Server Configuration
SQL_SERVER = os.getenv('SQL_SERVER', 'localhost')
SQL_DATABASE = os.getenv('SQL_DATABASE', 'WalmartAnalytics')
SQL_DRIVER = os.getenv('SQL_DRIVER', 'ODBC Driver 17 for SQL Server')
SQL_TRUSTED_CONNECTION = os.getenv('SQL_TRUSTED_CONNECTION', 'yes').lower() == 'yes'

# Database connection configuration
DB_CONFIG = {
    'server': SQL_SERVER,
    'database': SQL_DATABASE,
    'driver': SQL_DRIVER,
    'trusted_connection': SQL_TRUSTED_CONNECTION
}

# Application settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

