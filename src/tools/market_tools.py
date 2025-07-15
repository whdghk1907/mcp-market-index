"""
MCP Tools for Market Data
"""
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from ..api.client import KoreaInvestmentAPI
from ..utils.cache import MarketDataCache
from ..utils.data_processor import SectorAnalyzer, LocalizationHelper


async def get_market_summary(
    cache: MarketDataCache = None,
    api_client: KoreaInvestmentAPI = None
) -> Dict[str, Any]:
    """
    Get market summary data
    
    Args:
        cache: Cache instance
        api_client: API client instance
        
    Returns:
        Market summary data dictionary
    """
    cache_key = f"market_summary_{datetime.now().strftime('%Y%m%d_%H%M')}"
    
    summary_data = await cache.get_or_fetch(
        cache_key,
        lambda: api_client.get_market_summary(),
        ttl=10
    )
    
    return {
        "timestamp": datetime.now().isoformat(),
        "kospi": _parse_market_summary(summary_data.get("kospi", {})),
        "kosdaq": _parse_market_summary(summary_data.get("kosdaq", {}))
    }


async def get_sector_indices(
    market: str = "KOSPI",
    cache: MarketDataCache = None,
    api_client: KoreaInvestmentAPI = None
) -> Dict[str, Any]:
    """
    Get sector indices data
    
    Args:
        market: Market name (KOSPI, KOSDAQ)
        cache: Cache instance
        api_client: API client instance
        
    Returns:
        Sector indices data dictionary
    """
    if market not in ["KOSPI", "KOSDAQ"]:
        raise ValueError(f"Invalid market: {market}. Must be KOSPI or KOSDAQ")
    
    cache_key = f"sector_indices_{market}_{datetime.now().strftime('%Y%m%d_%H%M')}"
    
    sector_data = await cache.get_or_fetch(
        cache_key,
        lambda: api_client.get_sector_indices(market),
        ttl=10
    )
    
    # Parse and enhance sector data
    sectors = _parse_sector_data(sector_data)
    
    # Add translations
    sectors_with_translations = LocalizationHelper.add_translations(sectors)
    
    # Add performance analysis
    performance_analysis = SectorAnalyzer.analyze_sector_performance(sectors_with_translations)
    
    result = {
        "market": market,
        "timestamp": datetime.now().isoformat(),
        "sectors": sectors_with_translations
    }
    
    # Add performance analysis
    result.update(performance_analysis)
    
    return result


async def get_market_compare(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    cache: MarketDataCache = None,
    api_client: KoreaInvestmentAPI = None
) -> Dict[str, Any]:
    """
    Get market comparison data
    
    Args:
        date_from: Start date (YYYY-MM-DD)
        date_to: End date (YYYY-MM-DD)
        cache: Cache instance
        api_client: API client instance
        
    Returns:
        Market comparison data dictionary
    """
    # Validate date formats if provided
    if date_from:
        _validate_date_format(date_from)
    if date_to:
        _validate_date_format(date_to)
    
    # Use default period if dates not provided
    if not date_from or not date_to:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        date_from = start_date.strftime("%Y-%m-%d")
        date_to = end_date.strftime("%Y-%m-%d")
    
    cache_key = f"market_compare_{date_from}_{date_to}_{datetime.now().strftime('%Y%m%d_%H')}"
    
    # Mock comparison data for now - would need specific API endpoints
    compare_data = await cache.get_or_fetch(
        cache_key,
        lambda: _get_mock_compare_data(date_from, date_to),
        ttl=60
    )
    
    return {
        "period": {
            "from": date_from,
            "to": date_to
        },
        "kospi": _parse_compare_data(compare_data.get("kospi", {})),
        "kosdaq": _parse_compare_data(compare_data.get("kosdaq", {}))
    }


def _parse_market_summary(api_response: Dict) -> Dict[str, Any]:
    """Parse API response to market summary format"""
    output = api_response.get("output", {})
    
    return {
        "advancing": int(output.get("up_cnt", "0")),
        "declining": int(output.get("down_cnt", "0")),
        "unchanged": int(output.get("unch_cnt", "0")),
        "trading_halt": int(output.get("stop_cnt", "0")),
        "limit_up": int(output.get("uplmt_cnt", "0")),
        "limit_down": int(output.get("dnlmt_cnt", "0")),
        "new_high_52w": int(output.get("new_high_cnt", "0")),
        "new_low_52w": int(output.get("new_low_cnt", "0")),
        "market_cap": int(output.get("tot_askp_rsqn", "0")),
        "foreign_ownership_rate": float(output.get("forn_hold_rsqn", "0"))
    }


def _parse_sector_data(api_response: Dict) -> list:
    """Parse API response to sector data format"""
    output = api_response.get("output", [])
    
    sectors = []
    for item in output:
        sectors.append({
            "name": item.get("updn_issu_name", ""),
            "code": item.get("bstp_cls_code", ""),
            "current": float(item.get("bstp_nmix_prpr", "0")),
            "change": float(item.get("bstp_nmix_prdy_vrss", "0")),
            "change_rate": float(item.get("bstp_nmix_prdy_ctrt", "0")),
            "volume": int(item.get("acml_vol", "0")),
            "amount": int(item.get("acml_tr_pbmn", "0"))
        })
    
    return sectors


def _parse_compare_data(data: Dict) -> Dict[str, Any]:
    """Parse comparison data"""
    start_price = float(data.get("start_data", {}).get("bstp_nmix_prpr", "2450.00"))
    end_price = float(data.get("end_data", {}).get("bstp_nmix_prpr", "2500.50"))
    change = end_price - start_price
    change_rate = (change / start_price) * 100
    
    stats = data.get("stats", {})
    
    return {
        "start": start_price,
        "end": end_price,
        "change": change,
        "change_rate": change_rate,
        "high": float(stats.get("high_price", str(end_price + 20))),
        "low": float(stats.get("low_price", str(start_price - 10))),
        "avg_volume": int(stats.get("avg_volume", "380000000")),
        "avg_amount": int(stats.get("avg_amount", "7500000000000"))
    }


def _validate_date_format(date_str: str):
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


async def _get_mock_compare_data(date_from: str, date_to: str) -> Dict:
    """Get mock comparison data - replace with real API calls"""
    return {
        "kospi": {
            "start_data": {"bstp_nmix_prpr": "2450.00"},
            "end_data": {"bstp_nmix_prpr": "2500.50"},
            "stats": {
                "high_price": "2520.00",
                "low_price": "2440.00",
                "avg_volume": "380000000",
                "avg_amount": "7500000000000"
            }
        },
        "kosdaq": {
            "start_data": {"bstp_nmix_prpr": "830.00"},
            "end_data": {"bstp_nmix_prpr": "850.25"},
            "stats": {
                "high_price": "865.00",
                "low_price": "825.50",
                "avg_volume": "750000000",
                "avg_amount": "4800000000000"
            }
        }
    }