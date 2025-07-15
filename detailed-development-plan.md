# 📊 시장 지수 MCP 서버 상세 개발 계획서

## 📝 프로젝트 분석 요약

기존 계획서를 분석한 결과, 한국 주식시장 지수 데이터를 제공하는 MCP 서버 개발 프로젝트로 다음과 같은 핵심 요소들이 포함되어 있습니다:

- **목적**: 실시간 코스피/코스닥 지수 데이터 제공
- **기술 스택**: Python 3.11+, mcp-python, 한국투자증권 OpenAPI
- **핵심 기능**: 5개 주요 도구(지수 조회, 차트, 시장 요약, 업종별 지수, 비교)

## 🎯 상세 개발 계획

### Phase 1: 환경 설정 및 기초 구조 (1-2일)

#### 1.1 개발 환경 초기화
```bash
# 프로젝트 구조 생성
mkdir -p src/{tools,api,utils} tests logs
touch requirements.txt .env.example README.md
```

#### 1.2 의존성 관리
```python
# requirements.txt
mcp-python>=0.5.0
aiohttp>=3.8.0
pydantic>=2.0.0
python-dotenv>=1.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
```

#### 1.3 기본 설정 파일 구성
- `src/config.py`: 환경 변수 및 설정 관리
- `.env.example`: 환경 변수 템플릿
- `pyproject.toml`: 프로젝트 메타데이터

### Phase 2: 한국투자증권 API 클라이언트 구현 (2-3일)

#### 2.1 API 클라이언트 기본 구조
```python
# src/api/client.py 구현 순서:
1. 기본 클래스 구조 및 초기화
2. 토큰 발급/갱신 메서드
3. 지수 현재가 조회 API
4. 지수 차트 데이터 API
5. 업종별 지수 API
```

#### 2.2 데이터 모델 정의
```python
# src/api/models.py
- IndexData: 지수 현재가 데이터
- ChartData: 차트 데이터
- SectorData: 업종별 지수 데이터
- MarketSummary: 시장 요약 데이터
```

#### 2.3 API 응답 처리 및 검증
- 한국투자증권 API 응답 형식 분석
- Pydantic 모델을 통한 데이터 검증
- 에러 응답 처리 로직

### Phase 3: 캐싱 시스템 구현 (1일)

#### 3.1 캐시 매니저 구현
```python
# src/utils/cache.py 기능:
- 메모리 기반 캐시 (TTL 지원)
- 비동기 Lock을 통한 중복 요청 방지
- 캐시 통계 및 모니터링
- 캐시 무효화 기능
```

#### 3.2 캐시 전략 설정
- 실시간 지수: 5초 TTL
- 차트 데이터: 30초 TTL
- 시장 요약: 10초 TTL
- 업종별 지수: 10초 TTL

### Phase 4: MCP 도구 구현 (3-4일)

#### 4.1 도구별 구현 순서

**Day 1: 기본 지수 조회**
```python
# src/tools/index_tools.py
1. get_market_index() 구현
   - KOSPI/KOSDAQ 현재가 조회
   - 데이터 포맷팅 및 반환
   - 캐시 연동
```

**Day 2: 차트 데이터**
```python
# src/tools/index_tools.py
2. get_index_chart() 구현
   - 기간별/간격별 차트 데이터
   - 파라미터 검증
   - 대용량 데이터 처리
```

**Day 3: 시장 요약 및 업종별 지수**
```python
# src/tools/market_tools.py
3. get_market_summary() 구현
4. get_sector_indices() 구현
   - 복수 API 호출 최적화
   - 병렬 처리 구현
```

**Day 4: 비교 도구 및 통합**
```python
# src/tools/market_tools.py
5. get_market_compare() 구현
   - 기간별 변화율 계산
   - 통계 데이터 생성
```

#### 4.2 도구 등록 및 MCP 서버 설정
```python
# src/server.py
- MCP 서버 초기화
- 모든 도구 등록
- 에러 핸들링 미들웨어
- 로깅 설정
```

### Phase 5: 에러 처리 및 안정성 (1-2일)

#### 5.1 재시도 로직 구현
```python
# src/utils/retry.py
- 지수 백오프 재시도
- Rate Limit 처리
- API 장애 대응
- 커스텀 예외 정의
```

#### 5.2 데이터 검증 강화
```python
# src/utils/validator.py
- 입력 파라미터 검증
- API 응답 데이터 무결성 확인
- 비즈니스 로직 검증
```

### Phase 6: 로깅 및 모니터링 (1일)

#### 6.1 로깅 시스템 구현
```python
# src/utils/logger.py
- 구조화된 로깅
- 파일 및 콘솔 출력
- 로그 레벨별 필터링
```

#### 6.2 메트릭 수집
```python
# src/utils/metrics.py
- API 응답 시간 측정
- 캐시 히트율 모니터링
- 에러율 추적
```

### Phase 7: 테스트 작성 (2일)

#### 7.1 단위 테스트
```python
# tests/test_tools.py
- 각 도구별 기능 테스트
- 모킹을 통한 API 호출 테스트
- 파라미터 검증 테스트
```

#### 7.2 통합 테스트
```python
# tests/test_integration.py
- 실제 API 연동 테스트
- 캐시 동작 테스트
- 에러 시나리오 테스트
```

#### 7.3 성능 테스트
```python
# tests/test_performance.py
- 동시 요청 처리 테스트
- 메모리 사용량 모니터링
- 응답 시간 벤치마크
```

### Phase 8: 문서화 및 배포 준비 (1일)

#### 8.1 API 문서화
```markdown
# docs/api.md
- 각 도구별 사용법
- 파라미터 설명
- 응답 형식 예시
- 에러 코드 정의
```

#### 8.2 배포 설정
```dockerfile
# Dockerfile
- Python 3.11 슬림 이미지
- 의존성 설치 최적화
- 헬스체크 설정
```

```yaml
# docker-compose.yml
- 서비스 정의
- 환경 변수 설정
- 볼륨 마운트
```

## 🚀 실행 체크리스트

### 개발 전 준비사항
- [ ] 한국투자증권 OpenAPI 계정 생성
- [ ] APP_KEY, APP_SECRET 발급
- [ ] Python 3.11+ 환경 구성
- [ ] Git 저장소 초기화

### 개발 중 체크포인트
- [ ] 각 Phase 완료 후 기능 테스트
- [ ] API 호출 제한 확인 (분당 100회)
- [ ] 메모리 사용량 모니터링
- [ ] 로그 파일 크기 관리

### 테스트 체크리스트
- [ ] 모든 도구 정상 동작 확인
- [ ] 캐시 만료 시 데이터 갱신 확인
- [ ] API 장애 시 재시도 동작 확인
- [ ] 잘못된 파라미터 입력 시 에러 처리 확인

### 배포 전 체크리스트
- [ ] 환경 변수 설정 완료
- [ ] 로그 디렉토리 권한 설정
- [ ] Docker 이미지 빌드 테스트
- [ ] 프로덕션 환경 연결 테스트

## 📊 예상 일정 및 리소스

### 총 개발 기간: 10-12일
- **Week 1 (5일)**: Phase 1-4 (핵심 기능 구현)
- **Week 2 (5일)**: Phase 5-8 (안정성 및 문서화)
- **Buffer (2일)**: 예상치 못한 이슈 대응

### 주요 리스크 요소
1. **한국투자증권 API 변경**: API 스펙 변경 시 대응 방안 필요
2. **Rate Limit 제약**: 분당 100회 제한으로 인한 성능 이슈
3. **시장 시간 외 데이터**: 장외 시간 데이터 처리 방안
4. **실시간 데이터 정확성**: 지연 시간 및 데이터 신뢰성

### 성공 기준
1. **기능성**: 모든 5개 도구가 정상 동작
2. **성능**: 평균 응답 시간 2초 이내
3. **안정성**: 24시간 연속 운영 시 99% 가용성
4. **사용성**: 명확한 문서화 및 에러 메시지

## 🔧 기술적 고려사항

### API 호출 최적화
- 배치 요청으로 API 호출 횟수 최소화
- 캐시를 통한 중복 요청 방지
- 비동기 처리로 응답 시간 단축

### 메모리 관리
- 캐시 크기 제한 설정
- 오래된 캐시 데이터 자동 정리
- 메모리 사용량 모니터링

### 보안 고려사항
- API 키 환경 변수 분리
- 로그에 민감 정보 제외
- 입력 데이터 검증 강화

이 상세 계획서를 바탕으로 체계적이고 안정적인 MCP 서버 개발을 진행할 수 있습니다.