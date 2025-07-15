"""
Integration Tests for MCP Market Index Server
"""
import pytest
import asyncio
import json
from unittest.mock import patch, AsyncMock
from datetime import datetime

from src.server import server, cache, api_client
from src.config import get_settings
from mcp.types import TextContent


class TestMCPServerIntegration:
    """Integration tests for MCP server"""
    
    @pytest.fixture
    def settings(self):
        """Get test settings"""
        return get_settings()
    
    @pytest.fixture
    def mock_api_responses(self):
        """Mock API responses for integration tests"""
        return {
            "kospi_index": {
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
            },
            "kosdaq_index": {
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
            },
            "chart_data": {
                "output2": [
                    {
                        "stck_bsop_date": "20240110",
                        "stck_oprc": "2490.00",
                        "stck_hgpr": "2492.50",
                        "stck_lwpr": "2488.00",
                        "stck_clpr": "2491.20",
                        "acml_vol": "15000000"
                    }
                ]
            },
            "market_summary": {
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
            },
            "sector_data": {
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
                    }
                ]
            }
        }
    
    @pytest.mark.asyncio
    async def test_server_tool_listing(self):
        """Test that server lists all expected tools"""
        tools = await server.list_tools()
        
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "get_market_index",
            "get_index_chart", 
            "get_market_summary",
            "get_sector_indices",
            "get_market_compare"
        ]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names
    
    @pytest.mark.asyncio
    async def test_get_market_index_tool_integration(self, mock_api_responses):
        """Test get_market_index tool end-to-end"""
        with patch.object(api_client, 'get_index_price') as mock_get_index:
            mock_get_index.side_effect = [
                mock_api_responses["kospi_index"],
                mock_api_responses["kosdaq_index"]
            ]
            
            # Clear cache before test
            cache.invalidate()
            
            result = await server.call_tool("get_market_index", {"market": "ALL"})
            
            assert len(result) == 1
            assert isinstance(result[0], TextContent)
            
            # Parse the result
            result_data = eval(result[0].text)  # In real scenario, would use json.loads
            
            assert "timestamp" in result_data
            assert "kospi" in result_data
            assert "kosdaq" in result_data
            assert result_data["kospi"]["current"] == 2500.50
            assert result_data["kosdaq"]["current"] == 850.25
    
    @pytest.mark.asyncio
    async def test_get_index_chart_tool_integration(self, mock_api_responses):
        """Test get_index_chart tool end-to-end"""
        with patch.object(api_client, 'get_index_chart_data') as mock_get_chart:
            mock_get_chart.return_value = mock_api_responses["chart_data"]
            
            cache.invalidate()
            
            result = await server.call_tool("get_index_chart", {
                "market": "KOSPI",
                "period": "1D",
                "interval": "5m"
            })
            
            assert len(result) == 1
            result_data = eval(result[0].text)
            
            assert result_data["market"] == "KOSPI"
            assert result_data["period"] == "1D"
            assert result_data["interval"] == "5m"
            assert len(result_data["data"]) == 1
            assert result_data["data"][0]["open"] == 2490.00
    
    @pytest.mark.asyncio
    async def test_get_market_summary_tool_integration(self, mock_api_responses):
        """Test get_market_summary tool end-to-end"""
        with patch.object(api_client, 'get_market_summary') as mock_get_summary:
            mock_get_summary.return_value = mock_api_responses["market_summary"]
            
            cache.invalidate()
            
            result = await server.call_tool("get_market_summary", {})
            
            assert len(result) == 1
            result_data = eval(result[0].text)
            
            assert "timestamp" in result_data
            assert "kospi" in result_data
            assert "kosdaq" in result_data
            assert result_data["kospi"]["advancing"] == 450
            assert result_data["kosdaq"]["advancing"] == 750
    
    @pytest.mark.asyncio
    async def test_get_sector_indices_tool_integration(self, mock_api_responses):
        """Test get_sector_indices tool end-to-end"""
        with patch.object(api_client, 'get_sector_indices') as mock_get_sectors:
            mock_get_sectors.return_value = mock_api_responses["sector_data"]
            
            cache.invalidate()
            
            result = await server.call_tool("get_sector_indices", {"market": "KOSPI"})
            
            assert len(result) == 1
            result_data = eval(result[0].text)
            
            assert result_data["market"] == "KOSPI"
            assert "timestamp" in result_data
            assert "sectors" in result_data
            assert len(result_data["sectors"]) == 1
            assert result_data["sectors"][0]["name"] == "반도체"
    
    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test error handling in tool calls"""
        # Test with invalid tool name
        result = await server.call_tool("invalid_tool", {})
        
        assert len(result) == 1
        assert "Error" in result[0].text
        assert "Unknown tool" in result[0].text
    
    @pytest.mark.asyncio
    async def test_tool_parameter_validation(self):
        """Test parameter validation in tools"""
        # Test get_market_index with invalid market
        result = await server.call_tool("get_market_index", {"market": "INVALID"})
        
        assert len(result) == 1
        assert "Error" in result[0].text
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, mock_api_responses):
        """Test cache integration across multiple calls"""
        with patch.object(api_client, 'get_index_price') as mock_get_index:
            mock_get_index.return_value = mock_api_responses["kospi_index"]
            
            cache.invalidate()
            
            # First call - should hit API
            result1 = await server.call_tool("get_market_index", {"market": "KOSPI"})
            assert mock_get_index.call_count == 1
            
            # Second call immediately - should hit cache
            result2 = await server.call_tool("get_market_index", {"market": "KOSPI"})
            assert mock_get_index.call_count == 1  # No additional API call
            
            # Results should be the same
            assert result1[0].text == result2[0].text
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_calls(self, mock_api_responses):
        """Test concurrent tool calls don't interfere"""
        with patch.object(api_client, 'get_index_price') as mock_get_index:
            mock_get_index.side_effect = [
                mock_api_responses["kospi_index"],
                mock_api_responses["kosdaq_index"]
            ]
            
            cache.invalidate()
            
            # Make concurrent calls for different markets
            tasks = [
                server.call_tool("get_market_index", {"market": "KOSPI"}),
                server.call_tool("get_market_index", {"market": "KOSDAQ"})
            ]
            
            results = await asyncio.gather(*tasks)
            
            assert len(results) == 2
            assert len(results[0]) == 1
            assert len(results[1]) == 1
            
            # Parse results
            kospi_result = eval(results[0][0].text)
            kosdaq_result = eval(results[1][0].text)
            
            assert "kospi" in kospi_result
            assert "kosdaq" in kosdaq_result
            assert kospi_result["kospi"]["current"] == 2500.50
            assert kosdaq_result["kosdaq"]["current"] == 850.25


class TestAPIClientIntegration:
    """Integration tests for API client"""
    
    @pytest.mark.asyncio
    async def test_api_client_initialization(self):
        """Test API client initialization"""
        assert api_client.app_key is not None
        assert api_client.app_secret is not None
        assert api_client.base_url is not None
    
    @pytest.mark.asyncio
    async def test_token_management_integration(self):
        """Test token management in real scenario"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "access_token": "test_token",
                "expires_in": 3600,
                "token_type": "Bearer"
            }
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # First token request
            token1 = await api_client._get_access_token()
            assert token1 == "test_token"
            
            # Second request should use cached token
            token2 = await api_client._get_access_token()
            assert token2 == "test_token"
            assert mock_post.call_count == 1  # Only one API call


class TestCacheIntegration:
    """Integration tests for cache system"""
    
    @pytest.mark.asyncio
    async def test_cache_with_real_data_flow(self):
        """Test cache with realistic data flow"""
        test_cache = cache
        test_cache.invalidate()  # Start fresh
        
        call_count = 0
        
        async def mock_fetch():
            nonlocal call_count
            call_count += 1
            return {"data": f"call_{call_count}", "timestamp": datetime.now().isoformat()}
        
        # First call
        result1 = await test_cache.get_or_fetch("test_key", mock_fetch, ttl=2)
        assert call_count == 1
        assert result1["data"] == "call_1"
        
        # Second call (cached)
        result2 = await test_cache.get_or_fetch("test_key", mock_fetch, ttl=2)
        assert call_count == 1
        assert result2["data"] == "call_1"
        
        # Wait for expiration
        await asyncio.sleep(2.1)
        
        # Third call (expired, new fetch)
        result3 = await test_cache.get_or_fetch("test_key", mock_fetch, ttl=2)
        assert call_count == 2
        assert result3["data"] == "call_2"
    
    def test_cache_stats_integration(self):
        """Test cache statistics in realistic scenario"""
        test_cache = cache
        test_cache.invalidate()
        
        # Add some data
        test_cache.set("key1", {"data": "value1"}, ttl=10)
        test_cache.set("key2", {"data": "value2"}, ttl=0)  # Expired
        test_cache.set("key3", {"data": "value3"}, ttl=10)
        
        stats = test_cache.get_stats()
        
        assert stats["total_keys"] == 3
        assert stats["valid_keys"] == 2
        assert stats["expired_keys"] == 1
        assert stats["memory_usage"] > 0


class TestEndToEndWorkflows:
    """End-to-end workflow tests"""
    
    @pytest.mark.asyncio
    async def test_market_data_workflow(self, mock_api_responses):
        """Test complete market data retrieval workflow"""
        with patch.object(api_client, 'get_index_price') as mock_get_index, \
             patch.object(api_client, 'get_market_summary') as mock_get_summary, \
             patch.object(api_client, 'get_sector_indices') as mock_get_sectors:
            
            mock_get_index.side_effect = [
                mock_api_responses["kospi_index"],
                mock_api_responses["kosdaq_index"]
            ]
            mock_get_summary.return_value = mock_api_responses["market_summary"]
            mock_get_sectors.return_value = mock_api_responses["sector_data"]
            
            cache.invalidate()
            
            # Step 1: Get market indices
            indices_result = await server.call_tool("get_market_index", {"market": "ALL"})
            indices_data = eval(indices_result[0].text)
            
            # Step 2: Get market summary
            summary_result = await server.call_tool("get_market_summary", {})
            summary_data = eval(summary_result[0].text)
            
            # Step 3: Get sector indices
            sectors_result = await server.call_tool("get_sector_indices", {"market": "KOSPI"})
            sectors_data = eval(sectors_result[0].text)
            
            # Verify complete workflow
            assert "kospi" in indices_data
            assert "kosdaq" in indices_data
            assert "kospi" in summary_data
            assert "kosdaq" in summary_data
            assert sectors_data["market"] == "KOSPI"
            assert len(sectors_data["sectors"]) > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self):
        """Test error recovery in workflow"""
        with patch.object(api_client, 'get_index_price') as mock_get_index:
            # First call fails
            mock_get_index.side_effect = Exception("Network error")
            
            cache.invalidate()
            
            result = await server.call_tool("get_market_index", {"market": "KOSPI"})
            assert "Error" in result[0].text
            
            # Second call succeeds
            mock_get_index.side_effect = None
            mock_get_index.return_value = {
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
            
            result = await server.call_tool("get_market_index", {"market": "KOSPI"})
            result_data = eval(result[0].text)
            
            assert "kospi" in result_data
            assert result_data["kospi"]["current"] == 2500.50