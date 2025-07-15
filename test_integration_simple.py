"""
Simple integration test for MCP server
"""
import asyncio
from unittest.mock import AsyncMock, Mock

from src.server import server
from src.api.client import KoreaInvestmentAPI
from src.utils.cache import MarketDataCache


async def test_server_tools():
    """Test server tool listing"""
    print("Testing MCP server tool listing...")
    
    tools = await server.list_tools()
    tool_names = [tool.name for tool in tools]
    
    expected_tools = [
        "get_market_index",
        "get_index_chart",
        "get_market_summary", 
        "get_sector_indices",
        "get_market_compare"
    ]
    
    print(f"Found tools: {tool_names}")
    
    for expected_tool in expected_tools:
        assert expected_tool in tool_names, f"Missing tool: {expected_tool}"
    
    print("✓ All expected tools are available")


async def test_market_index_tool():
    """Test get_market_index tool with mocked data"""
    print("\nTesting get_market_index tool...")
    
    # Mock the API client and cache in the server module
    import src.server as server_module
    
    # Save original instances
    original_api_client = server_module.api_client
    original_cache = server_module.cache
    
    try:
        # Create mock API client
        mock_api_client = Mock(spec=KoreaInvestmentAPI)
        mock_api_client.get_index_price = AsyncMock(return_value={
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
        
        # Create real cache
        mock_cache = MarketDataCache()
        mock_cache.invalidate()  # Start fresh
        
        # Replace instances
        server_module.api_client = mock_api_client
        server_module.cache = mock_cache
        
        # Call the tool
        result = await server.call_tool("get_market_index", {"market": "KOSPI"})
        
        print(f"Tool result type: {type(result)}")
        print(f"Tool result length: {len(result)}")
        
        assert len(result) == 1
        result_text = result[0].text
        print(f"Result preview: {result_text[:100]}...")
        
        # Parse result (in real scenario would use json.loads)
        result_data = eval(result_text)
        
        assert "timestamp" in result_data
        assert "kospi" in result_data
        assert result_data["kospi"]["current"] == 2500.50
        
        print("✓ get_market_index tool works correctly")
        
    finally:
        # Restore original instances
        server_module.api_client = original_api_client
        server_module.cache = original_cache


async def test_error_handling():
    """Test error handling in tools"""
    print("\nTesting error handling...")
    
    # Test with invalid tool name
    result = await server.call_tool("invalid_tool", {})
    
    assert len(result) == 1
    assert "Error" in result[0].text
    assert "Unknown tool" in result[0].text
    
    print("✓ Error handling works correctly")


async def main():
    """Run integration tests"""
    print("Running MCP Server Integration Tests...\n")
    
    try:
        await test_server_tools()
        await test_market_index_tool()
        await test_error_handling()
        
        print("\n✅ All integration tests passed!")
        print("Phase 2 implementation is complete and working correctly.")
        
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())