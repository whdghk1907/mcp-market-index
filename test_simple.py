"""
Simple test to verify our implementation
"""
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.api.models import IndexData, ChartData, ChartPoint
from src.api.client import KoreaInvestmentAPI
from src.utils.cache import MarketDataCache
from src.utils.retry import retry_on_error, APIError


async def test_models():
    """Test data models"""
    print("Testing data models...")
    
    # Test IndexData
    index = IndexData(
        current=2500.50,
        change=15.30,
        change_rate=0.61,
        volume=450000000,
        amount=8500000000000,
        high=2510.20,
        low=2485.30,
        open=2490.00
    )
    assert index.current == 2500.50
    print("✓ IndexData model works")
    
    # Test ChartPoint and ChartData
    point = ChartPoint(
        timestamp=datetime.now(),
        open=2490.00,
        high=2492.50,
        low=2488.00,
        close=2491.20,
        volume=15000000
    )
    
    chart = ChartData(
        market="KOSPI",
        period="1D",
        interval="5m",
        data=[point]
    )
    assert chart.market == "KOSPI"
    assert len(chart.data) == 1
    print("✓ ChartData model works")


async def test_cache():
    """Test cache system"""
    print("\nTesting cache system...")
    
    cache = MarketDataCache()
    
    # Test cache miss and fetch
    call_count = 0
    async def fetch_func():
        nonlocal call_count
        call_count += 1
        return {"data": "test"}
    
    result1 = await cache.get_or_fetch("test_key", fetch_func, ttl=5)
    assert result1["data"] == "test"
    assert call_count == 1
    print("✓ Cache miss triggers fetch")
    
    # Test cache hit
    result2 = await cache.get_or_fetch("test_key", fetch_func, ttl=5)
    assert result2["data"] == "test"
    assert call_count == 1  # No additional fetch
    print("✓ Cache hit returns cached data")


async def test_retry():
    """Test retry logic"""
    print("\nTesting retry logic...")
    
    call_count = 0
    
    @retry_on_error(max_attempts=3, delay=0.1)
    async def test_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise APIError("Test error")
        return "success"
    
    result = await test_func()
    assert result == "success"
    assert call_count == 3
    print("✓ Retry logic works correctly")


async def test_api_client():
    """Test API client initialization"""
    print("\nTesting API client...")
    
    client = KoreaInvestmentAPI(
        app_key="test_key",
        app_secret="test_secret"
    )
    
    assert client.app_key == "test_key"
    assert client.app_secret == "test_secret"
    assert client.base_url is not None
    print("✓ API client initialization works")


async def test_tools():
    """Test MCP tools basic functionality"""
    print("\nTesting MCP tools...")
    
    # Create mocks
    cache = MarketDataCache()
    api_client = Mock(spec=KoreaInvestmentAPI)
    
    # Mock API response
    api_client.get_index_price = AsyncMock(return_value={
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
    })
    
    # Test get_market_index
    from src.tools.index_tools import get_market_index
    
    result = await get_market_index("KOSPI", cache, api_client)
    assert "timestamp" in result
    assert "kospi" in result
    assert result["kospi"]["current"] == 2500.50
    print("✓ get_market_index tool works")


async def main():
    """Run all tests"""
    print("Running Phase 2 implementation tests...\n")
    
    try:
        await test_models()
        await test_cache()
        await test_retry()
        await test_api_client()
        await test_tools()
        
        print("\n✅ All tests passed! Phase 2 implementation is working correctly.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())