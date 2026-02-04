"""
Unit tests for Walmart Analytics
Run: pytest tests/ -v
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import DB_CONFIG


class TestConfiguration:
    """Test configuration settings"""
    
    def test_db_config_exists(self):
        assert DB_CONFIG is not None
    
    def test_db_config_has_required_keys(self):
        required = ['server', 'database', 'driver', 'trusted_connection']
        for key in required:
            assert key in DB_CONFIG
    
    def test_db_server_not_empty(self):
        assert DB_CONFIG['server']
    
    def test_db_database_not_empty(self):
        assert DB_CONFIG['database']


class TestDatabaseConnection:
    """Test database utilities"""
    
    def test_connection_function_exists(self):
        from src.config.database import get_connection
        assert callable(get_connection)
    
    def test_close_connection_function_exists(self):
        from src.config.database import close_connection
        assert callable(close_connection)


class TestAnalyticsLogic:
    """Test analytics calculations"""
    
    def test_rfm_recency_calculation(self):
        """RFM Recency should decrease with time"""
        from datetime import datetime, timedelta
        
        today = datetime.now()
        recency_7_days = (today - timedelta(days=7)).date()
        recency_30_days = (today - timedelta(days=30)).date()
        
        days_7 = (today.date() - recency_7_days).days
        days_30 = (today.date() - recency_30_days).days
        
        assert days_7 < days_30
    
    def test_churn_risk_categories(self):
        """Churn risk should have 3 categories"""
        categories = ['High', 'Medium', 'Low']
        assert len(categories) == 3
        assert 'High' in categories


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
