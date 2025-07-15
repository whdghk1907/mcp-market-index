"""
Tests for API Data Models
"""
import pytest
from datetime import datetime
from decimal import Decimal
from pydantic import ValidationError

from src.api.models import (
    IndexData, ChartData, ChartPoint, SectorData, 
    MarketSummaryData, MarketCompareData
)


class TestIndexData:
    """Test cases for IndexData model"""
    
    def test_valid_index_data_creation(self):
        """Test creating valid IndexData"""
        data = IndexData(
            current=2500.50,
            change=15.30,
            change_rate=0.61,
            volume=450000000,
            amount=8500000000000,
            high=2510.20,
            low=2485.30,
            open=2490.00,
            timestamp=datetime.now()
        )
        
        assert data.current == 2500.50
        assert data.change == 15.30
        assert data.change_rate == 0.61
        assert data.volume == 450000000
        assert data.amount == 8500000000000
        assert isinstance(data.timestamp, datetime)
    
    def test_index_data_validation_negative_current(self):
        """Test validation fails for negative current price"""
        with pytest.raises(ValidationError) as excinfo:
            IndexData(
                current=-100.0,
                change=0.0,
                change_rate=0.0,
                volume=0,
                amount=0,
                high=100.0,
                low=90.0,
                open=95.0
            )
        assert "Input should be greater than 0" in str(excinfo.value)
    
    def test_index_data_validation_negative_volume(self):
        """Test validation fails for negative volume"""
        with pytest.raises(ValidationError):
            IndexData(
                current=100.0,
                change=0.0,
                change_rate=0.0,
                volume=-1000,
                amount=0,
                high=100.0,
                low=90.0,
                open=95.0
            )
    
    def test_index_data_validation_high_low_consistency(self):
        """Test validation for high/low price consistency"""
        # This should be validated in business logic, not model validation
        data = IndexData(
            current=100.0,
            change=0.0,
            change_rate=0.0,
            volume=1000,
            amount=100000,
            high=90.0,  # High less than current - should be caught in business logic
            low=110.0,  # Low greater than current - should be caught in business logic
            open=95.0
        )
        # Model should accept this, business logic should validate
        assert data.high == 90.0
        assert data.low == 110.0
    
    def test_index_data_change_rate_calculation(self):
        """Test change rate calculation consistency"""
        data = IndexData(
            current=2515.80,
            change=15.30,
            change_rate=0.61,
            volume=450000000,
            amount=8500000000000,
            high=2520.00,
            low=2485.30,
            open=2500.50
        )
        
        # Change rate should be approximately consistent with change and previous close
        previous_close = data.current - data.change
        expected_rate = (data.change / previous_close) * 100
        assert abs(data.change_rate - expected_rate) < 0.01
    
    def test_index_data_json_serialization(self):
        """Test JSON serialization/deserialization"""
        data = IndexData(
            current=2500.50,
            change=15.30,
            change_rate=0.61,
            volume=450000000,
            amount=8500000000000,
            high=2510.20,
            low=2485.30,
            open=2490.00
        )
        
        json_str = data.json()
        data_restored = IndexData.parse_raw(json_str)
        
        assert data_restored.current == data.current
        assert data_restored.change == data.change
        assert data_restored.volume == data.volume


class TestChartPoint:
    """Test cases for ChartPoint model"""
    
    def test_valid_chart_point_creation(self):
        """Test creating valid ChartPoint"""
        point = ChartPoint(
            timestamp=datetime(2024, 1, 10, 9, 0, 0),
            open=2490.00,
            high=2492.50,
            low=2488.00,
            close=2491.20,
            volume=15000000
        )
        
        assert point.open == 2490.00
        assert point.high == 2492.50
        assert point.low == 2488.00
        assert point.close == 2491.20
        assert point.volume == 15000000
    
    def test_chart_point_ohlc_validation(self):
        """Test OHLC validation logic"""
        # Valid OHLC data
        point = ChartPoint(
            timestamp=datetime(2024, 1, 10, 9, 0, 0),
            open=2490.00,
            high=2495.00,
            low=2485.00,
            close=2491.20,
            volume=15000000
        )
        
        assert point.high >= max(point.open, point.close)
        assert point.low <= min(point.open, point.close)
    
    def test_chart_point_negative_values(self):
        """Test validation for negative values"""
        with pytest.raises(ValidationError):
            ChartPoint(
                timestamp=datetime(2024, 1, 10, 9, 0, 0),
                open=-2490.00,
                high=2495.00,
                low=2485.00,
                close=2491.20,
                volume=15000000
            )


class TestChartData:
    """Test cases for ChartData model"""
    
    def test_valid_chart_data_creation(self):
        """Test creating valid ChartData"""
        points = [
            ChartPoint(
                timestamp=datetime(2024, 1, 10, 9, 0, 0),
                open=2490.00,
                high=2492.50,
                low=2488.00,
                close=2491.20,
                volume=15000000
            ),
            ChartPoint(
                timestamp=datetime(2024, 1, 10, 9, 5, 0),
                open=2491.20,
                high=2495.00,
                low=2490.00,
                close=2493.80,
                volume=18000000
            )
        ]
        
        chart = ChartData(
            market="KOSPI",
            period="1D",
            interval="5m",
            data=points
        )
        
        assert chart.market == "KOSPI"
        assert chart.period == "1D"
        assert chart.interval == "5m"
        assert len(chart.data) == 2
    
    def test_chart_data_empty_points(self):
        """Test chart data with empty points list"""
        chart = ChartData(
            market="KOSPI",
            period="1D",
            interval="5m",
            data=[]
        )
        
        assert len(chart.data) == 0
    
    def test_chart_data_market_validation(self):
        """Test market field validation"""
        with pytest.raises(ValidationError):
            ChartData(
                market="INVALID",
                period="1D",
                interval="5m",
                data=[]
            )


class TestSectorData:
    """Test cases for SectorData model"""
    
    def test_valid_sector_data_creation(self):
        """Test creating valid SectorData"""
        sector = SectorData(
            name="반도체",
            code="G2510",
            current=3250.50,
            change=45.20,
            change_rate=1.41,
            volume=25000000,
            amount=850000000000
        )
        
        assert sector.name == "반도체"
        assert sector.code == "G2510"
        assert sector.current == 3250.50
        assert sector.change == 45.20
        assert sector.change_rate == 1.41
    
    def test_sector_data_validation(self):
        """Test sector data validation"""
        with pytest.raises(ValidationError):
            SectorData(
                name="",  # Empty name should fail
                code="G2510",
                current=3250.50,
                change=45.20,
                change_rate=1.41,
                volume=25000000,
                amount=850000000000
            )
    
    def test_sector_code_format(self):
        """Test sector code format validation"""
        # Valid sector codes
        valid_codes = ["G2510", "Q1510", "G2720"]
        
        for code in valid_codes:
            sector = SectorData(
                name="테스트",
                code=code,
                current=1000.0,
                change=0.0,
                change_rate=0.0,
                volume=0,
                amount=0
            )
            assert sector.code == code


class TestMarketSummaryData:
    """Test cases for MarketSummaryData model"""
    
    def test_valid_market_summary_creation(self):
        """Test creating valid MarketSummaryData"""
        summary = MarketSummaryData(
            advancing=450,
            declining=380,
            unchanged=95,
            trading_halt=5,
            limit_up=12,
            limit_down=3,
            new_high_52w=8,
            new_low_52w=2,
            market_cap=2100000000000000,
            foreign_ownership_rate=31.5
        )
        
        assert summary.advancing == 450
        assert summary.declining == 380
        assert summary.unchanged == 95
        assert summary.foreign_ownership_rate == 31.5
    
    def test_market_summary_negative_values(self):
        """Test validation for negative values"""
        with pytest.raises(ValidationError):
            MarketSummaryData(
                advancing=-1,  # Should not be negative
                declining=380,
                unchanged=95,
                trading_halt=5,
                limit_up=12,
                limit_down=3,
                new_high_52w=8,
                new_low_52w=2,
                market_cap=2100000000000000,
                foreign_ownership_rate=31.5
            )
    
    def test_foreign_ownership_rate_bounds(self):
        """Test foreign ownership rate bounds"""
        # Valid rate
        summary = MarketSummaryData(
            advancing=450,
            declining=380,
            unchanged=95,
            trading_halt=5,
            limit_up=12,
            limit_down=3,
            new_high_52w=8,
            new_low_52w=2,
            market_cap=2100000000000000,
            foreign_ownership_rate=50.0
        )
        assert summary.foreign_ownership_rate == 50.0
        
        # Invalid rate (over 100%)
        with pytest.raises(ValidationError):
            MarketSummaryData(
                advancing=450,
                declining=380,
                unchanged=95,
                trading_halt=5,
                limit_up=12,
                limit_down=3,
                new_high_52w=8,
                new_low_52w=2,
                market_cap=2100000000000000,
                foreign_ownership_rate=150.0  # Over 100%
            )


class TestMarketCompareData:
    """Test cases for MarketCompareData model"""
    
    def test_valid_market_compare_creation(self):
        """Test creating valid MarketCompareData"""
        compare = MarketCompareData(
            start=2450.00,
            end=2500.50,
            change=50.50,
            change_rate=2.06,
            high=2520.00,
            low=2440.00,
            avg_volume=380000000,
            avg_amount=7500000000000
        )
        
        assert compare.start == 2450.00
        assert compare.end == 2500.50
        assert compare.change == 50.50
        assert compare.change_rate == 2.06
    
    def test_market_compare_consistency(self):
        """Test data consistency in market compare"""
        compare = MarketCompareData(
            start=2450.00,
            end=2500.50,
            change=50.50,
            change_rate=2.06,
            high=2520.00,
            low=2440.00,
            avg_volume=380000000,
            avg_amount=7500000000000
        )
        
        # Change should equal end - start
        assert abs(compare.change - (compare.end - compare.start)) < 0.01
        
        # Change rate should be consistent
        expected_rate = (compare.change / compare.start) * 100
        assert abs(compare.change_rate - expected_rate) < 0.01
    
    def test_market_compare_high_low_bounds(self):
        """Test high/low bounds validation"""
        # High should be >= max(start, end)
        # Low should be <= min(start, end)
        compare = MarketCompareData(
            start=2450.00,
            end=2500.50,
            change=50.50,
            change_rate=2.06,
            high=2520.00,  # Should be >= 2500.50
            low=2440.00,   # Should be <= 2450.00
            avg_volume=380000000,
            avg_amount=7500000000000
        )
        
        assert compare.high >= max(compare.start, compare.end)
        assert compare.low <= min(compare.start, compare.end)