"""
Test configuration and fixtures for MCP Market Index Server
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from typing import Dict, Any

from src.utils.cache import MarketDataCache
from src.api.client import KoreaInvestmentAPI
from src.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Create test settings"""
    return Settings(
        korea_investment_app_key="test_app_key",
        korea_investment_app_secret="test_app_secret",
        korea_investment_base_url="https://test.api.com",
        cache_ttl_seconds=5,
        cache_chart_ttl_seconds=30,
        cache_summary_ttl_seconds=10,
        max_requests_per_minute=100,
        max_retry_attempts=3,
        retry_delay_seconds=1.0,
        log_level="DEBUG",
        server_name="test-mcp-server",
        server_version="1.0.0-test",
        debug=True
    )


@pytest.fixture
def fresh_cache():
    """Create a fresh cache instance for each test"""
    cache = MarketDataCache()
    cache.invalidate()  # Ensure clean state
    return cache


@pytest.fixture
def mock_api_client():
    """Create a mock API client"""
    client = Mock(spec=KoreaInvestmentAPI)
    client.app_key = "test_key"
    client.app_secret = "test_secret"
    client.base_url = "https://test.api.com"
    client.access_token = "test_token"
    client.token_expires = datetime.now() + timedelta(hours=1)
    
    # Setup async methods
    client._get_access_token = AsyncMock(return_value="test_token")
    client.get_index_price = AsyncMock()
    client.get_index_chart_data = AsyncMock()
    client.get_sector_indices = AsyncMock()
    client.get_market_summary = AsyncMock()
    client.test_connection = AsyncMock()
    
    return client


@pytest.fixture
def sample_kospi_data():
    """Sample KOSPI index data"""
    return {
        "output": {
            "bstp_nmix_prpr": "2500.50",
            "bstp_nmix_prdy_vrss": "15.30",
            "prdy_vrss_sign": "2",
            "bstp_nmix_prdy_ctrt": "0.61",
            "acml_vol": "450000000",
            "acml_tr_pbmn": "8500000000000",
            "bstp_nmix_oprc": "2490.00",
            "bstp_nmix_hgpr": "2510.20",
            "bstp_nmix_lwpr": "2485.30"
        }
    }


@pytest.fixture
def sample_kosdaq_data():
    """Sample KOSDAQ index data"""
    return {
        "output": {
            "bstp_nmix_prpr": "850.25",
            "bstp_nmix_prdy_vrss": "-5.10",
            "prdy_vrss_sign": "5",
            "bstp_nmix_prdy_ctrt": "-0.60",
            "acml_vol": "850000000",
            "acml_tr_pbmn": "5200000000000",
            "bstp_nmix_oprc": "853.00",
            "bstp_nmix_hgpr": "855.00",
            "bstp_nmix_lwpr": "848.50"
        }
    }


@pytest.fixture
def sample_chart_data():
    """Sample chart data"""
    return {
        "output2": [
            {
                "stck_bsop_date": "20240110",
                "stck_oprc": "2490.00",
                "stck_hgpr": "2492.50",
                "stck_lwpr": "2488.00",
                "stck_clpr": "2491.20",
                "acml_vol": "15000000"
            },
            {
                "stck_bsop_date": "20240110",
                "stck_oprc": "2491.20",
                "stck_hgpr": "2495.00",
                "stck_lwpr": "2490.00",
                "stck_clpr": "2493.80",
                "acml_vol": "18000000"
            }
        ]
    }


@pytest.fixture
def sample_sector_data():
    """Sample sector indices data"""
    return {
        "output": [
            {
                "updn_issu_name": "반도체",
                "bstp_cls_code": "G2510",
                "bstp_nmix_prpr": "3250.50",
                "bstp_nmix_prdy_vrss": "45.20",
                "prdy_vrss_sign": "2",
                "bstp_nmix_prdy_ctrt": "1.41",
                "acml_vol": "25000000",
                "acml_tr_pbmn": "850000000000"
            },
            {
                "updn_issu_name": "은행",
                "bstp_cls_code": "G2710",
                "bstp_nmix_prpr": "850.30",
                "bstp_nmix_prdy_vrss": "-2.10",
                "prdy_vrss_sign": "5",
                "bstp_nmix_prdy_ctrt": "-0.25",
                "acml_vol": "8500000",
                "acml_tr_pbmn": "120000000000"
            }
        ]
    }


@pytest.fixture
def sample_market_summary():
    """Sample market summary data"""
    return {
        "kospi": {
            "output": {
                "up_cnt": "450",
                "down_cnt": "380",
                "unch_cnt": "95",
                "stop_cnt": "5",
                "uplmt_cnt": "12",
                "dnlmt_cnt": "3",
                "new_high_cnt": "8",
                "new_low_cnt": "2",
                "tot_askp_rsqn": "2100000000000000",
                "forn_hold_rsqn": "31.5"
            }
        },
        "kosdaq": {
            "output": {
                "up_cnt": "750",
                "down_cnt": "620",
                "unch_cnt": "180",
                "stop_cnt": "8",
                "uplmt_cnt": "25",
                "dnlmt_cnt": "5",
                "new_high_cnt": "15",
                "new_low_cnt": "7",
                "tot_askp_rsqn": "450000000000000",
                "forn_hold_rsqn": "8.2"
            }
        }
    }


@pytest.fixture
def all_market_data(sample_kospi_data, sample_kosdaq_data, sample_chart_data, 
                   sample_sector_data, sample_market_summary):
    """Complete market data for testing"""
    return {
        "kospi_index": sample_kospi_data,
        "kosdaq_index": sample_kosdaq_data,
        "chart_data": sample_chart_data,
        "sector_data": sample_sector_data,
        "market_summary": sample_market_summary
    }


class MockAPIResponse:
    """Mock API response helper"""
    
    def __init__(self, data: Dict[str, Any], status_code: int = 200):
        self.data = data
        self.status_code = status_code
    
    async def json(self):
        return self.data
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_http_session():
    """Mock HTTP session for API tests"""
    session = Mock()
    session.get = AsyncMock()
    session.post = AsyncMock()
    session.close = AsyncMock()
    
    async def mock_session_context():
        return session
    
    session.__aenter__ = mock_session_context
    session.__aexit__ = AsyncMock()
    
    return session


class APITestHelper:
    """Helper class for API testing"""
    
    @staticmethod
    def create_index_response(current: float, change: float, change_rate: float, 
                            volume: int, amount: int, open_price: float, 
                            high: float, low: float) -> Dict[str, Any]:
        """Create index API response"""
        sign = "2" if change > 0 else "5" if change < 0 else "3"
        return {
            "output": {
                "bstp_nmix_prpr": str(current),
                "bstp_nmix_prdy_vrss": str(change),
                "prdy_vrss_sign": sign,
                "bstp_nmix_prdy_ctrt": str(change_rate),
                "acml_vol": str(volume),
                "acml_tr_pbmn": str(amount),
                "bstp_nmix_oprc": str(open_price),
                "bstp_nmix_hgpr": str(high),
                "bstp_nmix_lwpr": str(low)
            }
        }
    
    @staticmethod
    def create_chart_response(data_points: list) -> Dict[str, Any]:
        """Create chart API response"""
        return {
            "output2": [
                {
                    "stck_bsop_date": point.get("date", "20240110"),
                    "stck_oprc": str(point["open"]),
                    "stck_hgpr": str(point["high"]),
                    "stck_lwpr": str(point["low"]),
                    "stck_clpr": str(point["close"]),
                    "acml_vol": str(point["volume"])
                }
                for point in data_points
            ]
        }
    
    @staticmethod
    def create_sector_response(sectors: list) -> Dict[str, Any]:
        """Create sector API response"""
        return {
            "output": [
                {
                    "updn_issu_name": sector["name"],
                    "bstp_cls_code": sector["code"],
                    "bstp_nmix_prpr": str(sector["current"]),
                    "bstp_nmix_prdy_vrss": str(sector["change"]),
                    "prdy_vrss_sign": "2" if sector["change"] > 0 else "5",
                    "bstp_nmix_prdy_ctrt": str(sector["change_rate"]),
                    "acml_vol": str(sector.get("volume", 0)),
                    "acml_tr_pbmn": str(sector.get("amount", 0))
                }
                for sector in sectors
            ]
        }


@pytest.fixture
def api_test_helper():
    """API test helper instance"""
    return APITestHelper()


class CacheTestHelper:
    """Helper class for cache testing"""
    
    @staticmethod
    async def wait_for_expiration(ttl: float):
        """Wait for cache expiration"""
        await asyncio.sleep(ttl + 0.1)
    
    @staticmethod
    def create_cache_entry(data: Any, ttl: int = 5) -> Dict[str, Any]:
        """Create cache entry"""
        return {
            "data": data,
            "expires": datetime.now() + timedelta(seconds=ttl)
        }


@pytest.fixture
def cache_test_helper():
    """Cache test helper instance"""
    return CacheTestHelper()


# Performance testing fixtures
@pytest.fixture
def performance_timer():
    """Performance timer fixture"""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
        
        def start(self):
            self.start_time = datetime.now()
        
        def stop(self):
            self.end_time = datetime.now()
        
        @property
        def elapsed(self) -> float:
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds()
            return 0.0
    
    return Timer()


# Error simulation fixtures
@pytest.fixture
def network_error():
    """Network error for testing"""
    return Exception("Network connection failed")


@pytest.fixture
def api_error():
    """API error for testing"""
    return Exception("API rate limit exceeded")


@pytest.fixture
def timeout_error():
    """Timeout error for testing"""
    return asyncio.TimeoutError("Request timed out")


# Test data generators
def generate_market_data(count: int = 100):
    """Generate market data for performance testing"""
    import random
    
    base_price = 2500.0
    data = []
    
    for i in range(count):
        change = random.uniform(-50, 50)
        current = base_price + change
        
        data.append({
            "current": current,
            "change": change,
            "change_rate": (change / base_price) * 100,
            "volume": random.randint(100000000, 1000000000),
            "amount": random.randint(1000000000000, 10000000000000),
            "open": base_price,
            "high": current + random.uniform(0, 20),
            "low": current - random.uniform(0, 20)
        })
    
    return data


@pytest.fixture
def large_market_dataset():
    """Large market dataset for performance testing"""
    return generate_market_data(1000)