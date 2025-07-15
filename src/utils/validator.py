"""
Data validation and integrity checks
데이터 검증 및 무결성 검사
"""

import re
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, time
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation operation"""
    valid: bool
    errors: List[str]
    warnings: List[str]
    score: float = 0.0
    
    def add_error(self, error: str):
        """Add an error"""
        self.errors.append(error)
        self.valid = False
    
    def add_warning(self, warning: str):
        """Add a warning"""
        self.warnings.append(warning)


class DataValidator:
    """Enhanced data validation and integrity checks"""
    
    def __init__(self):
        # Valid markets
        self.valid_markets = {"KOSPI", "KOSDAQ", "ALL"}
        
        # Valid periods
        self.valid_periods = {"1D", "1W", "1M", "3M", "1Y"}
        
        # Valid intervals
        self.valid_intervals = {"1m", "5m", "15m", "30m", "1h", "1d"}
        
        # Korean market hours (KST)
        self.market_open_time = time(9, 0)  # 9:00 AM
        self.market_close_time = time(15, 30)  # 3:30 PM
        
        # Weekend days (Saturday=5, Sunday=6)
        self.weekend_days = {5, 6}
    
    def validate_chart_parameters(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate chart request parameters"""
        result = ValidationResult(valid=True, errors=[], warnings=[])
        
        # Validate market
        market = params.get("market", "").upper()
        if market not in self.valid_markets:
            result.add_error(f"Invalid market '{market}'. Must be one of: {', '.join(self.valid_markets)}")
        
        # Validate period
        period = params.get("period", "").upper()
        if period not in self.valid_periods:
            result.add_error(f"Invalid period '{period}'. Must be one of: {', '.join(self.valid_periods)}")
        
        # Validate interval
        interval = params.get("interval", "").lower()
        if interval not in self.valid_intervals:
            result.add_error(f"Invalid interval '{interval}'. Must be one of: {', '.join(self.valid_intervals)}")
        
        # Validate format option if provided
        format_option = params.get("format_option", "standard")
        valid_formats = {"standard", "detailed", "compact", "json"}
        if format_option not in valid_formats:
            result.add_error(f"Invalid format_option '{format_option}'. Must be one of: {', '.join(valid_formats)}")
        
        # Calculate validation score
        total_checks = 4
        passed_checks = total_checks - len(result.errors)
        result.score = passed_checks / total_checks if total_checks > 0 else 0.0
        
        return {
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "score": result.score
        }
    
    def validate_api_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Validate API response data integrity"""
        result = ValidationResult(valid=True, errors=[], warnings=[])
        data_issues = []
        
        # Check if response has expected structure
        if "output" not in response:
            result.add_error("Missing 'output' field in API response")
            return {
                "valid": False,
                "errors": result.errors,
                "warnings": result.warnings,
                "completeness_score": 0.0,
                "data_issues": ["Missing output field"]
            }
        
        output = response["output"]
        required_fields = {
            "bstp_nmix_prpr": "current price",
            "bstp_nmix_prdy_vrss": "price change",
            "bstp_nmix_prdy_ctrt": "change rate",
            "acml_vol": "volume"
        }
        
        present_fields = 0
        total_fields = len(required_fields)
        
        for field, description in required_fields.items():
            if field in output:
                present_fields += 1
                value = output[field]
                
                # Validate data types and values
                if field in ["bstp_nmix_prpr", "bstp_nmix_prdy_vrss", "bstp_nmix_prdy_ctrt"]:
                    # Should be numeric strings
                    if not isinstance(value, (str, int, float)):
                        data_issues.append(f"Invalid type for {description}: {type(value)}")
                        result.add_error(f"Invalid type for {description}")
                    elif isinstance(value, str):
                        try:
                            float_val = float(value)
                            # Check for reasonable price ranges
                            if field == "bstp_nmix_prpr" and (float_val < 0 or float_val > 1000000):
                                data_issues.append(f"Price out of reasonable range: {float_val}")
                                result.add_warning(f"Price seems unusual: {float_val}")
                        except ValueError:
                            data_issues.append(f"Cannot convert {description} to number: {value}")
                            result.add_error(f"Invalid numeric value for {description}")
                
                elif field == "acml_vol":
                    # Volume should be positive
                    if value is not None:
                        try:
                            vol_val = int(value) if isinstance(value, str) else value
                            if vol_val < 0:
                                data_issues.append(f"Negative volume: {vol_val}")
                                result.add_error("Volume cannot be negative")
                        except (ValueError, TypeError):
                            data_issues.append(f"Invalid volume value: {value}")
                            result.add_error("Invalid volume format")
            else:
                result.add_warning(f"Missing field: {description}")
        
        # Calculate completeness score
        completeness_score = present_fields / total_fields if total_fields > 0 else 0.0
        
        # Overall validation
        if completeness_score < 0.5:
            result.add_error("Response data is incomplete")
        
        return {
            "valid": result.valid,
            "errors": result.errors,
            "warnings": result.warnings,
            "completeness_score": completeness_score,
            "data_issues": data_issues
        }
    
    def validate_market_hours(self, timestamp: datetime) -> Dict[str, Any]:
        """Validate if timestamp is within market hours"""
        result = {
            "timestamp": timestamp.isoformat(),
            "is_market_hours": False,
            "is_weekend": False,
            "market_session": "closed"
        }
        
        # Check if it's weekend
        weekday = timestamp.weekday()
        if weekday in self.weekend_days:
            result["is_weekend"] = True
            result["market_session"] = "weekend"
            return result
        
        # Check time
        current_time = timestamp.time()
        
        if self.market_open_time <= current_time <= self.market_close_time:
            result["is_market_hours"] = True
            result["market_session"] = "trading"
        elif current_time < self.market_open_time:
            result["market_session"] = "pre_market"
        else:
            result["market_session"] = "after_hours"
        
        return result
    
    def validate_price_change(self, current_price: float, previous_price: float, 
                            max_change_percent: float = 30.0) -> Dict[str, Any]:
        """Validate price change is within reasonable bounds"""
        if previous_price == 0:
            return {
                "valid": False,
                "error": "Previous price cannot be zero",
                "change_percent": 0.0
            }
        
        change_percent = abs((current_price - previous_price) / previous_price) * 100
        
        result = {
            "valid": change_percent <= max_change_percent,
            "change_percent": change_percent,
            "current_price": current_price,
            "previous_price": previous_price,
            "max_allowed_change": max_change_percent
        }
        
        if not result["valid"]:
            result["error"] = f"Price change {change_percent:.2f}% exceeds maximum allowed {max_change_percent}%"
        
        return result
    
    def validate_volume_data(self, volume: int, historical_avg: Optional[int] = None) -> Dict[str, Any]:
        """Validate volume data"""
        result = {
            "valid": True,
            "volume": volume,
            "warnings": []
        }
        
        # Basic validation
        if volume < 0:
            result["valid"] = False
            result["error"] = "Volume cannot be negative"
            return result
        
        # Check against historical average if provided
        if historical_avg is not None and historical_avg > 0:
            volume_ratio = volume / historical_avg
            
            if volume_ratio > 10:  # 10x higher than average
                result["warnings"].append(f"Volume {volume} is {volume_ratio:.1f}x higher than average")
            elif volume_ratio < 0.1:  # 90% lower than average
                result["warnings"].append(f"Volume {volume} is unusually low ({volume_ratio:.1f}x average)")
        
        return result
    
    def validate_data_completeness(self, data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """Validate data completeness"""
        missing_fields = []
        present_fields = []
        
        for field in required_fields:
            if field in data and data[field] is not None:
                present_fields.append(field)
            else:
                missing_fields.append(field)
        
        completeness_score = len(present_fields) / len(required_fields) if required_fields else 0.0
        
        return {
            "completeness_score": completeness_score,
            "missing_fields": missing_fields,
            "present_fields": present_fields,
            "is_complete": len(missing_fields) == 0
        }
    
    def validate_timestamp_sequence(self, timestamps: List[datetime]) -> Dict[str, Any]:
        """Validate timestamp sequence is properly ordered"""
        result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        if len(timestamps) < 2:
            return result
        
        # Check for proper ordering
        for i in range(1, len(timestamps)):
            if timestamps[i] <= timestamps[i-1]:
                result["valid"] = False
                result["errors"].append(f"Timestamp at index {i} is not in ascending order")
        
        # Check for large gaps
        for i in range(1, len(timestamps)):
            gap = (timestamps[i] - timestamps[i-1]).total_seconds()
            if gap > 86400:  # More than 24 hours
                result["warnings"].append(f"Large time gap detected: {gap/3600:.1f} hours")
        
        return result
    
    def validate_numeric_range(self, value: Union[int, float], min_val: Optional[float] = None, 
                             max_val: Optional[float] = None, field_name: str = "value") -> Dict[str, Any]:
        """Validate numeric value is within acceptable range"""
        result = {
            "valid": True,
            "value": value,
            "field_name": field_name
        }
        
        if min_val is not None and value < min_val:
            result["valid"] = False
            result["error"] = f"{field_name} {value} is below minimum {min_val}"
        
        if max_val is not None and value > max_val:
            result["valid"] = False
            result["error"] = f"{field_name} {value} is above maximum {max_val}"
        
        return result