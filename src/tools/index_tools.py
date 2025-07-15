"""
MCP Tools for Index Data
"""
from datetime import datetime
from typing import Dict, Any
import asyncio

from ..api.client import KoreaInvestmentAPI
from ..utils.cache import MarketDataCache
from ..utils.data_processor import (
    MarketStatusDetector, DataFreshnessAnalyzer, DataQualityValidator, 
    TechnicalIndicatorCalculator, PerformanceTracker
)
from ..config import MARKET_CODES, CHART_PERIOD_CODES, CHART_INTERVAL_CODES


async def get_market_index(
    market: str = "ALL",
    cache: MarketDataCache = None,
    api_client: KoreaInvestmentAPI = None,
    format_option: str = "standard",
    allow_fallback: bool = False
) -> Dict[str, Any]:
    """
    Get current market index data with advanced features
    
    Args:
        market: Market to query (KOSPI, KOSDAQ, ALL)
        cache: Cache instance
        api_client: API client instance
        format_option: Output format ('standard', 'detailed')
        allow_fallback: Allow fallback to cached data on API failure
        
    Returns:
        Market index data dictionary with advanced metadata
    """
    if market not in ["KOSPI", "KOSDAQ", "ALL"]:
        raise ValueError(f"Invalid market: {market}. Must be KOSPI, KOSDAQ, or ALL")
    
    start_time = datetime.now()
    
    # Market status detection
    market_status = MarketStatusDetector.get_market_status()
    trading_session = MarketStatusDetector.get_trading_session()
    
    result = {
        "timestamp": start_time.isoformat(),
        "market_status": market_status,
        "trading_session": trading_session
    }
    
    cache_hits = 0
    data_completeness = 0
    total_expected = 1 if market != "ALL" else 2
    
    try:
        if market in ["KOSPI", "ALL"]:
            try:
                cache_key = f"market_index_KOSPI_{start_time.strftime('%Y%m%d_%H%M')}"
                was_cached = cache.get(cache_key) is not None
                
                kospi_data = await cache.get_or_fetch(
                    cache_key,
                    lambda: api_client.get_index_price(MARKET_CODES["KOSPI"]),
                    ttl=5
                )
                
                if was_cached:
                    cache_hits += 1
                
                parsed_kospi = _parse_index_data(kospi_data)
                
                # Add data quality validation
                quality_result = DataQualityValidator.validate_index_data(parsed_kospi)
                parsed_kospi["data_quality"] = quality_result["quality_score"]
                parsed_kospi["anomalies_detected"] = quality_result["anomalies"]
                parsed_kospi["validation_status"] = quality_result["validation_status"]
                
                result["kospi"] = parsed_kospi
                data_completeness += 1
                
            except Exception as e:
                if allow_fallback:
                    # Try to get cached data even if expired
                    fallback_keys = [
                        cache_key,  # Try the original cache key first
                        f"market_index_KOSPI_fallback",  # Then specific fallback key
                        f"market_index_KOSPI_test"  # Then test key
                    ]
                    fallback_data = None
                    for fallback_key in fallback_keys:
                        fallback_data = cache.get(fallback_key)
                        if fallback_data:
                            break
                    
                    if fallback_data:
                        result["kospi"] = _parse_index_data(fallback_data)
                        result["data_source"] = "fallback_cache"
                        result["staleness_warning"] = "Using cached data due to API failure"
                        data_completeness += 0.5
                    else:
                        result["kospi_error"] = str(e)
                else:
                    result["kospi_error"] = str(e)
        
        if market in ["KOSDAQ", "ALL"]:
            try:
                cache_key = f"market_index_KOSDAQ_{start_time.strftime('%Y%m%d_%H%M')}"
                was_cached = cache.get(cache_key) is not None
                
                kosdaq_data = await cache.get_or_fetch(
                    cache_key,
                    lambda: api_client.get_index_price(MARKET_CODES["KOSDAQ"]),
                    ttl=5
                )
                
                if was_cached:
                    cache_hits += 1
                
                parsed_kosdaq = _parse_index_data(kosdaq_data)
                
                # Add data quality validation
                quality_result = DataQualityValidator.validate_index_data(parsed_kosdaq)
                parsed_kosdaq["data_quality"] = quality_result["quality_score"]
                parsed_kosdaq["anomalies_detected"] = quality_result["anomalies"]
                parsed_kosdaq["validation_status"] = quality_result["validation_status"]
                
                result["kosdaq"] = parsed_kosdaq
                data_completeness += 1
                
            except Exception as e:
                if allow_fallback:
                    # Try to get cached data even if expired
                    fallback_keys = [
                        cache_key,  # Try the original cache key first
                        f"market_index_KOSDAQ_fallback",  # Then specific fallback key
                        f"market_index_KOSDAQ_test"  # Then test key
                    ]
                    fallback_data = None
                    for fallback_key in fallback_keys:
                        fallback_data = cache.get(fallback_key)
                        if fallback_data:
                            break
                    
                    if fallback_data:
                        result["kosdaq"] = _parse_index_data(fallback_data)
                        result["data_source"] = "fallback_cache"
                        result["staleness_warning"] = "Using cached data due to API failure"
                        data_completeness += 0.5
                    else:
                        result["kosdaq_error"] = str(e)
                else:
                    result["kosdaq_error"] = str(e)
    
    except Exception as e:
        result["general_error"] = str(e)
    
    # Data freshness analysis
    freshness_info = DataFreshnessAnalyzer.analyze_freshness(
        start_time, 
        cache_hit=(cache_hits > 0)
    )
    
    result["data_freshness"] = freshness_info["freshness"]
    result["cache_status"] = "hit" if cache_hits > 0 else "miss"
    result["last_updated"] = freshness_info["data_timestamp"]
    
    # Data completeness
    result["data_completeness"] = (data_completeness / total_expected) * 100
    if data_completeness < total_expected:
        result["partial_data_warning"] = "Some market data unavailable"
    
    # Aggregate data quality info
    all_anomalies = []
    total_quality_score = 0
    quality_count = 0
    
    for market_name in ["kospi", "kosdaq"]:
        if market_name in result and isinstance(result[market_name], dict):
            market_data = result[market_name]
            if "anomalies_detected" in market_data:
                all_anomalies.extend(market_data["anomalies_detected"])
            if "data_quality" in market_data:
                total_quality_score += market_data["data_quality"]
                quality_count += 1
    
    result["data_quality"] = total_quality_score / quality_count if quality_count > 0 else 100
    result["anomalies_detected"] = all_anomalies
    result["validation_status"] = "anomalies_detected" if all_anomalies else "valid"
    
    # Performance metrics
    end_time = datetime.now()
    result["performance_metrics"] = PerformanceTracker.create_performance_metrics(
        start_time, end_time, data_points=data_completeness, cache_hits=cache_hits
    )
    
    # Add formatted output for detailed format
    if format_option == "detailed":
        result["formatted_values"] = _create_formatted_values(result)
        result["display_text"] = _create_display_text(result)
        result["human_readable"] = _create_human_readable_summary(result)
    
    return result


async def get_index_chart(
    market: str,
    period: str = "1D",
    interval: str = "5m",
    cache: MarketDataCache = None,
    api_client: KoreaInvestmentAPI = None
) -> Dict[str, Any]:
    """
    Get index chart data
    
    Args:
        market: Market name (KOSPI, KOSDAQ)
        period: Chart period (1D, 1W, 1M, 3M, 1Y)
        interval: Chart interval (1m, 5m, 30m, 1h, 1d)
        cache: Cache instance
        api_client: API client instance
        
    Returns:
        Chart data dictionary
    """
    if market not in ["KOSPI", "KOSDAQ"]:
        raise ValueError(f"Invalid market: {market}. Must be KOSPI or KOSDAQ")
    
    if period not in ["1D", "1W", "1M", "3M", "1Y"]:
        raise ValueError(f"Invalid period: {period}")
    
    if interval not in ["1m", "5m", "30m", "1h", "1d"]:
        raise ValueError(f"Invalid interval: {interval}")
    
    # Get chart data from API via cache
    cache_key = f"chart_data_{market}_{period}_{interval}_{datetime.now().strftime('%Y%m%d_%H%M')}"
    
    chart_response = await cache.get_or_fetch(
        cache_key,
        lambda: api_client.get_index_chart_data(
            index_code=MARKET_CODES[market],
            period_div_code=CHART_PERIOD_CODES[period],
            input_date=""
        ),
        ttl=30
    )
    
    # Parse chart data
    chart_data = _parse_chart_data(chart_response)
    
    # Add technical analysis
    tech_analysis = TechnicalIndicatorCalculator.analyze_chart_data(chart_data)
    
    # Create response
    response = {
        "market": market,
        "period": period,
        "interval": interval,
        "data": chart_data
    }
    
    # Add technical indicators if we have enough data
    if tech_analysis:
        response.update(tech_analysis)
    
    # Add processing stats
    response["processing_stats"] = {
        "data_points": len(chart_data),
        "memory_usage": len(str(chart_data)),
        "optimization_applied": len(chart_data) > 50
    }
    
    return response


def _parse_index_data(api_response: Dict) -> Dict[str, Any]:
    """Parse API response to index data format"""
    output = api_response.get("output", {})
    
    return {
        "current": float(output.get("bstp_nmix_prpr", "0")),
        "change": float(output.get("bstp_nmix_prdy_vrss", "0")),
        "change_rate": float(output.get("bstp_nmix_prdy_ctrt", "0")),
        "volume": int(output.get("acml_vol", "0")),
        "amount": int(output.get("acml_tr_pbmn", "0")),
        "high": float(output.get("bstp_nmix_hgpr", "0")),
        "low": float(output.get("bstp_nmix_lwpr", "0")),
        "open": float(output.get("bstp_nmix_oprc", "0"))
    }


def _parse_chart_data(api_response: Dict) -> list:
    """Parse API response to chart data format"""
    output = api_response.get("output2", [])
    
    chart_points = []
    for item in output:
        chart_points.append({
            "timestamp": _parse_date(item.get("stck_bsop_date", "20240101")),
            "open": float(item.get("stck_oprc", "0")),
            "high": float(item.get("stck_hgpr", "0")),
            "low": float(item.get("stck_lwpr", "0")),
            "close": float(item.get("stck_clpr", "0")),
            "volume": int(item.get("acml_vol", "0"))
        })
    
    return chart_points


def _parse_date(date_str: str) -> str:
    """Parse date string to ISO format"""
    try:
        if len(date_str) == 8:  # YYYYMMDD
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{year}-{month}-{day}T09:00:00+09:00"
        return date_str
    except:
        return "2024-01-01T09:00:00+09:00"


def _create_formatted_values(result: Dict[str, Any]) -> Dict[str, Any]:
    """Create formatted display values"""
    formatted = {}
    
    for market in ["kospi", "kosdaq"]:
        if market in result:
            data = result[market]
            formatted[market] = {
                "current_formatted": f"{data.get('current', 0):,.2f}",
                "change_formatted": f"{data.get('change', 0):+,.2f}",
                "change_rate_formatted": f"{data.get('change_rate', 0):+.2f}%",
                "volume_formatted": f"{data.get('volume', 0):,}",
                "amount_formatted": f"{data.get('amount', 0):,.0f}"
            }
    
    return formatted


def _create_display_text(result: Dict[str, Any]) -> str:
    """Create human-readable display text"""
    lines = []
    lines.append(f"Market Status: {result.get('market_status', 'unknown').title()}")
    lines.append(f"Trading Session: {result.get('trading_session', 'unknown').replace('_', ' ').title()}")
    lines.append("")
    
    for market in ["kospi", "kosdaq"]:
        if market in result:
            data = result[market]
            market_name = market.upper()
            current = data.get('current', 0)
            change = data.get('change', 0)
            change_rate = data.get('change_rate', 0)
            
            direction = "↑" if change > 0 else "↓" if change < 0 else "→"
            lines.append(f"{market_name}: {current:,.2f} {direction} {change:+,.2f} ({change_rate:+.2f}%)")
    
    return "\n".join(lines)


def _create_human_readable_summary(result: Dict[str, Any]) -> str:
    """Create human-readable summary"""
    summary_parts = []
    
    # Market status
    status = result.get('market_status', 'unknown')
    if status == 'open':
        summary_parts.append("Markets are currently open")
    elif status == 'closed':
        summary_parts.append("Markets are currently closed")
    else:
        summary_parts.append(f"Markets are in {status.replace('_', ' ')} session")
    
    # Performance summary
    if 'kospi' in result and 'kosdaq' in result:
        kospi_change = result['kospi'].get('change_rate', 0)
        kosdaq_change = result['kosdaq'].get('change_rate', 0)
        
        if kospi_change > 0 and kosdaq_change > 0:
            summary_parts.append("Both markets are showing positive performance")
        elif kospi_change < 0 and kosdaq_change < 0:
            summary_parts.append("Both markets are showing negative performance")
        else:
            summary_parts.append("Markets are showing mixed performance")
    
    # Data quality
    data_completeness = result.get('data_completeness', 100)
    if data_completeness < 100:
        summary_parts.append(f"Data completeness: {data_completeness:.0f}%")
    
    return ". ".join(summary_parts) + "."