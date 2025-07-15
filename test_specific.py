"""
Specific tests for API models validation
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.api.models import (
    IndexData, ChartData, ChartPoint, SectorData, 
    MarketSummaryData, MarketCompareData
)


def test_index_data_validation():
    """Test IndexData validation"""
    # Valid data should work
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
    assert data.current == 2500.50
    
    # Negative current should fail
    with pytest.raises(ValidationError):
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


def test_chart_data_validation():
    """Test ChartData validation"""
    point = ChartPoint(
        timestamp=datetime(2024, 1, 10, 9, 0, 0),
        open=2490.00,
        high=2492.50,
        low=2488.00,
        close=2491.20,
        volume=15000000
    )
    
    # Valid market should work
    chart = ChartData(
        market="KOSPI",
        period="1D",
        interval="5m",
        data=[point]
    )
    assert chart.market == "KOSPI"
    
    # Invalid market should fail
    with pytest.raises(ValidationError):
        ChartData(
            market="INVALID",
            period="1D",
            interval="5m",
            data=[]
        )


def test_sector_data_validation():
    """Test SectorData validation"""
    # Valid data should work
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
    
    # Empty name should fail
    with pytest.raises(ValidationError):
        SectorData(
            name="",
            code="G2510",
            current=3250.50,
            change=45.20,
            change_rate=1.41,
            volume=25000000,
            amount=850000000000
        )


def test_market_summary_validation():
    """Test MarketSummaryData validation"""
    # Valid data should work
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
    
    # Negative values should fail
    with pytest.raises(ValidationError):
        MarketSummaryData(
            advancing=-1,
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
    
    # Foreign ownership rate over 100% should fail
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
            foreign_ownership_rate=150.0
        )


def test_market_compare_data():
    """Test MarketCompareData"""
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
    
    # Test data consistency
    assert abs(compare.change - (compare.end - compare.start)) < 0.01
    
    # Test high/low bounds
    assert compare.high >= max(compare.start, compare.end)
    assert compare.low <= min(compare.start, compare.end)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])