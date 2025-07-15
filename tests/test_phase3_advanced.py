"""
Phase 3 Advanced Features Tests - TDD Style
These tests define the advanced features we need to implement
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta
import json

from src.tools.index_tools import get_market_index, get_index_chart
from src.tools.market_tools import get_market_summary, get_sector_indices, get_market_compare
from src.utils.cache import MarketDataCache
from src.api.client import KoreaInvestmentAPI


class TestAdvancedDataProcessing:
    """Test advanced data processing features"""
    
    @pytest.mark.asyncio
    async def test_real_time_data_freshness(self):
        """Test that data includes real-time freshness indicators"""
        cache = MarketDataCache()
        cache.invalidate()
        
        api_client = Mock(spec=KoreaInvestmentAPI)
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
        
        result = await get_market_index("KOSPI", cache, api_client)
        
        # Should include data freshness info
        assert "data_freshness" in result
        assert "cache_status" in result
        assert "last_updated" in result
        assert result["data_freshness"] in ["real_time", "cached", "delayed"]
    
    @pytest.mark.asyncio
    async def test_market_status_detection(self):
        """Test market status detection (open/closed/pre-market/after-hours)"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
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
        
        result = await get_market_index("KOSPI", cache, api_client)
        
        # Should detect market status
        assert "market_status" in result
        assert result["market_status"] in ["open", "closed", "pre_market", "after_hours"]
        assert "trading_session" in result
    
    @pytest.mark.asyncio
    async def test_enhanced_chart_data_processing(self):
        """Test enhanced chart data with technical indicators"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
        api_client.get_index_chart_data = AsyncMock(return_value={
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
        })
        
        result = await get_index_chart("KOSPI", "1D", "5m", cache, api_client)
        
        # Should include technical analysis
        assert "technical_indicators" in result
        assert "summary_stats" in result
        assert "price_trends" in result
        
        # Technical indicators
        tech = result["technical_indicators"]
        assert "moving_averages" in tech
        assert "volatility" in tech
        assert "trend_direction" in tech
    
    @pytest.mark.asyncio
    async def test_sector_performance_ranking(self):
        """Test sector performance ranking and analysis"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
        api_client.get_sector_indices = AsyncMock(return_value={
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
        })
        
        result = await get_sector_indices("KOSPI", cache, api_client)
        
        # Should include performance analysis
        assert "performance_ranking" in result
        assert "sector_analysis" in result
        assert "top_performers" in result
        assert "worst_performers" in result
        
        # Rankings should be sorted
        rankings = result["performance_ranking"]
        assert len(rankings) > 0
        assert all("rank" in sector for sector in rankings)


class TestDataValidationAndFormatting:
    """Test enhanced data validation and formatting"""
    
    @pytest.mark.asyncio
    async def test_data_quality_validation(self):
        """Test data quality validation and anomaly detection"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
        
        # Mock data with potential anomalies
        api_client.get_index_price = AsyncMock(return_value={
            "output": {
                "bstp_nmix_prpr": "2500.50",
                "bstp_nmix_prdy_vrss": "150.30",  # Unusually large change
                "prdy_vrss_sign": "2",
                "bstp_nmix_prdy_ctrt": "6.41",    # Unusually large change rate
                "acml_vol": "450000000",
                "acml_tr_pbmn": "8500000000000",
                "bstp_nmix_oprc": "2490.00",
                "bstp_nmix_hgpr": "2510.20",
                "bstp_nmix_lwpr": "2485.30"
            }
        })
        
        result = await get_market_index("KOSPI", cache, api_client)
        
        # Should include data quality info
        assert "data_quality" in result
        assert "anomalies_detected" in result
        assert "validation_status" in result
    
    @pytest.mark.asyncio
    async def test_multi_language_support(self):
        """Test multi-language support for sector names and descriptions"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
        api_client.get_sector_indices = AsyncMock(return_value={
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
        })
        
        result = await get_sector_indices("KOSPI", cache, api_client)
        
        # Should include multi-language names
        sectors = result["sectors"]
        for sector in sectors:
            assert "name_kr" in sector
            assert "name_en" in sector
            assert "description" in sector
    
    @pytest.mark.asyncio
    async def test_formatted_output_options(self):
        """Test different output format options"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
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
        
        # Test with formatting options
        result = await get_market_index("KOSPI", cache, api_client, format_option="detailed")
        
        # Should include formatted display values
        assert "formatted_values" in result
        assert "display_text" in result
        assert "human_readable" in result


class TestPerformanceOptimization:
    """Test performance optimization features"""
    
    @pytest.mark.asyncio
    async def test_parallel_data_fetching(self):
        """Test parallel fetching for multiple markets"""
        cache = MarketDataCache()
        cache.invalidate()
        
        api_client = Mock(spec=KoreaInvestmentAPI)
        
        # Mock responses for both markets
        responses = [
            {  # KOSPI
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
            {  # KOSDAQ
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
        ]
        
        api_client.get_index_price = AsyncMock(side_effect=responses)
        
        start_time = datetime.now()
        result = await get_market_index("ALL", cache, api_client)
        end_time = datetime.now()
        
        # Should complete quickly (parallel execution)
        execution_time = (end_time - start_time).total_seconds()
        
        assert "kospi" in result
        assert "kosdaq" in result
        assert "performance_metrics" in result
        assert result["performance_metrics"]["execution_time"] < 5.0
    
    @pytest.mark.asyncio
    async def test_batch_processing_optimization(self):
        """Test batch processing for large datasets"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
        
        # Mock large chart dataset
        large_dataset = []
        for i in range(100):  # 100 data points
            large_dataset.append({
                "stck_bsop_date": f"2024011{i%10}",
                "stck_oprc": str(2490.00 + i),
                "stck_hgpr": str(2492.50 + i),
                "stck_lwpr": str(2488.00 + i),
                "stck_clpr": str(2491.20 + i),
                "acml_vol": str(15000000 + i * 1000)
            })
        
        api_client.get_index_chart_data = AsyncMock(return_value={
            "output2": large_dataset
        })
        
        result = await get_index_chart("KOSPI", "1M", "1h", cache, api_client)
        
        # Should handle large datasets efficiently
        assert len(result["data"]) == 100
        assert "processing_stats" in result
        assert "memory_usage" in result["processing_stats"]
        assert "optimization_applied" in result["processing_stats"]
        assert result["processing_stats"]["optimization_applied"] == True  # Should be True for > 50 data points


class TestErrorHandlingAndRecovery:
    """Test advanced error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation when some data is unavailable"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
        
        # Mock partial failure (KOSPI succeeds, KOSDAQ fails)
        async def mock_get_index_price(code):
            if code == "0001":  # KOSPI
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
            else:  # KOSDAQ fails
                raise Exception("API Error")
        
        api_client.get_index_price = AsyncMock(side_effect=mock_get_index_price)
        
        result = await get_market_index("ALL", cache, api_client)
        
        # Should provide partial data with error info
        assert "kospi" in result
        assert "kosdaq_error" in result
        assert "partial_data_warning" in result
        assert result["data_completeness"] < 100
    
    @pytest.mark.asyncio
    async def test_fallback_data_sources(self):
        """Test fallback to cached or alternative data sources"""
        cache = MarketDataCache()
        api_client = Mock(spec=KoreaInvestmentAPI)
        
        # Pre-populate cache with older data
        cache.set("market_index_KOSPI_test", {
            "output": {
                "bstp_nmix_prpr": "2450.00",  # Older data
                "bstp_nmix_prdy_vrss": "10.00",
                "prdy_vrss_sign": "2",
                "bstp_nmix_prdy_ctrt": "0.40",
                "acml_vol": "400000000",
                "acml_tr_pbmn": "8000000000000",
                "bstp_nmix_oprc": "2440.00",
                "bstp_nmix_hgpr": "2460.20",
                "bstp_nmix_lwpr": "2435.30"
            }
        }, ttl=10)
        
        # Mock API failure
        api_client.get_index_price = AsyncMock(side_effect=Exception("API Down"))
        
        result = await get_market_index("KOSPI", cache, api_client, allow_fallback=True)
        
        # Should use fallback data
        assert "kospi" in result
        assert "data_source" in result
        assert result["data_source"] == "fallback_cache"
        assert "staleness_warning" in result