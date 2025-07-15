"""
Tests for MCP Tools
"""
import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.tools.index_tools import get_market_index, get_index_chart
from src.tools.market_tools import get_market_summary, get_sector_indices, get_market_compare
from src.utils.cache import MarketDataCache
from src.api.client import KoreaInvestmentAPI


class TestIndexTools:
    """Test cases for index tools"""
    
    @pytest.fixture
    def mock_cache(self):
        """Mock cache for testing"""
        return Mock(spec=MarketDataCache)
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client for testing"""
        return Mock(spec=KoreaInvestmentAPI)
    
    @pytest.fixture
    def mock_kospi_response(self):
        """Mock KOSPI API response"""
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
    def mock_kosdaq_response(self):
        """Mock KOSDAQ API response"""
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
    
    @pytest.mark.asyncio
    async def test_get_market_index_all(self, mock_cache, mock_api_client, 
                                      mock_kospi_response, mock_kosdaq_response):
        """Test getting all market indices"""
        # Setup cache to return None (cache miss)
        mock_cache.get_or_fetch = AsyncMock()
        mock_cache.get_or_fetch.side_effect = [
            mock_kospi_response,  # KOSPI response
            mock_kosdaq_response  # KOSDAQ response
        ]
        
        result = await get_market_index("ALL", mock_cache, mock_api_client)
        
        assert "timestamp" in result
        assert "kospi" in result
        assert "kosdaq" in result
        
        # Check KOSPI data
        kospi = result["kospi"]
        assert kospi["current"] == 2500.50
        assert kospi["change"] == 15.30
        assert kospi["change_rate"] == 0.61
        assert kospi["volume"] == 450000000
        
        # Check KOSDAQ data
        kosdaq = result["kosdaq"]
        assert kosdaq["current"] == 850.25
        assert kosdaq["change"] == -5.10
        assert kosdaq["change_rate"] == -0.60
        assert kosdaq["volume"] == 850000000
    
    @pytest.mark.asyncio
    async def test_get_market_index_kospi_only(self, mock_cache, mock_api_client, mock_kospi_response):
        """Test getting KOSPI index only"""
        mock_cache.get_or_fetch = AsyncMock(return_value=mock_kospi_response)
        
        result = await get_market_index("KOSPI", mock_cache, mock_api_client)
        
        assert "timestamp" in result
        assert "kospi" in result
        assert "kosdaq" not in result
        
        kospi = result["kospi"]
        assert kospi["current"] == 2500.50
        assert kospi["change"] == 15.30
    
    @pytest.mark.asyncio
    async def test_get_market_index_kosdaq_only(self, mock_cache, mock_api_client, mock_kosdaq_response):
        """Test getting KOSDAQ index only"""
        mock_cache.get_or_fetch = AsyncMock(return_value=mock_kosdaq_response)
        
        result = await get_market_index("KOSDAQ", mock_cache, mock_api_client)
        
        assert "timestamp" in result
        assert "kosdaq" in result
        assert "kospi" not in result
        
        kosdaq = result["kosdaq"]
        assert kosdaq["current"] == 850.25
        assert kosdaq["change"] == -5.10
    
    @pytest.mark.asyncio
    async def test_get_market_index_invalid_market(self, mock_cache, mock_api_client):
        """Test error handling for invalid market"""
        with pytest.raises(ValueError) as excinfo:
            await get_market_index("INVALID", mock_cache, mock_api_client)
        
        assert "Invalid market" in str(excinfo.value)
    
    @pytest.mark.asyncio
    async def test_get_index_chart(self, mock_cache, mock_api_client):
        """Test getting index chart data"""
        mock_chart_response = {
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
        
        mock_cache.get_or_fetch = AsyncMock(return_value=mock_chart_response)
        
        result = await get_index_chart(
            market="KOSPI",
            period="1D",
            interval="5m",
            cache=mock_cache,
            api_client=mock_api_client
        )
        
        assert result["market"] == "KOSPI"
        assert result["period"] == "1D"
        assert result["interval"] == "5m"
        assert len(result["data"]) == 2
        
        # Check first data point
        first_point = result["data"][0]
        assert first_point["open"] == 2490.00
        assert first_point["high"] == 2492.50
        assert first_point["low"] == 2488.00
        assert first_point["close"] == 2491.20
        assert first_point["volume"] == 15000000
    
    @pytest.mark.asyncio
    async def test_get_index_chart_invalid_market(self, mock_cache, mock_api_client):
        """Test error handling for invalid market in chart"""
        with pytest.raises(ValueError):
            await get_index_chart(
                market="INVALID",
                period="1D",
                interval="5m",
                cache=mock_cache,
                api_client=mock_api_client
            )
    
    @pytest.mark.asyncio
    async def test_get_index_chart_invalid_period(self, mock_cache, mock_api_client):
        """Test error handling for invalid period"""
        with pytest.raises(ValueError):
            await get_index_chart(
                market="KOSPI",
                period="INVALID",
                interval="5m",
                cache=mock_cache,
                api_client=mock_api_client
            )
    
    @pytest.mark.asyncio
    async def test_get_index_chart_invalid_interval(self, mock_cache, mock_api_client):
        """Test error handling for invalid interval"""
        with pytest.raises(ValueError):
            await get_index_chart(
                market="KOSPI",
                period="1D",
                interval="INVALID",
                cache=mock_cache,
                api_client=mock_api_client
            )


class TestMarketTools:
    """Test cases for market tools"""
    
    @pytest.fixture
    def mock_cache(self):
        """Mock cache for testing"""
        return Mock(spec=MarketDataCache)
    
    @pytest.fixture
    def mock_api_client(self):
        """Mock API client for testing"""
        return Mock(spec=KoreaInvestmentAPI)
    
    @pytest.fixture
    def mock_market_summary_response(self):
        """Mock market summary API response"""
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
    def mock_sector_response(self):
        """Mock sector indices API response"""
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
    
    @pytest.mark.asyncio
    async def test_get_market_summary(self, mock_cache, mock_api_client, mock_market_summary_response):
        """Test getting market summary"""
        mock_cache.get_or_fetch = AsyncMock(return_value=mock_market_summary_response)
        
        result = await get_market_summary(mock_cache, mock_api_client)
        
        assert "timestamp" in result
        assert "kospi" in result
        assert "kosdaq" in result
        
        # Check KOSPI summary
        kospi = result["kospi"]
        assert kospi["advancing"] == 450
        assert kospi["declining"] == 380
        assert kospi["unchanged"] == 95
        assert kospi["trading_halt"] == 5
        assert kospi["limit_up"] == 12
        assert kospi["limit_down"] == 3
        assert kospi["new_high_52w"] == 8
        assert kospi["new_low_52w"] == 2
        assert kospi["market_cap"] == 2100000000000000
        assert kospi["foreign_ownership_rate"] == 31.5
        
        # Check KOSDAQ summary
        kosdaq = result["kosdaq"]
        assert kosdaq["advancing"] == 750
        assert kosdaq["declining"] == 620
        assert kosdaq["unchanged"] == 180
    
    @pytest.mark.asyncio
    async def test_get_sector_indices_kospi(self, mock_cache, mock_api_client, mock_sector_response):
        """Test getting KOSPI sector indices"""
        mock_cache.get_or_fetch = AsyncMock(return_value=mock_sector_response)
        
        result = await get_sector_indices("KOSPI", mock_cache, mock_api_client)
        
        assert result["market"] == "KOSPI"
        assert "timestamp" in result
        assert "sectors" in result
        assert len(result["sectors"]) == 2
        
        # Check first sector
        semiconductor = result["sectors"][0]
        assert semiconductor["name"] == "반도체"
        assert semiconductor["code"] == "G2510"
        assert semiconductor["current"] == 3250.50
        assert semiconductor["change"] == 45.20
        assert semiconductor["change_rate"] == 1.41
        assert semiconductor["volume"] == 25000000
        assert semiconductor["amount"] == 850000000000
        
        # Check second sector
        bank = result["sectors"][1]
        assert bank["name"] == "은행"
        assert bank["code"] == "G2710"
        assert bank["current"] == 850.30
        assert bank["change"] == -2.10
        assert bank["change_rate"] == -0.25
    
    @pytest.mark.asyncio
    async def test_get_sector_indices_kosdaq(self, mock_cache, mock_api_client, mock_sector_response):
        """Test getting KOSDAQ sector indices"""
        mock_cache.get_or_fetch = AsyncMock(return_value=mock_sector_response)
        
        result = await get_sector_indices("KOSDAQ", mock_cache, mock_api_client)
        
        assert result["market"] == "KOSDAQ"
        assert "sectors" in result
    
    @pytest.mark.asyncio
    async def test_get_sector_indices_invalid_market(self, mock_cache, mock_api_client):
        """Test error handling for invalid market in sector indices"""
        with pytest.raises(ValueError):
            await get_sector_indices("INVALID", mock_cache, mock_api_client)
    
    @pytest.mark.asyncio
    async def test_get_market_compare_with_dates(self, mock_cache, mock_api_client):
        """Test market comparison with specific dates"""
        mock_compare_response = {
            "kospi": {
                "start_data": {
                    "bstp_nmix_prpr": "2450.00"
                },
                "end_data": {
                    "bstp_nmix_prpr": "2500.50"
                },
                "stats": {
                    "high_price": "2520.00",
                    "low_price": "2440.00",
                    "avg_volume": "380000000",
                    "avg_amount": "7500000000000"
                }
            },
            "kosdaq": {
                "start_data": {
                    "bstp_nmix_prpr": "830.00"
                },
                "end_data": {
                    "bstp_nmix_prpr": "850.25"
                },
                "stats": {
                    "high_price": "865.00",
                    "low_price": "825.50",
                    "avg_volume": "750000000",
                    "avg_amount": "4800000000000"
                }
            }
        }
        
        mock_cache.get_or_fetch = AsyncMock(return_value=mock_compare_response)
        
        result = await get_market_compare(
            date_from="2024-01-01",
            date_to="2024-01-10",
            cache=mock_cache,
            api_client=mock_api_client
        )
        
        assert result["period"]["from"] == "2024-01-01"
        assert result["period"]["to"] == "2024-01-10"
        
        # Check KOSPI comparison
        kospi = result["kospi"]
        assert kospi["start"] == 2450.00
        assert kospi["end"] == 2500.50
        assert kospi["change"] == 50.50
        assert abs(kospi["change_rate"] - 2.06) < 0.01
        assert kospi["high"] == 2520.00
        assert kospi["low"] == 2440.00
        
        # Check KOSDAQ comparison
        kosdaq = result["kosdaq"]
        assert kosdaq["start"] == 830.00
        assert kosdaq["end"] == 850.25
        assert kosdaq["change"] == 20.25
        assert abs(kosdaq["change_rate"] - 2.44) < 0.01
    
    @pytest.mark.asyncio
    async def test_get_market_compare_without_dates(self, mock_cache, mock_api_client):
        """Test market comparison without specific dates (default period)"""
        mock_compare_response = {
            "kospi": {
                "start_data": {"bstp_nmix_prpr": "2490.00"},
                "end_data": {"bstp_nmix_prpr": "2500.50"},
                "stats": {
                    "high_price": "2510.00",
                    "low_price": "2485.00",
                    "avg_volume": "400000000",
                    "avg_amount": "8000000000000"
                }
            },
            "kosdaq": {
                "start_data": {"bstp_nmix_prpr": "845.00"},
                "end_data": {"bstp_nmix_prpr": "850.25"},
                "stats": {
                    "high_price": "855.00",
                    "low_price": "840.00",
                    "avg_volume": "800000000",
                    "avg_amount": "5000000000000"
                }
            }
        }
        
        mock_cache.get_or_fetch = AsyncMock(return_value=mock_compare_response)
        
        result = await get_market_compare(
            date_from=None,
            date_to=None,
            cache=mock_cache,
            api_client=mock_api_client
        )
        
        assert "period" in result
        assert "kospi" in result
        assert "kosdaq" in result
    
    @pytest.mark.asyncio
    async def test_get_market_compare_invalid_date_format(self, mock_cache, mock_api_client):
        """Test error handling for invalid date format"""
        with pytest.raises(ValueError):
            await get_market_compare(
                date_from="invalid-date",
                date_to="2024-01-10",
                cache=mock_cache,
                api_client=mock_api_client
            )
    
    @pytest.mark.asyncio
    async def test_api_error_handling_in_tools(self, mock_cache, mock_api_client):
        """Test error handling when API calls fail"""
        mock_cache.get_or_fetch = AsyncMock(side_effect=Exception("API Error"))
        
        with pytest.raises(Exception):
            await get_market_index("KOSPI", mock_cache, mock_api_client)
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self, mock_cache, mock_api_client, mock_kospi_response):
        """Test that cache keys are generated correctly"""
        mock_cache.get_or_fetch = AsyncMock(return_value=mock_kospi_response)
        
        await get_market_index("KOSPI", mock_cache, mock_api_client)
        
        # Verify cache was called with correct key
        mock_cache.get_or_fetch.assert_called()
        call_args = mock_cache.get_or_fetch.call_args[0]
        assert "market_index" in call_args[0]  # Cache key should contain 'market_index'
        assert "KOSPI" in call_args[0]  # Cache key should contain market name