"""
Configuration management for MCP Market Index Server
"""
import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    # Korea Investment API Configuration
    korea_investment_app_key: str = Field(default="test_key", env="KOREA_INVESTMENT_APP_KEY")
    korea_investment_app_secret: str = Field(default="test_secret", env="KOREA_INVESTMENT_APP_SECRET")
    korea_investment_base_url: str = Field(
        default="https://openapi.koreainvestment.com:9443",
        env="KOREA_INVESTMENT_BASE_URL"
    )
    
    # Cache Configuration
    cache_ttl_seconds: int = Field(default=5, env="CACHE_TTL_SECONDS")
    cache_chart_ttl_seconds: int = Field(default=30, env="CACHE_CHART_TTL_SECONDS")
    cache_summary_ttl_seconds: int = Field(default=10, env="CACHE_SUMMARY_TTL_SECONDS")
    
    # API Rate Limiting
    max_requests_per_minute: int = Field(default=100, env="MAX_REQUESTS_PER_MINUTE")
    max_retry_attempts: int = Field(default=3, env="MAX_RETRY_ATTEMPTS")
    retry_delay_seconds: float = Field(default=1.0, env="RETRY_DELAY_SECONDS")
    
    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file_path: str = Field(default="logs/mcp-market-index.log", env="LOG_FILE_PATH")
    
    # MCP Server Configuration
    server_name: str = Field(default="mcp-market-index", env="SERVER_NAME")
    server_version: str = Field(default="1.0.0", env="SERVER_VERSION")
    
    # Development Configuration
    debug: bool = Field(default=False, env="DEBUG")
    
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings"""
    return settings


# API Endpoints for Korea Investment
API_ENDPOINTS = {
    "token": "/oauth2/tokenP",
    "index_price": "/uapi/domestic-stock/v1/quotations/inquire-index-price",
    "index_chart": "/uapi/domestic-stock/v1/quotations/inquire-index-chart-price",
    "sector_index": "/uapi/domestic-stock/v1/quotations/inquire-sector-index",
    "market_info": "/uapi/domestic-stock/v1/quotations/inquire-market-info"
}

# Market Codes
MARKET_CODES = {
    "KOSPI": "0001",
    "KOSDAQ": "1001"
}

# Sector Codes (주요 업종만 포함)
SECTOR_CODES = {
    "KOSPI": {
        "반도체": "G2510",
        "은행": "G2710", 
        "화학": "G2720",
        "철강": "G2730",
        "자동차": "G2740",
        "건설": "G2750",
        "조선": "G2760",
        "기계": "G2770",
        "전기전자": "G2780"
    },
    "KOSDAQ": {
        "IT": "Q1510",
        "바이오": "Q1520",
        "게임": "Q1530",
        "소프트웨어": "Q1540",
        "통신": "Q1550"
    }
}

# Chart Period Codes
CHART_PERIOD_CODES = {
    "1D": "D",
    "1W": "W", 
    "1M": "M",
    "3M": "M",
    "1Y": "Y"
}

# Chart Interval Codes  
CHART_INTERVAL_CODES = {
    "1m": "1",
    "5m": "5",
    "30m": "30", 
    "1h": "60",
    "1d": "D"
}