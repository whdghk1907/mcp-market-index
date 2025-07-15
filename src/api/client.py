"""
Korea Investment API Client
"""
import aiohttp
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

from ..utils.retry import retry_on_error, APIError, RateLimitError
from ..config import get_settings


logger = logging.getLogger(__name__)


class KoreaInvestmentAPI:
    """Korea Investment API client"""
    
    def __init__(self, app_key: str, app_secret: str, base_url: Optional[str] = None):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = base_url or get_settings().korea_investment_base_url
        self.access_token: Optional[str] = None
        self.token_expires: Optional[datetime] = None
        self._token_lock = asyncio.Lock()
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def close(self):
        """Close HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def _get_access_token(self) -> str:
        """Get or refresh access token"""
        async with self._token_lock:
            # Check if current token is still valid
            if (self.access_token and 
                self.token_expires and 
                self.token_expires > datetime.now()):
                return self.access_token
            
            # Request new token
            headers = {"content-type": "application/json"}
            body = {
                "grant_type": "client_credentials",
                "appkey": self.app_key,
                "appsecret": self.app_secret
            }
            
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.post(
                        f"{self.base_url}/oauth2/tokenP",
                        headers=headers,
                        json=body
                    ) as response:
                        if response.status == 429:
                            raise RateLimitError("Token request rate limit exceeded")
                        elif response.status != 200:
                            raise APIError(f"Token request failed with status {response.status}")
                        
                        data = await response.json()
                        self.access_token = data["access_token"]
                        self.token_expires = datetime.now() + timedelta(
                            seconds=data.get("expires_in", 3600)
                        )
                        
                        logger.info("Successfully obtained new access token")
                        return self.access_token
                        
                except aiohttp.ClientError as e:
                    raise APIError(f"Token request failed: {str(e)}")
    
    @retry_on_error(max_attempts=3, delay=1.0, exceptions=(APIError,))
    async def get_index_price(self, index_code: str) -> Dict:
        """
        Get index current price
        
        Args:
            index_code: Index code (0001 for KOSPI, 1001 for KOSDAQ)
            
        Returns:
            API response dictionary
        """
        token = await self._get_access_token()
        
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKUP03500100"
        }
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "U",
            "FID_INPUT_ISCD": index_code
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-index-price",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("API rate limit exceeded")
                    elif response.status != 200:
                        raise APIError(f"API request failed with status {response.status}")
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                raise APIError(f"API request failed: {str(e)}")
    
    @retry_on_error(max_attempts=3, delay=1.0, exceptions=(APIError,))
    async def get_index_chart_data(
        self, 
        index_code: str, 
        period_div_code: str,
        input_date: str = ""
    ) -> Dict:
        """
        Get index chart data
        
        Args:
            index_code: Index code
            period_div_code: Period division code
            input_date: Input date
            
        Returns:
            API response dictionary
        """
        token = await self._get_access_token()
        
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKUP03500200"
        }
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "U",
            "FID_INPUT_ISCD": index_code,
            "FID_PERIOD_DIV_CODE": period_div_code,
            "FID_INPUT_DATE_1": input_date
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-index-chart-price",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("API rate limit exceeded")
                    elif response.status != 200:
                        raise APIError(f"API request failed with status {response.status}")
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                raise APIError(f"API request failed: {str(e)}")
    
    @retry_on_error(max_attempts=3, delay=1.0, exceptions=(APIError,))
    async def get_market_summary(self) -> Dict:
        """
        Get market summary data
        
        Returns:
            API response dictionary
        """
        token = await self._get_access_token()
        
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKUP03500300"
        }
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "U"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-market-summary",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("API rate limit exceeded")
                    elif response.status != 200:
                        raise APIError(f"API request failed with status {response.status}")
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                raise APIError(f"API request failed: {str(e)}")
    
    @retry_on_error(max_attempts=3, delay=1.0, exceptions=(APIError,))
    async def get_sector_data(self) -> Dict:
        """
        Get sector performance data
        
        Returns:
            API response dictionary
        """
        token = await self._get_access_token()
        
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKUP03500400"
        }
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "U"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-sector-data",
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 429:
                        raise RateLimitError("API rate limit exceeded")
                    elif response.status != 200:
                        raise APIError(f"API request failed with status {response.status}")
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                raise APIError(f"API request failed: {str(e)}")