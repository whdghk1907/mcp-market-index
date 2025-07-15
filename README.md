# 📊 MCP Market Index Server

한국 주식시장 지수 데이터를 제공하는 MCP (Model Context Protocol) 서버입니다.

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일에서 한국투자증권 API 키 설정
```

### 2. 한국투자증권 API 키 발급

1. [한국투자증권 OpenAPI](https://apiportal.koreainvestment.com) 접속
2. 회원가입 및 앱 등록
3. APP_KEY, APP_SECRET 발급
4. `.env` 파일에 키 정보 입력

### 3. 서버 실행

```bash
python -m src.server
```

## 📋 제공 기능

### 1. 시장 지수 조회 (`get_market_index`)
- 코스피/코스닥 현재 지수 및 등락률
- 거래량, 거래대금 정보
- 일중 고가/저가/시가 데이터

### 2. 지수 차트 데이터 (`get_index_chart`)
- 기간별 차트 데이터 (1D, 1W, 1M, 3M, 1Y)
- 다양한 시간 간격 (1분, 5분, 30분, 1시간, 1일)
- OHLC + 거래량 데이터

### 3. 시장 요약 정보 (`get_market_summary`)
- 상승/하락/보합 종목 수
- 상한가/하한가 종목 수
- 52주 신고가/신저가 종목 수
- 시가총액 및 외국인 지분율

### 4. 업종별 지수 (`get_sector_indices`)
- 코스피/코스닥 주요 업종별 지수
- 업종별 등락률 및 거래 정보

### 5. 시장 비교 (`get_market_compare`)
- 기간별 시장 지수 변화
- 코스피/코스닥 상대 성과 분석

## 🛠️ 개발 환경 설정

### 가상환경 생성
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
```

### 개발 의존성 설치
```bash
pip install -e ".[dev]"
```

### 코드 포맷팅
```bash
black src/ tests/
isort src/ tests/
```

### 린팅
```bash
flake8 src/ tests/
mypy src/
```

### 테스트 실행
```bash
pytest
pytest --cov=src tests/  # 커버리지 포함
```

## 📁 프로젝트 구조

```
mcp-market-index/
├── src/
│   ├── __init__.py
│   ├── server.py           # MCP 서버 메인
│   ├── config.py           # 설정 관리
│   ├── tools/              # MCP 도구 구현
│   │   ├── __init__.py
│   │   ├── index_tools.py  # 지수 관련 도구
│   │   └── market_tools.py # 시장 요약 도구
│   ├── api/                # API 클라이언트
│   │   ├── __init__.py
│   │   ├── client.py       # 한국투자증권 API
│   │   └── models.py       # 데이터 모델
│   └── utils/              # 유틸리티
│       ├── __init__.py
│       ├── cache.py        # 캐시 관리
│       ├── logger.py       # 로깅 설정
│       └── retry.py        # 재시도 로직
├── tests/                  # 테스트 파일
├── logs/                   # 로그 파일
├── docs/                   # 문서
├── requirements.txt        # 의존성 목록
├── pyproject.toml         # 프로젝트 설정
├── .env.example           # 환경변수 템플릿
└── README.md
```

## ⚙️ 설정 옵션

### 캐시 설정
- `CACHE_TTL_SECONDS`: 일반 데이터 캐시 TTL (기본값: 5초)
- `CACHE_CHART_TTL_SECONDS`: 차트 데이터 캐시 TTL (기본값: 30초)
- `CACHE_SUMMARY_TTL_SECONDS`: 요약 데이터 캐시 TTL (기본값: 10초)

### API 제한 설정
- `MAX_REQUESTS_PER_MINUTE`: 분당 최대 요청 수 (기본값: 100)
- `MAX_RETRY_ATTEMPTS`: 최대 재시도 횟수 (기본값: 3)
- `RETRY_DELAY_SECONDS`: 재시도 지연 시간 (기본값: 1.0초)

### 로깅 설정
- `LOG_LEVEL`: 로그 레벨 (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE_PATH`: 로그 파일 경로

## 🔒 보안 고려사항

- API 키는 환경변수로 관리
- `.env` 파일은 git에 포함하지 않음
- 로그에 민감 정보 기록 금지
- Rate limiting으로 API 사용량 제어

## 📊 모니터링

서버는 다음 메트릭을 수집합니다:
- API 응답 시간
- 캐시 히트율
- 에러율
- 메모리 사용량

## 🤝 기여하기

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for your changes
5. Run tests and ensure they pass
6. Submit a pull request

## 📄 라이선스

MIT License

## 🆘 지원

문제가 발생하면 GitHub Issues에 등록해주세요.