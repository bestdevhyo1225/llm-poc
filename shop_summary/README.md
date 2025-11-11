# Shop Summary RAG System

3단계 RAG(Retrieval-Augmented Generation) 시스템을 활용한 음식점 요약문 생성 프로젝트입니다.

## 시스템 개요

이 시스템은 Gemini 2.5 Pro와 Chroma 벡터 데이터베이스를 사용하여 3개 음식점 카테고리에 대해 고품질의 일관된 요약문을 생성합니다.

## 디렉토리 구조

```
shop_summary/
├── chroma_db/                          # 공통 벡터 데이터베이스 (모든 카테고리 공유)
│   ├── fine_dining_sources/           # 파인다이닝 원본 소스 컬렉션
│   ├── fine_dining_examples/          # 파인다이닝 요약문 예시 컬렉션
│   ├── mid_price_sources/             # 중저가 원본 소스 컬렉션
│   ├── mid_price_examples/            # 중저가 요약문 예시 컬렉션
│   ├── waiting_hotplace_sources/      # 웨이팅 핫플 원본 소스 컬렉션
│   └── waiting_hotplace_examples/     # 웨이팅 핫플 요약문 예시 컬렉션
│
├── knowledge_base/                     # 원본 소스 관리 (최초 1회 실행)
│   ├── source_chunking_experiment.ipynb  # Phase 2A: 청킹 전략 실험
│   ├── source_parser.ipynb              # Phase 2A-2: LLM 기반 텍스트 파싱
│   ├── source_collector.ipynb           # Phase 2B: 데이터 수집 및 검증
│   └── source_indexer.ipynb             # Phase 2C: 벡터 DB 인덱싱
│
├── fine_dining_and_susi_omakase/      # 파인다이닝 / 스시 오마카세
│   ├── main.ipynb                      # v1.0: 기본 버전 (RAG 없음)
│   ├── main_rag.ipynb                  # v3.0: Example-based RAG
│   ├── main_rag_source.ipynb           # v4.0: Source-based RAG
│   └── main_rag_hybrid.ipynb           # v5.0: Hybrid RAG
│
├── low_to_mid_price_dining/           # 중저가 예약 매장
│   ├── main.ipynb                      # v1.0: 기본 버전
│   ├── main_rag.ipynb                  # v3.0: Example-based RAG
│   ├── main_rag_source.ipynb           # v4.0: Source-based RAG
│   └── main_rag_hybrid.ipynb           # v5.0: Hybrid RAG
│
└── waiting_hotplace/                   # 웨이팅 핫플레이스
    ├── main.ipynb                      # v1.0: 기본 버전
    ├── main_rag.ipynb                  # v3.0: Example-based RAG
    ├── main_rag_source.ipynb           # v4.0: Source-based RAG
    └── main_rag_hybrid.ipynb           # v5.0: Hybrid RAG
```

## RAG 시스템 아키텍처

### 3단계 RAG 진화

| 버전 | 방식 | 검색 대상 | 장점 | 단점 | 사용 시기 |
|------|------|-----------|------|------|-----------|
| **v3.0** | Example-based | 요약문 예시 | 스타일 일관성 | 컨텍스트 부족 | 스타일 통일이 중요할 때 |
| **v4.0** | Source-based | 원본 소스 | 풍부한 정보 | 스타일 불안정 | Cold Start 상황 |
| **v5.0** | Hybrid | 소스 + 예시 | 최고 품질 | 토큰 비용 증가 | 최고 품질이 필요할 때 |

### 벡터 DB 구조

#### 원본 소스 컬렉션 (Sources)
- **목적**: 배경 지식 제공
- **데이터**: 미쉐린/블루리본 리뷰, 셰프 인터뷰, 코스 설명, 브랜드 철학
- **청킹**: 소스 타입별 최적화 (200~800자, 0~25% 오버랩)

#### 요약문 예시 컬렉션 (Examples)
- **목적**: 스타일 일관성 학습
- **데이터**: 검증 통과한 요약문 (제목 + 3개 문장)
- **청킹**: 문서 단위 (청킹 없음, 전체 180자)

## 워크플로우

### 1단계: 환경 설정

```bash
# 의존성 설치
pip install google-cloud-aiplatform google-genai python-dotenv chromadb langchain langchain-text-splitters pandas

# 인증 설정
export GOOGLE_APPLICATION_CREDENTIALS="/home/ubuntu/keys/wad-dw-data-engineer.json"
```

### 2단계: Knowledge Base 구축 (최초 1회)

```bash
# 실행 순서
1. knowledge_base/source_chunking_experiment.ipynb  # 청킹 전략 실험
2. knowledge_base/source_parser.ipynb              # 웹 텍스트를 JSON으로 파싱
3. knowledge_base/source_collector.ipynb           # 데이터 수집 및 검증
4. knowledge_base/source_indexer.ipynb             # 벡터 DB 인덱싱 (모든 카테고리)
```

**중요**: `source_indexer.ipynb`는 모든 카테고리의 데이터를 동시에 처리하며, 공통 벡터 DB(`shop_summary/chroma_db/`)를 생성합니다.

### 3단계: 요약문 생성 (다중 매장 배치 처리)

각 카테고리 디렉토리에서 RAG 버전을 선택하고 다중 매장을 배치 처리합니다:

#### 노트북 설정 (모든 RAG 버전 공통)

**섹션 6: 매장 정보 설정**
```python
# 1️⃣ 매장 기본 정보 (shop_seq, shop_name)
SHOPS = [
    (1, "모수"),
    (2, "밍글스"),
    (3, "가온"),
]

# 2️⃣ 매장별 수집된 정보 (매장명을 키로 사용)
COLLECTED_INFO = {
    "모수": """[웹 검색 결과]""",
    "밍글스": """[웹 검색 결과]""",
    "가온": """[웹 검색 결과]""",
}

# 3️⃣ SHOP_LIST 자동 생성 (자동 실행)
```

**섹션 7: 건너뛰기**

**섹션 8: RAG 강화 요약문 생성**
- 모든 매장에 대해 순차적으로 처리
- Example-based (v3.0): 유사한 요약문 예시 2개 검색
- Source-based (v4.0): 유사한 원본 소스 3개 검색
- Hybrid (v5.0): 원본 소스 2개 + 요약문 예시 2개 검색

**섹션 9: 구조 검증**
- 각 매장의 제목 1개, 요약문 3개 확인
- 각 문장 길이 체크 (권장 40-60자)

**섹션 10: 결과 저장**
- JSON 파일: `batch_summaries_{timestamp}.json`
- CSV 파일: `batch_summaries_{timestamp}.csv`
- 검증 통과한 요약문을 벡터 DB의 examples 컬렉션에 자동 저장

## 청킹 전략

### 소스 타입별 최적화

| 소스 타입 | 방법 | 크기 | 오버랩 | 근거 |
|-----------|------|------|--------|------|
| 미쉐린/블루리본 | Document | - | 0% | 200-500자, 완전한 문서 |
| 셰프 인터뷰 | Recursive | 800 | 25% (200) | Q&A 맥락 유지 |
| 코스 설명 | Semantic | 512 | 10% (50) | 요리별 독립성 |
| 브랜드 철학 | Recursive | 600 | 17% (100) | 문단 연결성 |
| 공간/분위기 | Recursive | 512 | 10% (50) | 공간 묘사 |
| 전통/기법 | Recursive | 600 | 17% (100) | 기술 설명 |

## 출력 형식

모든 요약문은 다음 JSON 형식을 따릅니다:

```json
{
  "shop_seq": 12345,
  "shop_name": "매장명",
  "title": "15-30자 길이의 설명적 제목",
  "summaries": [
    "1번 문장: 셰프 철학/브랜드 정체성 (40-60자)",
    "2번 문장: 코스 구성/시그니처 메뉴 (40-60자)",
    "3번 문장: 공간/분위기/미식 경험 (40-60자)"
  ]
}
```

## 핵심 기술 스택

- **LLM**: Gemini 2.5 Pro (temperature: 0.5)
- **임베딩**: Vertex AI text-embedding-004 (768차원)
- **벡터 DB**: Chroma (로컬, 영구 저장, HNSW 인덱싱)
- **청킹**: LangChain RecursiveCharacterTextSplitter
- **인증**: GCP 서비스 계정 (`/home/ubuntu/keys/wad-dw-data-engineer.json`)

## RAG 검색 전략

### Top-K 선택

| RAG 방식 | Top-K | 근거 |
|----------|-------|------|
| Example-based | 2 | 스타일 학습에 충분, 과다 시 혼란 |
| Source-based | 3 | 풍부한 컨텍스트 필요 |
| Hybrid | 2+2 | 균형 있는 정보 제공 |

### 유사도 점수 해석

Chroma는 코사인 거리(0-2)를 반환합니다:
```python
similarity = 1.0 - (distance / 2.0)
```

- **0.9-1.0**: 거의 동일 (복사 의심)
- **0.7-0.9**: 매우 유사 (훌륭한 참고 자료)
- **0.5-0.7**: 관련성 있음 (참고 가능)
- **<0.5**: 관련성 낮음 (필터링 권장)

## 자가 개선 시스템

RAG 시스템은 시간이 지남에 따라 학습하고 개선됩니다:

| 기간 | 예시 수 | 예상 성공률 | 특징 |
|------|---------|-------------|------|
| 1일차 | 0 | ~70% | Few-shot 프롬프트만 |
| 1주차 | 20 | ~78% | 초기 패턴 학습 |
| 1개월 | 80 | ~85% | 안정적 품질 |
| 3개월+ | 200+ | ~90% | 성숙한 시스템 |

## 비용 구조

### 토큰 비용 (Gemini 2.5 Pro)

| RAG 방식 | 평균 Input | 평균 Output | 매장당 비용 |
|----------|------------|-------------|-------------|
| Example-based | 1,500 | 200 | ~$0.0020 |
| Source-based | 2,500 | 200 | ~$0.0035 |
| Hybrid | 3,000 | 200 | ~$0.0040 |

**참고**:
- Gemini 2.5 Pro: $1.25/1M input tokens, $5.00/1M output tokens
- Vertex AI 임베딩: 무료 (월 100만 요청까지)
- Chroma: 무료 (로컬 저장)

## 일반적인 문제 및 해결

### 1. Chroma 컬렉션이 비어있음

**증상**: `retrieve_similar_sources()`가 빈 리스트 반환

**원인**: `knowledge_base/source_indexer.ipynb` 미실행

**해결**:
```bash
# knowledge_base/source_indexer.ipynb 실행
# 모든 카테고리의 원본 소스를 동시에 인덱싱
```

### 2. 낮은 유사도 점수

**증상**: 모든 검색 결과의 유사도가 0.5 미만

**해결**:
```python
# 최소 점수 필터링 추가
filtered_results = [r for r in results if r.get('score', 0) >= 0.5]

# 또는 카테고리가 올바른지 확인
# 파인다이닝은 fine_dining_sources만 검색해야 함
```

### 3. 검증 실패

**체크리스트**:
- ✅ `title` 필드 존재 (15-30자)
- ✅ `summaries` 배열에 정확히 3개 문장
- ✅ 각 문장 길이 40-60자 권장
- ⚠️ 30자 미만 또는 100자 초과 시 경고

### 4. 벡터 DB 백업

```bash
# 백업 생성
cd shop_summary
cp -r ./chroma_db ./chroma_db_backup_$(date +%Y%m%d)

# 복원
cp -r ./chroma_db_backup_20250111 ./chroma_db
```

## 카테고리별 특징

### 파인다이닝 / 스시 오마카세
- **톤**: 전문적, 고급스러운
- **키워드**: 셰프 철학, 오마카세, 제철 식재료, 미식 경험
- **예시 매장**: 모수, 밍글스

### 중저가 예약 매장
- **톤**: 전문적이면서도 접근 가능한
- **키워드**: 합리적 가격, 신선한 식재료, 세련된 공간
- **예시 매장**: 레스토랑 우오보, 더 런던 베이글 뮤지엄

### 웨이팅 핫플레이스
- **톤**: 트렌디하고 대중적인
- **키워드**: 핫플, 인기 메뉴, SNS 감성, 분위기
- **예시 매장**: 성수연방, 르바게트

## 점진적 개선 로드맵

```
Phase 1: 기본 Few-shot 프롬프트 (v1.0)
   ↓
Phase 2: Example-based RAG (v3.0)
   - 과거 성공 요약문 학습
   - 스타일 일관성 확보
   ↓
Phase 3: Knowledge Base 구축
   - 원본 소스 수집 (source_collector.ipynb)
   - 청킹 및 인덱싱 (source_indexer.ipynb)
   ↓
Phase 4: Source-based RAG (v4.0)
   - 풍부한 배경 지식 활용
   - Cold Start 문제 해결
   ↓
Phase 5: Hybrid RAG (v5.0)
   - 최적의 균형
   - 프로덕션 배포
```

## 프로젝트 설정

- **GCP 프로젝트**: wad-dw
- **리전**: us-central1
- **모델**: gemini-2.5-pro
- **Temperature**: 0.5
- **Max Output Tokens**: 4096
- **응답 형식**: JSON

## 참고 문서

- `RAG_IMPLEMENTATION.md` - RAG 통합 가이드
- `RAG_ARCHITECTURE_OVERVIEW.md` - 상세 아키텍처 설명
- `VECTOR_DB_EMBEDDING_EXPLAINED.md` - 벡터 임베딩 개념
- `CLAUDE.md` - Claude Code 작업 가이드

## 라이선스

이 프로젝트는 내부 PoC(Proof of Concept)용입니다.
