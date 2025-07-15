"""
Data models for Korea Investment API responses
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class IndexData(BaseModel):
    """Index data model"""
    current: float = Field(..., gt=0, description="Current index value")
    change: float = Field(..., description="Change from previous close")
    change_rate: float = Field(..., description="Change rate percentage")
    volume: int = Field(..., ge=0, description="Trading volume")
    amount: int = Field(..., ge=0, description="Trading amount")
    high: float = Field(..., gt=0, description="Day high")
    low: float = Field(..., gt=0, description="Day low") 
    open: float = Field(..., gt=0, description="Day open")
    timestamp: datetime = Field(default_factory=datetime.now, description="Data timestamp")


class ChartPoint(BaseModel):
    """Single chart data point"""
    timestamp: datetime = Field(..., description="Data timestamp")
    open: float = Field(..., gt=0, description="Open price")
    high: float = Field(..., gt=0, description="High price")
    low: float = Field(..., gt=0, description="Low price")
    close: float = Field(..., gt=0, description="Close price")
    volume: int = Field(..., ge=0, description="Volume")


class ChartData(BaseModel):
    """Chart data collection"""
    market: str = Field(..., description="Market name")
    period: str = Field(..., description="Chart period")
    interval: str = Field(..., description="Chart interval")
    data: List[ChartPoint] = Field(default_factory=list, description="Chart data points")
    
    @field_validator('market')
    @classmethod
    def validate_market(cls, v):
        if v not in ['KOSPI', 'KOSDAQ']:
            raise ValueError(f'Invalid market: {v}')
        return v


class SectorData(BaseModel):
    """Sector index data"""
    name: str = Field(..., min_length=1, description="Sector name")
    code: str = Field(..., description="Sector code")
    current: float = Field(..., gt=0, description="Current index value")
    change: float = Field(..., description="Change from previous close")
    change_rate: float = Field(..., description="Change rate percentage")
    volume: int = Field(..., ge=0, description="Trading volume")
    amount: int = Field(..., ge=0, description="Trading amount")


class MarketSummaryData(BaseModel):
    """Market summary statistics"""
    advancing: int = Field(..., ge=0, description="Number of advancing stocks")
    declining: int = Field(..., ge=0, description="Number of declining stocks") 
    unchanged: int = Field(..., ge=0, description="Number of unchanged stocks")
    trading_halt: int = Field(..., ge=0, description="Number of trading halt stocks")
    limit_up: int = Field(..., ge=0, description="Number of limit up stocks")
    limit_down: int = Field(..., ge=0, description="Number of limit down stocks")
    new_high_52w: int = Field(..., ge=0, description="Number of 52-week high stocks")
    new_low_52w: int = Field(..., ge=0, description="Number of 52-week low stocks")
    market_cap: int = Field(..., ge=0, description="Total market cap")
    foreign_ownership_rate: float = Field(..., ge=0, le=100, description="Foreign ownership rate")


class MarketCompareData(BaseModel):
    """Market comparison data"""
    start: float = Field(..., gt=0, description="Start value")
    end: float = Field(..., gt=0, description="End value")
    change: float = Field(..., description="Change value")
    change_rate: float = Field(..., description="Change rate percentage")
    high: float = Field(..., gt=0, description="Period high")
    low: float = Field(..., gt=0, description="Period low")
    avg_volume: int = Field(..., ge=0, description="Average volume")
    avg_amount: int = Field(..., ge=0, description="Average amount")