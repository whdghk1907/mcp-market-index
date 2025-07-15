# 📊 시장 지수 MCP 서버 개발 계획서

## 1. 프로젝트 개요

### 1.1 목적
실시간 한국 주식시장 지수(코스피/코스닥) 데이터를 제공하는 MCP 서버 구축

### 1.2 범위
- 코스피/코스닥 현재 지수 및 등락률
- 지수 차트 데이터 (일중/일별/주별/월별)
- 시장 전체 요약 정보 (거래량, 거래대금, 시가총액)
- 업종별 지수 정보

### 1.3 기술 스택
- **언어**: Python 3.11+
- **MCP SDK**: mcp-python
- **API Client**: 한국투자증권 OpenAPI
- **비동기 처리**: asyncio, aiohttp
- **데이터 검증**: pydantic
- **캐싱**: 내장 메모리 캐시

## 2. 서버 아키텍처

```
mcp-market-index/
├── src/
│   ├── server.py           # MCP 서버 메인
│   ├── tools/              # MCP 도구 정의
│   │   ├── __init__.py
│   │   ├── index_tools.py  # 지수 관련 도구
│   │   └── market_tools.py # 시장 요약 도구
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py       # 한국투자증권 API 클라이언트
│   │   └── models.py       # 데이터 모델
│   ├── utils/
│   │   ├── cache.py        # 캐시 관리
│   │   ├── formatter.py    # 데이터 포맷팅
│   │   └── validator.py    # 데이터 검증
│   └── config.py           # 설정 관리
├── tests/
│   ├── test_tools.py
│   └── test_api.py
├── requirements.txt
├── .env.example
└── README.md
```

## 3. 핵심 기능 명세

### 3.1 제공 도구 (Tools)

#### 1) `get_market_index`
```python
@tool
async def get_market_index(market: Literal["KOSPI", "KOSDAQ", "ALL"] = "ALL") -> dict:
    """
    현재 시장 지수 조회
    
    Parameters:
        market: 조회할 시장 (KOSPI, KOSDAQ, ALL)
    
    Returns:
        {
            "timestamp": "2024-01-10T10:30:00+09:00",
            "kospi": {
                "current": 2500.50,
                "change": 15.30,
                "change_rate": 0.61,
                "volume": 450000000,
                "amount": 8500000000000,
                "high": 2510.20,
                "low": 2485.30,
                "open": 2490.00
            },
            "kosdaq": {
                "current": 850.25,
                "change": -5.10,
                "change_rate": -0.60,
                "volume": 850000000,
                "amount": 5200000000000,
                "high": 855.00,
                "low": 848.50,
                "open": 853.00
            }
        }
    """
```

#### 2) `get_index_chart`
```python
@tool
async def get_index_chart(
    market: Literal["KOSPI", "KOSDAQ"], 
    period: Literal["1D", "1W", "1M", "3M", "1Y"] = "1D",
    interval: Literal["1m", "5m", "30m", "1h", "1d"] = "5m"
) -> dict:
    """
    지수 차트 데이터 조회
    
    Parameters:
        market: 시장 구분
        period: 조회 기간
        interval: 데이터 간격
    
    Returns:
        {
            "market": "KOSPI",
            "period": "1D",
            "interval": "5m",
            "data": [
                {
                    "timestamp": "2024-01-10T09:00:00+09:00",
                    "open": 2490.00,
                    "high": 2492.50,
                    "low": 2488.00,
                    "close": 2491.20,
                    "volume": 15000000
                },
                ...
            ]
        }
    """
```

#### 3) `get_market_summary`
```python
@tool
async def get_market_summary() -> dict:
    """
    시장 전체 요약 정보 조회
    
    Returns:
        {
            "timestamp": "2024-01-10T10:30:00+09:00",
            "kospi": {
                "advancing": 450,
                "declining": 380,
                "unchanged": 95,
                "trading_halt": 5,
                "limit_up": 12,
                "limit_down": 3,
                "new_high_52w": 8,
                "new_low_52w": 2,
                "market_cap": 2100000000000000,  # 조 단위
                "foreign_ownership_rate": 31.5
            },
            "kosdaq": {
                "advancing": 750,
                "declining": 620,
                "unchanged": 180,
                "trading_halt": 8,
                "limit_up": 25,
                "limit_down": 5,
                "new_high_52w": 15,
                "new_low_52w": 7,
                "market_cap": 450000000000000,
                "foreign_ownership_rate": 8.2
            }
        }
    """
```

#### 4) `get_sector_indices`
```python
@tool
async def get_sector_indices(market: Literal["KOSPI", "KOSDAQ"] = "KOSPI") -> dict:
    """
    업종별 지수 조회
    
    Parameters:
        market: 시장 구분
    
    Returns:
        {
            "market": "KOSPI",
            "timestamp": "2024-01-10T10:30:00+09:00",
            "sectors": [
                {
                    "name": "반도체",
                    "code": "G2510",
                    "current": 3250.50,
                    "change": 45.20,
                    "change_rate": 1.41,
                    "volume": 25000000,
                    "amount": 850000000000
                },
                {
                    "name": "은행",
                    "code": "G2710",
                    "current": 850.30,
                    "change": -2.10,
                    "change_rate": -0.25,
                    "volume": 8500000,
                    "amount": 120000000000
                },
                ...
            ]
        }
    """
```

#### 5) `get_market_compare`
```python
@tool
async def get_market_compare(
    date_from: str = None,
    date_to: str = None
) -> dict:
    """
    시장 지수 비교 (기간별 변화)
    
    Parameters:
        date_from: 시작일 (YYYY-MM-DD)
        date_to: 종료일 (YYYY-MM-DD)
    
    Returns:
        {
            "period": {
                "from": "2024-01-01",
                "to": "2024-01-10"
            },
            "kospi": {
                "start": 2450.00,
                "end": 2500.50,
                "change": 50.50,
                "change_rate": 2.06,
                "high": 2520.00,
                "low": 2440.00,
                "avg_volume": 380000000,
                "avg_amount": 7500000000000
            },
            "kosdaq": {
                "start": 830.00,
                "end": 850.25,
                "change": 20.25,
                "change_rate": 2.44,
                "high": 865.00,
                "low": 825.50,
                "avg_volume": 750000000,
                "avg_amount": 4800000000000
            }
        }
    """
```

## 4. API 클라이언트 구현

### 4.1 한국투자증권 API 클라이언트

```python
# src/api/client.py
import aiohttp
import asyncio
from typing import Dict, Optional
from datetime import datetime, timedelta
import hashlib
import json

class KoreaInvestmentAPI:
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.base_url = "https://openapi.koreainvestment.com:9443"
        self.access_token = None
        self.token_expires = None
        
    async def _get_access_token(self):
        """액세스 토큰 발급/갱신"""
        if self.access_token and self.token_expires > datetime.now():
            return self.access_token
            
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/oauth2/tokenP",
                headers=headers,
                json=body
            ) as resp:
                data = await resp.json()
                self.access_token = data["access_token"]
                self.token_expires = datetime.now() + timedelta(seconds=data["expires_in"])
                
        return self.access_token
    
    async def get_index_price(self, index_code: str) -> Dict:
        """지수 현재가 조회"""
        token = await self._get_access_token()
        
        headers = {
            "authorization": f"Bearer {token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKUP03500100"
        }
        
        params = {
            "FID_COND_MRKT_DIV_CODE": "U",
            "FID_INPUT_ISCD": index_code  # 0001: KOSPI, 1001: KOSDAQ
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-index-price",
                headers=headers,
                params=params
            ) as resp:
                return await resp.json()
    
    async def get_index_chart_data(
        self, 
        index_code: str, 
        period_div_code: str,
        input_date: str = ""
    ) -> Dict:
        """지수 차트 데이터 조회"""
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
            async with session.get(
                f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-index-chart-price",
                headers=headers,
                params=params
            ) as resp:
                return await resp.json()
```

## 5. 캐싱 전략

```python
# src/utils/cache.py
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import asyncio

class MarketDataCache:
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        
    async def get_or_fetch(
        self, 
        key: str, 
        fetch_func, 
        ttl: int = 5  # 기본 5초 캐시
    ) -> Any:
        """캐시에서 가져오거나 새로 fetch"""
        # 캐시 확인
        if key in self._cache:
            cached = self._cache[key]
            if cached['expires'] > datetime.now():
                return cached['data']
        
        # Lock을 사용해 중복 요청 방지
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
            
        async with self._locks[key]:
            # 다시 한번 캐시 확인 (race condition 방지)
            if key in self._cache:
                cached = self._cache[key]
                if cached['expires'] > datetime.now():
                    return cached['data']
            
            # 새로 fetch
            data = await fetch_func()
            
            # 캐시 저장
            self._cache[key] = {
                'data': data,
                'expires': datetime.now() + timedelta(seconds=ttl)
            }
            
            return data
    
    def invalidate(self, key: str = None):
        """캐시 무효화"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 반환"""
        total_keys = len(self._cache)
        valid_keys = sum(1 for v in self._cache.values() 
                        if v['expires'] > datetime.now())
        
        return {
            'total_keys': total_keys,
            'valid_keys': valid_keys,
            'expired_keys': total_keys - valid_keys
        }
```

## 6. 에러 처리 및 재시도

```python
# src/utils/retry.py
import asyncio
from functools import wraps
from typing import TypeVar, Callable, Union
import logging

T = TypeVar('T')
logger = logging.getLogger(__name__)

class APIError(Exception):
    """API 호출 관련 에러"""
    pass

class RateLimitError(APIError):
    """Rate Limit 에러"""
    pass

def retry_on_error(
    max_attempts: int = 3, 
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (APIError,)
):
    """API 호출 재시도 데코레이터"""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            attempt_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if isinstance(e, RateLimitError):
                        # Rate limit의 경우 더 긴 대기
                        attempt_delay = 60.0
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_attempts} failed: {str(e)}"
                    )
                    
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(attempt_delay)
                        attempt_delay *= backoff
                    else:
                        logger.error(f"All {max_attempts} attempts failed")
                        raise
                        
            raise last_exception
            
        return wrapper
    return decorator
```

## 7. 구현 일정

### Phase 1: 기초 구현 (3일)
- [ ] 프로젝트 구조 설정
- [ ] MCP 서버 기본 설정
- [ ] 한국투자증권 API 클라이언트 구현
- [ ] 기본 지수 조회 도구 구현

### Phase 2: 핵심 기능 (4일)
- [ ] 모든 도구(tools) 구현
- [ ] 캐싱 시스템 구현
- [ ] 에러 처리 및 재시도 로직
- [ ] 데이터 포맷팅 및 검증

### Phase 3: 고도화 (3일)
- [ ] 성능 최적화
- [ ] 로깅 시스템
- [ ] 단위 테스트 작성
- [ ] 문서화

## 8. 테스트 계획

### 8.1 단위 테스트
```python
# tests/test_tools.py
import pytest
from src.tools.index_tools import get_market_index
from src.utils.cache import MarketDataCache

@pytest.mark.asyncio
async def test_get_market_index():
    """시장 지수 조회 테스트"""
    result = await get_market_index("ALL")
    
    assert "kospi" in result
    assert "kosdaq" in result
    assert "timestamp" in result
    
    # KOSPI 데이터 검증
    kospi = result["kospi"]
    assert all(key in kospi for key in ["current", "change", "change_rate"])
    assert isinstance(kospi["current"], float)
    assert kospi["current"] > 0

@pytest.mark.asyncio
async def test_cache_functionality():
    """캐시 기능 테스트"""
    cache = MarketDataCache()
    
    call_count = 0
    async def fetch_func():
        nonlocal call_count
        call_count += 1
        return {"data": "test"}
    
    # 첫 호출
    result1 = await cache.get_or_fetch("test_key", fetch_func, ttl=1)
    assert call_count == 1
    
    # 캐시된 데이터 반환
    result2 = await cache.get_or_fetch("test_key", fetch_func, ttl=1)
    assert call_count == 1  # fetch_func이 다시 호출되지 않음
    assert result1 == result2
    
    # TTL 만료 후
    await asyncio.sleep(1.1)
    result3 = await cache.get_or_fetch("test_key", fetch_func, ttl=1)
    assert call_count == 2  # fetch_func이 다시 호출됨
```

### 8.2 통합 테스트
- API 연동 테스트
- 캐시 동작 테스트
- 에러 시나리오 테스트
- 부하 테스트

## 9. 배포 및 운영

### 9.1 환경 설정
```bash
# .env 파일
KOREA_INVESTMENT_APP_KEY=your_app_key
KOREA_INVESTMENT_APP_SECRET=your_app_secret
CACHE_TTL_SECONDS=5
LOG_LEVEL=INFO
MAX_RETRY_ATTEMPTS=3
RATE_LIMIT_PER_MINUTE=100
```

### 9.2 Docker 설정
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "src.server"]
```

### 9.3 실행 방법
```bash
# 개발 환경
python -m src.server

# Docker
docker build -t mcp-market-index .
docker run -p 8080:8080 --env-file .env mcp-market-index

# Docker Compose
docker-compose up -d
```

## 10. 모니터링 및 유지보수

### 10.1 로깅 설정
```python
# src/utils/logger.py
import logging
import sys
from datetime import datetime

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """로거 설정"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(
        f"logs/{name}_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler.setLevel(logging.DEBUG)
    
    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger
```

### 10.2 메트릭 수집
```python
# src/utils/metrics.py
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

@dataclass
class APIMetric:
    endpoint: str
    response_time: float
    status_code: int
    timestamp: datetime
    
class MetricsCollector:
    def __init__(self):
        self.metrics: List[APIMetric] = []
        
    def record_api_call(
        self, 
        endpoint: str, 
        response_time: float, 
        status_code: int
    ):
        """API 호출 메트릭 기록"""
        metric = APIMetric(
            endpoint=endpoint,
            response_time=response_time,
            status_code=status_code,
            timestamp=datetime.now()
        )
        self.metrics.append(metric)
        
    def get_stats(self) -> Dict:
        """통계 반환"""
        if not self.metrics:
            return {}
            
        total_calls = len(self.metrics)
        avg_response_time = sum(m.response_time for m in self.metrics) / total_calls
        error_rate = sum(1 for m in self.metrics if m.status_code >= 400) / total_calls
        
        return {
            'total_calls': total_calls,
            'avg_response_time': avg_response_time,
            'error_rate': error_rate * 100,
            'last_call': self.metrics[-1].timestamp
        }
```

### 10.3 알림 설정
- API 장애 감지
- 비정상 데이터 감지
- 캐시 메모리 사용량
- Rate Limit 도달 경고

## 11. 보안 고려사항

### 11.1 API 키 관리
- 환경 변수로 민감 정보 분리
- `.env` 파일 git ignore
- 키 로테이션 주기 설정

### 11.2 요청 검증
- 입력 파라미터 검증
- SQL Injection 방지
- Rate Limiting 구현

### 11.3 통신 보안
- HTTPS 사용
- API 응답 데이터 암호화
- 로그에 민감 정보 제외

이 계획서를 통해 안정적이고 효율적인 시장 지수 MCP 서버를 구축할 수 있습니다.