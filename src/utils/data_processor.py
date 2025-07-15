"""
Advanced data processing utilities for market data
"""
from datetime import datetime, time
from typing import Dict, Any, List, Optional
import statistics


class MarketStatusDetector:
    """Detect market status based on time and data"""
    
    MARKET_OPEN_TIME = time(9, 0)  # 9:00 AM
    MARKET_CLOSE_TIME = time(15, 30)  # 3:30 PM
    
    @classmethod
    def get_market_status(cls, timestamp: Optional[datetime] = None) -> str:
        """
        Determine current market status
        
        Returns:
            str: 'open', 'closed', 'pre_market', 'after_hours'
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        current_time = timestamp.time()
        weekday = timestamp.weekday()
        
        # Weekend
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            return "closed"
        
        # Weekday time check
        if current_time < cls.MARKET_OPEN_TIME:
            return "pre_market"
        elif current_time > cls.MARKET_CLOSE_TIME:
            return "after_hours"
        else:
            return "open"
    
    @classmethod
    def get_trading_session(cls, timestamp: Optional[datetime] = None) -> str:
        """Get detailed trading session info"""
        status = cls.get_market_status(timestamp)
        
        if timestamp is None:
            timestamp = datetime.now()
        
        current_time = timestamp.time()
        
        if status == "open":
            if current_time < time(10, 0):
                return "opening_session"
            elif current_time > time(14, 30):
                return "closing_session"
            else:
                return "regular_session"
        
        return status


class DataFreshnessAnalyzer:
    """Analyze data freshness and quality"""
    
    @classmethod
    def analyze_freshness(cls, data_timestamp: datetime, cache_hit: bool = False) -> Dict[str, Any]:
        """
        Analyze data freshness
        
        Args:
            data_timestamp: When the data was generated
            cache_hit: Whether data came from cache
            
        Returns:
            Dict with freshness analysis
        """
        now = datetime.now()
        age_seconds = (now - data_timestamp).total_seconds()
        
        if cache_hit:
            freshness = "cached"
        elif age_seconds < 30:
            freshness = "real_time"
        elif age_seconds < 300:  # 5 minutes
            freshness = "delayed"
        else:
            freshness = "stale"
        
        return {
            "freshness": freshness,
            "age_seconds": age_seconds,
            "is_cache_hit": cache_hit,
            "data_timestamp": data_timestamp.isoformat(),
            "analysis_timestamp": now.isoformat()
        }


class DataQualityValidator:
    """Validate data quality and detect anomalies"""
    
    @classmethod
    def validate_index_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate index data for quality and anomalies
        
        Args:
            data: Index data dictionary
            
        Returns:
            Validation results
        """
        anomalies = []
        warnings = []
        
        current = data.get("current", 0)
        change = data.get("change", 0)
        change_rate = data.get("change_rate", 0)
        
        # Check for extreme movements
        if abs(change_rate) > 5.0:  # >5% change
            anomalies.append(f"Extreme price movement: {change_rate:.2f}%")
        
        if abs(change_rate) > 2.0:  # >2% change
            warnings.append(f"Large price movement: {change_rate:.2f}%")
        
        # Check for data consistency
        if current <= 0:
            anomalies.append("Invalid current price: must be positive")
        
        # Calculate expected change rate
        if current > 0 and change != 0:
            expected_rate = (change / (current - change)) * 100
            if abs(change_rate - expected_rate) > 0.1:
                warnings.append("Change rate inconsistency detected")
        
        validation_status = "valid"
        if anomalies:
            validation_status = "anomalies_detected"
        elif warnings:
            validation_status = "warnings"
        
        return {
            "validation_status": validation_status,
            "anomalies": anomalies,
            "warnings": warnings,
            "quality_score": max(0, 100 - len(anomalies) * 30 - len(warnings) * 10)
        }


class TechnicalIndicatorCalculator:
    """Calculate technical indicators for chart data"""
    
    @classmethod
    def calculate_moving_averages(cls, prices: List[float]) -> Dict[str, float]:
        """Calculate moving averages"""
        if len(prices) < 5:
            return {}
        
        ma5 = statistics.mean(prices[-5:]) if len(prices) >= 5 else None
        ma10 = statistics.mean(prices[-10:]) if len(prices) >= 10 else None
        ma20 = statistics.mean(prices[-20:]) if len(prices) >= 20 else None
        
        result = {}
        if ma5 is not None:
            result["ma5"] = round(ma5, 2)
        if ma10 is not None:
            result["ma10"] = round(ma10, 2)
        if ma20 is not None:
            result["ma20"] = round(ma20, 2)
        
        return result
    
    @classmethod
    def calculate_volatility(cls, prices: List[float]) -> float:
        """Calculate price volatility (standard deviation)"""
        if len(prices) < 2:
            return 0.0
        
        return round(statistics.stdev(prices), 4)
    
    @classmethod
    def detect_trend(cls, prices: List[float]) -> str:
        """Detect price trend direction"""
        if len(prices) < 3:
            return "insufficient_data"
        
        recent_prices = prices[-5:]
        if len(recent_prices) < 3:
            recent_prices = prices
        
        # Simple trend detection
        start_price = recent_prices[0]
        end_price = recent_prices[-1]
        change_percent = ((end_price - start_price) / start_price) * 100
        
        if change_percent > 0.5:
            return "uptrend"
        elif change_percent < -0.5:
            return "downtrend"
        else:
            return "sideways"
    
    @classmethod
    def analyze_chart_data(cls, chart_data: List[Dict]) -> Dict[str, Any]:
        """Comprehensive chart data analysis"""
        if not chart_data:
            return {}
        
        # Extract prices
        close_prices = [float(point.get("close", 0)) for point in chart_data]
        high_prices = [float(point.get("high", 0)) for point in chart_data]
        low_prices = [float(point.get("low", 0)) for point in chart_data]
        volumes = [int(point.get("volume", 0)) for point in chart_data]
        
        # Calculate indicators
        moving_averages = cls.calculate_moving_averages(close_prices)
        volatility = cls.calculate_volatility(close_prices)
        trend = cls.detect_trend(close_prices)
        
        # Summary statistics
        summary_stats = {
            "highest_price": max(high_prices) if high_prices else 0,
            "lowest_price": min(low_prices) if low_prices else 0,
            "average_volume": round(statistics.mean(volumes)) if volumes else 0,
            "total_volume": sum(volumes),
            "price_range": max(high_prices) - min(low_prices) if high_prices and low_prices else 0
        }
        
        return {
            "technical_indicators": {
                "moving_averages": moving_averages,
                "volatility": volatility,
                "trend_direction": trend
            },
            "summary_stats": summary_stats,
            "price_trends": {
                "current_trend": trend,
                "volatility_level": "high" if volatility > 50 else "medium" if volatility > 20 else "low"
            }
        }


class SectorAnalyzer:
    """Analyze sector performance and rankings"""
    
    @classmethod
    def rank_sectors(cls, sectors: List[Dict]) -> List[Dict]:
        """Rank sectors by performance"""
        # Sort by change_rate (performance)
        sorted_sectors = sorted(
            sectors,
            key=lambda x: float(x.get("change_rate", 0)),
            reverse=True
        )
        
        # Add rank information
        for i, sector in enumerate(sorted_sectors):
            sector["rank"] = i + 1
            sector["performance_tier"] = cls._get_performance_tier(i, len(sorted_sectors))
        
        return sorted_sectors
    
    @classmethod
    def _get_performance_tier(cls, rank: int, total_sectors: int) -> str:
        """Determine performance tier based on rank"""
        top_third = total_sectors // 3
        if rank < top_third:
            return "top_performer"
        elif rank < 2 * top_third:
            return "middle_performer"
        else:
            return "underperformer"
    
    @classmethod
    def analyze_sector_performance(cls, sectors: List[Dict]) -> Dict[str, Any]:
        """Comprehensive sector performance analysis"""
        if not sectors:
            return {}
        
        ranked_sectors = cls.rank_sectors(sectors)
        
        # Get top and worst performers
        top_performers = [s for s in ranked_sectors if s.get("performance_tier") == "top_performer"]
        worst_performers = [s for s in ranked_sectors if s.get("performance_tier") == "underperformer"]
        
        # Calculate statistics
        change_rates = [float(s.get("change_rate", 0)) for s in sectors]
        avg_performance = statistics.mean(change_rates) if change_rates else 0
        
        return {
            "performance_ranking": ranked_sectors,
            "top_performers": top_performers[:3],  # Top 3
            "worst_performers": worst_performers[-3:],  # Bottom 3
            "sector_analysis": {
                "average_performance": round(avg_performance, 2),
                "best_sector": ranked_sectors[0] if ranked_sectors else None,
                "worst_sector": ranked_sectors[-1] if ranked_sectors else None,
                "total_sectors": len(sectors)
            }
        }


class LocalizationHelper:
    """Handle multi-language support"""
    
    SECTOR_TRANSLATIONS = {
        "반도체": {"en": "Semiconductors", "kr": "반도체"},
        "은행": {"en": "Banking", "kr": "은행"},
        "화학": {"en": "Chemicals", "kr": "화학"},
        "철강": {"en": "Steel", "kr": "철강"},
        "자동차": {"en": "Automotive", "kr": "자동차"},
        "건설": {"en": "Construction", "kr": "건설"},
        "조선": {"en": "Shipbuilding", "kr": "조선"},
        "기계": {"en": "Machinery", "kr": "기계"},
        "전기전자": {"en": "Electronics", "kr": "전기전자"},
        "IT": {"en": "Information Technology", "kr": "정보기술"},
        "바이오": {"en": "Biotechnology", "kr": "바이오"},
        "게임": {"en": "Gaming", "kr": "게임"},
        "소프트웨어": {"en": "Software", "kr": "소프트웨어"},
        "통신": {"en": "Telecommunications", "kr": "통신"}
    }
    
    @classmethod
    def add_translations(cls, sectors: List[Dict]) -> List[Dict]:
        """Add multi-language names to sectors"""
        for sector in sectors:
            name_kr = sector.get("name", "")
            translation = cls.SECTOR_TRANSLATIONS.get(name_kr, {})
            
            sector["name_kr"] = name_kr
            sector["name_en"] = translation.get("en", name_kr)
            sector["description"] = cls._get_sector_description(name_kr)
        
        return sectors
    
    @classmethod
    def _get_sector_description(cls, sector_name: str) -> str:
        """Get sector description"""
        descriptions = {
            "반도체": "Technology sector focusing on semiconductor manufacturing and design",
            "은행": "Financial services sector including commercial and investment banking",
            "화학": "Chemical industry including petrochemicals and specialty chemicals",
            "철강": "Steel and metal production industry",
            "자동차": "Automotive manufacturing and related components",
            "건설": "Construction and real estate development",
            "조선": "Shipbuilding and marine engineering",
            "기계": "Industrial machinery and equipment manufacturing",
            "전기전자": "Electronics and electrical equipment industry",
            "IT": "Information technology and software services",
            "바이오": "Biotechnology and pharmaceutical industry",
            "게임": "Gaming and entertainment software",
            "소프트웨어": "Software development and IT services",
            "통신": "Telecommunications and network services"
        }
        
        return descriptions.get(sector_name, "Market sector")


class PerformanceTracker:
    """Track performance metrics for API calls and data processing"""
    
    @classmethod
    def create_performance_metrics(cls, start_time: datetime, end_time: datetime, 
                                 data_points: int = 0, cache_hits: int = 0) -> Dict[str, Any]:
        """Create performance metrics"""
        execution_time = (end_time - start_time).total_seconds()
        
        return {
            "execution_time": round(execution_time, 3),
            "data_points_processed": data_points,
            "cache_hits": cache_hits,
            "processing_rate": round(data_points / execution_time, 2) if execution_time > 0 else 0,
            "timestamp": end_time.isoformat()
        }