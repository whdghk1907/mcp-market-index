"""
Tests for Korea Investment API Client
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta
import aiohttp

from src.api.client import KoreaInvestmentAPI
from src.api.models import IndexData, ChartData, SectorData


class TestKoreaInvestmentAPI:
    """Test cases for Korea Investment API client"""
    
    @pytest.fixture
    def api_client(self):
        """Create API client for testing"""
        return KoreaInvestmentAPI(
            app_key="test_key",
            app_secret="test_secret"
        )
    
    @pytest.fixture
    def mock_token_response(self):
        """Mock token response"""
        return {
            "access_token": "test_token_123",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
    
    @pytest.fixture
    def mock_index_response(self):
        """Mock index price response"""
        return {
            "output": {
                "bstp_nmix_prpr": "2500.50",  # 현재가
                "bstp_nmix_prdy_vrss": "15.30",  # 전일대비
                "prdy_vrss_sign": "2",  # 등락구분 (2:상승)
                "bstp_nmix_prdy_ctrt": "0.61",  # 등락률
                "acml_vol": "450000000",  # 누적거래량
                "acml_tr_pbmn": "8500000000000",  # 누적거래대금
                "bstp_nmix_oprc": "2490.00",  # 시가
                "bstp_nmix_hgpr": "2510.20",  # 고가
                "bstp_nmix_lwpr": "2485.30"   # 저가
            }
        }
    
    @pytest.fixture
    def mock_chart_response(self):
        """Mock chart data response"""
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
    
    @pytest.mark.asyncio
    async def test_get_access_token_success(self, api_client, mock_token_response):
        """Test successful token acquisition"""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_token_response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            token = await api_client._get_access_token()
            
            assert token == "test_token_123"
            assert api_client.access_token == "test_token_123"
            assert api_client.token_expires > datetime.now()
    
    @pytest.mark.asyncio
    async def test_get_access_token_cached(self, api_client):
        """Test token caching functionality"""
        # Set existing valid token
        api_client.access_token = "cached_token"
        api_client.token_expires = datetime.now() + timedelta(minutes=30)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            token = await api_client._get_access_token()
            
            assert token == "cached_token"
            assert not mock_post.called  # Should not make new request
    
    @pytest.mark.asyncio
    async def test_get_access_token_expired(self, api_client, mock_token_response):
        """Test token refresh when expired"""
        # Set expired token
        api_client.access_token = "expired_token"
        api_client.token_expires = datetime.now() - timedelta(minutes=1)
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_token_response
            mock_post.return_value.__aenter__.return_value = mock_response
            
            token = await api_client._get_access_token()
            
            assert token == "test_token_123"
            assert mock_post.called
    
    @pytest.mark.asyncio
    async def test_get_index_price_kospi(self, api_client, mock_index_response):
        """Test KOSPI index price retrieval"""
        with patch.object(api_client, '_get_access_token', return_value="test_token"), \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_index_response
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await api_client.get_index_price("0001")
            
            assert result == mock_index_response
            
            # Verify correct parameters were used
            call_args = mock_get.call_args
            assert call_args[1]['params']['FID_INPUT_ISCD'] == "0001"
    
    @pytest.mark.asyncio
    async def test_get_index_price_kosdaq(self, api_client, mock_index_response):
        """Test KOSDAQ index price retrieval"""
        with patch.object(api_client, '_get_access_token', return_value="test_token"), \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_index_response
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await api_client.get_index_price("1001")
            
            assert result == mock_index_response
            
            # Verify correct parameters were used
            call_args = mock_get.call_args
            assert call_args[1]['params']['FID_INPUT_ISCD'] == "1001"
    
    @pytest.mark.asyncio
    async def test_get_chart_data(self, api_client, mock_chart_response):
        """Test chart data retrieval"""
        with patch.object(api_client, '_get_access_token', return_value="test_token"), \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_chart_response
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await api_client.get_index_chart_data(
                index_code="0001",
                period_div_code="D",
                input_date="20240110"
            )
            
            assert result == mock_chart_response
            
            # Verify parameters
            call_args = mock_get.call_args
            params = call_args[1]['params']
            assert params['FID_INPUT_ISCD'] == "0001"
            assert params['FID_PERIOD_DIV_CODE'] == "D"
            assert params['FID_INPUT_DATE_1'] == "20240110"
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, api_client):
        """Test API error handling"""
        with patch.object(api_client, '_get_access_token', return_value="test_token"), \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            # Simulate HTTP error
            mock_get.side_effect = aiohttp.ClientError("Connection failed")
            
            with pytest.raises(aiohttp.ClientError):
                await api_client.get_index_price("0001")
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self, api_client):
        """Test rate limit error handling"""
        with patch.object(api_client, '_get_access_token', return_value="test_token"), \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.status = 429  # Rate limit
            mock_response.json.return_value = {"error": "Rate limit exceeded"}
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await api_client.get_index_price("0001")
            
            # Should still return response for handling upstream
            assert result["error"] == "Rate limit exceeded"
    
    @pytest.mark.asyncio
    async def test_get_sector_indices(self, api_client):
        """Test sector indices retrieval"""
        mock_response_data = {
            "output": [
                {
                    "updn_issu_name": "반도체",
                    "bstp_cls_code": "G2510",
                    "bstp_nmix_prpr": "3250.50",
                    "bstp_nmix_prdy_vrss": "45.20",
                    "prdy_vrss_sign": "2",
                    "bstp_nmix_prdy_ctrt": "1.41"
                }
            ]
        }
        
        with patch.object(api_client, '_get_access_token', return_value="test_token"), \
             patch('aiohttp.ClientSession.get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_response_data
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await api_client.get_sector_indices("KOSPI")
            
            assert result == mock_response_data
    
    @pytest.mark.asyncio
    async def test_connection_test(self, api_client):
        """Test connection testing functionality"""
        with patch.object(api_client, '_get_access_token', return_value="test_token"):
            # Should not raise exception with valid token
            await api_client.test_connection()
    
    @pytest.mark.asyncio
    async def test_connection_test_failure(self, api_client):
        """Test connection test failure"""
        with patch.object(api_client, '_get_access_token', side_effect=Exception("Auth failed")):
            with pytest.raises(Exception):
                await api_client.test_connection()
    
    def test_init_with_custom_base_url(self):
        """Test initialization with custom base URL"""
        client = KoreaInvestmentAPI(
            app_key="test_key",
            app_secret="test_secret",
            base_url="https://custom.url.com"
        )
        
        assert client.base_url == "https://custom.url.com"
    
    @pytest.mark.asyncio
    async def test_concurrent_token_requests(self, api_client, mock_token_response):
        """Test that concurrent token requests don't cause race conditions"""
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.1)  # Simulate API delay
            mock_response = AsyncMock()
            mock_response.json.return_value = mock_token_response
            return mock_response
        
        with patch('aiohttp.ClientSession.post') as mock_post_patch:
            mock_post_patch.return_value.__aenter__ = mock_post
            
            # Make multiple concurrent token requests
            tasks = [api_client._get_access_token() for _ in range(5)]
            tokens = await asyncio.gather(*tasks)
            
            # All should return the same token
            assert all(token == "test_token_123" for token in tokens)
            # Should only make one actual API call
            assert call_count == 1