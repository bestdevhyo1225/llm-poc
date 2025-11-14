# 네이버 플레이스 Backoffice AI Agent 구축 사례 요약

> RAG + MCP 기반 사내 지식 검색 시스템 구축 사례 및 우리 프로젝트 적용 인사이트

**출처**: [네이버 플레이스 개발 블로그](https://medium.com/naver-place-dev/backoffice-ai-agent-%EA%B5%AC%EC%B6%95%EA%B8%B0-rag-mcp-%EA%B8%B0%EB%B0%98-%ED%94%8C%EB%A0%88%EC%9D%B4%EC%8A%A4ai-%ED%8A%B9%ED%99%94-%EC%A7%80%EC%8B%9D-%EA%B2%80%EC%83%89-%EC%8B%9C%EC%8A%A4%ED%85%9C-9a66b4afa1aa)
**작성**: 네이버 플레이스 AI 플랫폼(PAIP) 팀 - 윤종석, 유서연
**요약일**: 2025-11-14

---

## 📊 핵심 성과

| 지표 | 개선 효과 |
|------|----------|
| **응답 만족도** | ×2 (2배 향상) |
| **응답 속도** | 1.4배 향상 |
| **토큰 사용량** | 66% 감소 |
| **툴 호출 수** | 49% 감소 |

---

## 🎯 프로젝트 배경 및 목표

### 문제 상황
- 문서가 Confluence, GitHub, 외부 문서에 흩어져 있음
- 기존 검색은 **Lexical Search(단어 일치)** 위주 → 표현이 달라지면 검색 실패
- 약어, 사내 용어, 긴 회의록에 특히 취약
- 서비스별로 지식이 분산되어 지식 공유 어려움

### 목표
1. **팀 내 기술·서비스 간 지식 격차 해소**
2. **정보 접근성 향상**
3. **OJT 및 협업 과정에서 업무 효율 극대화**

### 솔루션
**Semantic Search 기반 RAG + MCP 기반 Agentic AI Agent**
- 문서의 **의미**를 이해해 관련 정보 검색
- **질의 의도**를 해석해 최적의 답변 제공
- 신규 입사자 온보딩(OJT)을 주요 시나리오로 검증

---

## 🏗️ 시스템 아키텍처

### 3계층 컴포넌트 구조

```
┌─────────────────────────────────────────────────┐
│           MCP Server (Execution Engine)         │
│   - Search Module (Milvus 연동)                 │
│   - Document Module (OpenSearch 연동)           │
└─────────────────────────────────────────────────┘
                        ↕
┌──────────────────┬──────────────────┬───────────┐
│   Data Loader    │  Milvus Loader   │   MCP Log │
│   (수집/정제)     │  (임베딩/청킹)    │   Store   │
└──────────────────┴──────────────────┴───────────┘
                        ↕
┌──────────────────┬──────────────────────────────┐
│   OpenSearch     │         Milvus               │
│ (Raw Data Store) │ (Vector Store: Dense+Sparse) │
└──────────────────┴──────────────────────────────┘
```

### 핵심 컴포넌트

#### Databases
- **OpenSearch (Raw Data Store)**: 원본 데이터 1차 저장소, 키-값 스토어
- **Milvus (Vector Store)**: Dense + Sparse 벡터 저장, Hybrid 검색 소스
- **OpenSearch DB (MCP Log Store)**: 운영 로그, 성능 평가 데이터

#### Core Components
- **Data Loader**: 수집 → 정규화 → 청킹 → 임베딩 → 적재 자동화
- **Milvus Loader**: 청킹 + Dense/Sparse 임베딩 생성 전처리 허브
- **MCP Server**: Agent 백엔드, Tool 제공 (search_smart 등)

---

## 📚 데이터 파이프라인

### 데이터 소스 (총 11,173건)

| 소스 | 내용 | 수집 방법 |
|------|------|----------|
| **GitHub Issues** | 프로젝트 진행, 실험 로그, 문제 해결 과정 | GitHub API (본문 + 댓글 매칭) |
| **Confluence Wiki** | 프로젝트, 기술 리서치, 회의록 | CQL 쿼리 (메타데이터 포함) |
| **기술 공식 문서** | Milvus, VLLM, Kserve 등 | 사이트맵 기반 크롤링 |

### 데이터 분포
- GitHub 문서: **84.5%** (9,441건)
- 나머지 소스: 15.5% (1,732건)

### Data Loader 파이프라인

```python
# 4단계 자동화 파이프라인
1. 수집       → API/크롤러로 원문 수집
2. 구조화     → Markdown 포맷 변환 (markdownify)
3. 임베딩     → 청킹 + 벡터화
4. 적재       → OpenSearch + Milvus 이중 저장
```

### 핵심 기술

#### Crawl4AI - 텍스트 밀도 기반 크롤링
- BeautifulSoup → Crawl4AI 전환
- HTML 태그/텍스트 비율 계산하여 의미 있는 본문만 추출
- 광고, 사이드바 자동 배제

#### API 설계 - 증분 업데이트
```python
# 엔드포인트 분리
/update/full          # 전체 문서 갱신
/update/incremental   # 특정 기간 이후 문서만 갱신

# 변경 감지 예시
GET /update/github?since=2025-09-24
# → 2025년 9월 24일 이후 변경된 문서만 수집
```

---

## 🔍 검색 파이프라인 - RAG 최적화

### 평가 체계

#### 1. BEIR-SCIFACT 기반 정량 평가
- **데이터셋**: 과학 논문 기반 IR 벤치마크
- **선정 이유**: 도메인 특화 문서 검색 환경 유사성
- **평가 지표**: Recall@K

#### 2. LLM-as-a-Judge 기반 의미 평가
```python
# 평가 프로세스
1. 평가용 쿼리 선별 (실제 MCP 사용 기록 기반 10개 핵심 질문)
2. LLM으로 의미 변형 쿼리 증강 (20개로 확장)
3. 평가 모델(Large LLM 30B↑)이 문서-쿼리 연관성 평가 (0~10점)
4. 평균 점수 산출
```

### 하이브리드 검색 구조

```
┌─────────────────────────────────────────┐
│  Dense Search (Milvus)                  │
│  - 의미적 유사도 파악                    │
│  - 넓은 범위 탐색                        │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────┴───────────────────────┐
│  Sparse Search (BM25)                   │
│  - 정확한 키워드 매칭                    │
│  - 전문 용어/약어 보완                   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│  RRF (Reciprocal Rank Fusion)           │
│  - Dense + Sparse 결과 융합             │
│  - 순위 정보 기반 통합                   │
└─────────────────┬───────────────────────┘
                  │
┌─────────────────▼───────────────────────┐
│  LLM Reranker (Cross-Encoder)           │
│  - 쿼리-문서 의미 일치도 정밀 평가       │
│  - 최종 Context 구성                     │
└─────────────────────────────────────────┘
```

### 검색 최적화 실험 (20개 실험 수행)

#### 1. Index 선택
- **선택**: HNSW (Hierarchical Navigable Small World)
- **이유**: 높은 Recall, 안정적 Latency, 확장성

#### 2. Embedding 모델
```
실험 조합:
- A: Encoder-only (Dense + Sparse 동시 생성)
- B: LLM-based (긴 문맥, 전문 용어 이해 강점)
- Size: Small(1B↓), Medium(1B~5B), Large(5B~10B)

결과:
- 최종 선택: LLM-based B Small + Milvus 내장 BM25
- 이유: 품질 대비 효율성, 운영 비용 최적
```

#### 3. Chunking 전략
```
문제:
- Markdown Header 기준 분할 → 문맥 단절
- 문단 단위 스플리터 → 의미 끊김

해결:
- TokenTextSplitter 도입
- 토큰 단위 균등 분할 + 10~20% 중첩(Overlap)
- Chunk Size: 1024 vs 2048 비교 → 2048 선택

결과:
- 2048 토큰이 긴 문맥(회의록, 로그) 처리에서 우수
- 정보 단절 없이 맥락 온전히 제공
```

#### 4. Reranking - LLM Reranker
```
1차 융합: RRF (순위 기반 Dense + Sparse 통합)
2차 재정렬: LLM Reranker (Cross-Encoder)

실험 결과:
- Medium 모델 선택
- Judge 점수 평균 +0.7점 향상
- Context 품질 크게 개선
```

---

## 🤖 MCP 기반 Agentic RAG

### MCP란?
- **Model Context Protocol**: Anthropic 개발 오픈소스 프로토콜
- Agent가 외부 리소스와 표준화된 방식으로 상호작용
- Database, API, 파일 시스템 등 연동

### Backoffice AI MCP 서버 구성

```
┌──────────────────────────────────────────┐
│  Search Module                           │
│  - 벡터 임베딩 기반 문서 검색             │
│  - Milvus 연동                           │
└──────────────────────────────────────────┘

┌──────────────────────────────────────────┐
│  Document Module                         │
│  - 원문 문서 및 메타데이터 조회           │
│  - OpenSearch 연동                       │
└──────────────────────────────────────────┘
```

### MCP 도구 호출 시나리오

```
사용자 질의
    ↓
[Search Module] Vector 검색 → 관련 문서 청크 반환
    ↓
질의 복잡도 판단
    ↓
├─ 간단한 경우 → 즉시 응답 생성
│   (예: "최근 회의록 요약")
│
└─ 복잡한 경우 → [Document Module] 원문 조회
    (예: "윤종석의 9월 작업 내용 정리")
    ↓
두 검색 결과 통합 분석
    ↓
최종 응답 생성
```

**Agent의 자율 판단**:
- Vector 검색만으로 충분한지
- 원문 조회가 필요한지
- MCP Resource의 시스템 프롬프트로 정의

---

## 🎨 Smart Search - Pre-Retrieval 최적화

### MCP 로그 분석 → 문제 발견

```
문제:
- 사용자 비정형 질의가 검색 품질 저하의 주요 원인
  예: "지난달 회의록 정리해줘"
      "윤종석이 작성한 문서 찾아줘"

분석 결과:
- 시점 표현 (지난달, 1년간)
- 작성자 표기 (다양한 이름 형식)
- 명령형 질의 (정리해줘, 찾아줘)
```

### Smart Search 3단계 질의 정제

#### Step 1: Query Normalization (질의 구조화)

```python
# 1) Time Normalization
입력: "지난달 회의록"
처리: 서버 현재 시점 참조
출력: 2025-09-01 ~ 2025-09-30

# 2) Author Normalization
입력: "윤종석"
처리: 시스템 간 표기 통일
출력: yoon-jong-suk → jongsuk-yoon, js-y

# 3) Query Rewrite
입력: "회의록 정리해줘"
처리: 조사/어미 제거, 핵심 키워드 추출
출력: "회의록 요약"
```

#### Step 2: Entity Expansion (검색 누락 방지)

```python
# Name Variants 자동 생성
입력: "윤종석"
정규화: yoon-jong-suk
확장:
  - jongsuk-yoon
  - js-y
  - yoon.js
  - 윤종석

결과: 다양한 이름 표기로 저장된 문서 모두 검색
```

#### Step 3: Query Filtering (검색 범위 정밀화)

```python
# 문서 타입 자동 판단
질의: "최근 회의록 정리해줘"
판단: confluence_page (회의록은 주로 Confluence에 저장)

질의: "버그 수정 이슈 찾아줘"
판단: github_issue

# 리소스 프롬프트에 정의
- Confluence: 장기 문서, 회의록, 기술 리서치
- GitHub: 이슈, 실험 로그, 문제 해결
```

### Agentic RAG 최종 워크플로우

```
사용자 질의: "유서연이 지난달 정리한 회의록 정리해줘"
    ↓
┌────────────────────────────────────────────────┐
│ Search Smart Tool (Pre-Retrieval)              │
├────────────────────────────────────────────────┤
│ ① 시간 변환: 2025-09-01~09-30                 │
│ ② 작성자 정규화: yuseoyeon, ys-yeon           │
│ ③ 문서 타입 필터: confluence_page              │
│ ④ 검색어 정제: 회의록 요약                     │
└────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────┐
│ Search Smart Tool (Retrieval)                  │
├────────────────────────────────────────────────┤
│ ⑤ Milvus Hybrid 검색 (Dense + Sparse)         │
└────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────┐
│ Search Smart Tool (Post-Retrieval)             │
├────────────────────────────────────────────────┤
│ ⑥ RRF 융합 → LLM Reranker                     │
└────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────┐
│ Document Search Tool                           │
├────────────────────────────────────────────────┤
│ ⑦ OpenSearch 원문 검색 (필요 시)               │
└────────────────────────────────────────────────┘
    ↓
┌────────────────────────────────────────────────┐
│ Host LLM                                       │
├────────────────────────────────────────────────┤
│ ⑧ 근거 기반 요약 및 답변 생성                  │
└────────────────────────────────────────────────┘
```

**핵심**: LLM이 검색 과정 전체를 스스로 판단·제어

---

## 📊 성능 평가 - A/B 테스트

### 평가 설계

**비교 대상**:
- **Lexical Search MCP**: 키워드 기반 (오픈소스)
- **Backoffice AI MCP**: 의미 기반 Agentic RAG

**평가 시나리오**: 신규 입사자 온보딩(OJT)
- 8개 대표 질의 선정
- 실제 업무 질문 패턴 반영

**평가 방법**:
- **정성평가**: PAIP 팀원 10명 블라인드 설문
- **정량평가**: 토큰 사용량, 응답 속도, 툴 호출 수

### 정성평가 결과

| 항목 | Lexical Search MCP | Backoffice AI MCP |
|------|-------------------|-------------------|
| **응답 만족도** | 기준 | **2배 향상** ⭐ |
| **문맥 이해** | 반복 검색 루프, 답변 실패 | 다중 문서 추론 성공 |
| **추론형 질의** | 취약 | 강점 |

**특히 우수한 질의 유형**:
- 팀 문화, 협업 규칙
- "윤종석의 9월 작업 내용 정리" (다중 문서 추론)

### 정량평가 결과

| 지표 | Lexical Search MCP | Backoffice AI MCP | 개선 |
|------|-------------------|-------------------|------|
| **응답 속도** | 기준 | **1.4배 빠름** | ⭐ |
| **토큰 사용량** | 기준 | **66% 감소** | ⭐⭐⭐ |
| **툴 호출 수** | 기준 | **49% 감소** | ⭐⭐ |

**핵심 인사이트**:
- 의미 기반 검색 → 불필요한 정보 탐색 감소
- 첫 시도에 정확한 결과 → 툴 호출 감소
- 적은 자원으로 안정적인 결과 도출

---

## 💡 핵심 인사이트 및 성과

### 목표 달성

#### 1. 지식 접근성 향상
- 흩어진 문서를 하나의 질의로 통합 검색
- 단절된 정보 흐름 연결

#### 2. 서비스 간 협업 강화
- 기술 문서 + 실험 히스토리 통합 검색
- 중복 작업 감소, 협업 효율 향상

#### 3. OJT 효율 개선
- 신규 입사자가 서비스 전반 맥락 한 번에 파악
- 온보딩 속도 향상

### 추가 실무 인사이트

#### 검색 효율 최적화
- 응답 만족도 향상 + 토큰 절감 + 속도 향상 **동시 달성**
- 개발 생산성 향상

#### 조직 학습 구조 진화
- 질의 로그 분석 → FAQ/가이드 환류
- Cursor Rules, 검색 규칙 자동화 학습 데이터 기반 마련

---

## 🚀 후속 계획

### 1. 세분화된 필터링 체계
- 현재: document_type 단위 필터링
- 향후: 회의록, 성능평가, 기술가이드 등 세부 분류
- 효과: 검색 정확도 향상, 응답 일관성 개선

### 2. MCP 간 연동 강화
```
복합 질의 예시:
"지난 분기 성능 평가에서 언급된 개선 항목을 정리해 위키에 게시해줘"

처리 과정:
1. Backoffice MCP → '성능평가 문서' 검색
2. Attlasian MCP → 위키에 게시

결과:
- 단순 검색기 → 조직 지식 흐름 연결 허브로 진화
```

---

## 🎯 우리 프로젝트 적용 인사이트

> **우리 시스템**: RAG 기반 음식점 요약문 생성 (추천 시스템 아님)
> - 목적: 매장 정보 → 3문장 요약문 자동 생성
> - 핵심: 카테고리별 예시 기반 일관된 톤앤매너 유지

### 직접 적용 가능한 기법

#### 1. Hybrid Search - 유사 예시 검색 개선
```python
# 현재: main_rag.ipynb
- Chroma Dense 검색만 사용
- 유사 요약문 2개 검색 → 스타일 참고

# 네이버 방식 적용
- Dense (의미 유사도) + BM25 Sparse (키워드 매칭)
- RRF로 결합 → 최적의 예시 선택

예상 효과:
- "미쉐린 3스타 스시 오마카세" 같은 전문 용어 인식 향상
- 카테고리 내 더 정확한 유사 예시 검색
- 검색 실패율 감소 (현재: 예시 부족 시 빈 결과)
```

#### 2. Chunking 최적화 - Knowledge Base 구축
```python
# 현재: knowledge_base/source_pipeline.ipynb
- 소스 타입별 독립 문서 (청킹 없음)

# 네이버 방식 적용
- TokenTextSplitter (2048 토큰, 10~20% Overlap)
- 긴 블로그 리뷰, 미쉐린 가이드 분할 처리

적용 시나리오:
- 네이버 블로그 크롤링 시 긴 리뷰 → 2048 토큰 단위 청킹
- 문맥 단절 방지 (예: "셰프 이야기 + 메뉴 소개"를 한 청크에)
```

#### 3. LLM-as-a-Judge 평가 시스템
```python
# 현재: 규칙 기반 검증만 존재 (섹션 9)
- 길이, 구조, 금지어, 중복 체크

# 네이버 방식 추가 → 의미적 품질 평가
평가 항목:
1. 정보 충실도: COLLECTED_INFO와 요약문 일치도
2. 톤앤매너: 카테고리 스타일 준수도
3. 가독성: 자연스러운 문장 흐름

효과:
- 정량적 품질 측정 (0~10점)
- v3.0 vs v5.0 성능 비교 가능
- 프롬프트 개선 효과 측정
```

#### 4. 로깅 시스템 - 생성 실패 분석
```python
# 네이버: MCP Log Store로 모든 호출 추적

# 우리 시스템 적용
BigQuery 로깅 항목:
- 매장 정보 (shop_seq, shop_name, category)
- 생성 성공/실패 여부
- 검증 실패 원인 (구조 오류, 길이 초과, 금지어 등)
- 사용 토큰 수, 응답 시간
- 검색된 유사 예시 (similarity score)

활용:
- 실패 패턴 분석 → 프롬프트 개선
- 카테고리별 성공률 추적
- 비용 최적화 (토큰 사용량 모니터링)
```

#### 5. 증분 업데이트 - 벡터 DB 관리
```python
# 네이버 방식
/update/incremental?since=2025-09-24

# 우리 시스템 적용 (섹션 10: store_successful_example)
- 현재: 검증 통과한 요약문 즉시 저장
- 개선: 타임스탬프 기반 증분 관리

활용:
- 매일 신규 매장만 처리
- 벡터 DB 백업/복원 시 날짜 기준 선택
- 특정 기간 요약문 재생성 시 효율적
```

### 성과 측정 지표

네이버 성과(응답 만족도 2배, 토큰 66% 감소)를 참고한 우리 KPI:

| 지표 | 현재 | 목표 | 측정 방법 |
|------|------|------|----------|
| **1차 생성 성공률** | ~70% | 85%+ | 검증 통과율 (섹션 9) |
| **토큰 사용량** | 기준 | -30% | 프롬프트 최적화 (RAG 적용) |
| **처리 속도** | 기준 | -20% | 매장당 평균 생성 시간 |
| **품질 점수** | - | 8.0+ | LLM-as-a-Judge (신규) |
| **예시 검색 정확도** | - | 0.7+ | Similarity Score 평균 |

---

## 📌 핵심 교훈 (Key Takeaways)

### 1. Hybrid Search로 예시 검색 정확도 향상
- **네이버**: Dense + Sparse로 Recall 향상
- **우리**: 유사 요약문 검색 시 전문 용어("미쉐린", "오마카세") 인식 개선
- **적용**: Chroma에 BM25 Sparse 추가 검토

### 2. Chunking은 Knowledge Base 품질을 결정
- **네이버**: 2048 토큰 + 10~20% Overlap
- **우리**: 긴 블로그 리뷰 처리 시 문맥 유지
- **적용**: `source_pipeline.ipynb`에 TokenTextSplitter 추가

### 3. LLM-as-a-Judge로 품질 정량화
- **네이버**: Judge 점수 +0.7점 향상, A/B 테스트 가능
- **우리**: 현재 규칙 기반 검증만 존재
- **적용**: 정보 충실도, 톤앤매너, 가독성 점수화 (0~10점)

### 4. 로깅으로 지속 개선
- **네이버**: MCP Log 분석 → 문제 발견 → 개선
- **우리**: 생성 실패 패턴 분석 → 프롬프트 튜닝
- **적용**: BigQuery에 생성 로그 저장 (성공/실패, 토큰 수, 유사도)

### 5. 평가 체계 우선 구축
- **네이버**: 20개 실험을 정량 비교
- **우리**: v1.0 → v5.0 성능 비교 체계 필요
- **적용**: 카테고리별 성공률, 토큰 효율성 추적

---

## 🔗 관련 기술 스택 비교

| 항목 | 네이버 플레이스 | 우리 프로젝트 | 고려사항 |
|------|----------------|--------------|----------|
| **LLM** | 미명시 (Claude 추정) | Gemini 2.5 Pro | - |
| **임베딩** | LLM-based Small | Vertex AI text-embedding-004 | Sparse 추가 검토 |
| **벡터 DB** | Milvus | Chroma | Milvus 전환 고려 (Sparse 지원) |
| **문서 DB** | OpenSearch | - | PostgreSQL/MySQL 활용 |
| **청킹** | TokenTextSplitter 2048 | 미정의 | 2048 토큰 + Overlap 적용 |
| **검색 방식** | Hybrid (Dense+Sparse) | Dense만 | BM25 Sparse 추가 |
| **Reranking** | RRF + LLM Reranker | - | 추가 검토 필요 |
| **인터페이스** | MCP (FastMCP) | Multi-Agent | MCP 전환 고려 |
| **로깅** | OpenSearch | - | BigQuery 활용 |
| **평가** | BEIR + LLM-as-a-Judge | 규칙 기반 | LLM 평가 추가 |

---

## 🛠️ 즉시 적용 가능한 개선 사항

### Phase 1: Chunking 최적화 (Knowledge Base)
```python
# 위치: shop_summary/knowledge_base/source_pipeline.ipynb

from langchain.text_splitter import TokenTextSplitter

splitter = TokenTextSplitter(
    chunk_size=2048,       # 긴 리뷰 전체 맥락 유지
    chunk_overlap=200      # 10% 중첩
)

# 적용 대상
- 네이버 블로그 긴 리뷰 (1000자 이상)
- 미쉐린 가이드 상세 설명
```

### Phase 2: Hybrid Search 추가 (유사 예시 검색)
```python
# 위치: shop_summary/fine_dining_and_susi_omakase/main_rag.ipynb

from rank_bm25 import BM25Okapi

# 1. Chroma에서 Dense 검색 (기존)
dense_results = collection.query(
    query_embeddings=[embedding],
    n_results=5
)

# 2. BM25 Sparse 검색 추가
corpus = [doc['text'] for doc in all_examples]
bm25 = BM25Okapi(corpus)
sparse_results = bm25.get_top_n(query_tokens, corpus, n=5)

# 3. RRF로 융합 → top_k=2 선택
final_results = reciprocal_rank_fusion(dense_results, sparse_results)[:2]
```

### Phase 3: LLM-as-a-Judge 평가 시스템
```python
# 위치: 각 카테고리 main_rag.ipynb 섹션 9 (검증 후)

def evaluate_summary_quality(collected_info, generated_summary, category):
    prompt = f"""
    수집 정보: {collected_info}
    생성 요약문: {generated_summary}
    카테고리: {category}

    다음 기준으로 0~10점 평가:
    1. 정보 충실도: 수집 정보가 요약문에 정확히 반영되었는가?
    2. 톤앤매너: {category} 스타일에 맞는가?
    3. 가독성: 3문장이 자연스럽게 연결되는가?

    JSON 반환: {{"score": 8.5, "reason": "..."}}
    """
    return gemini_model.generate_content(prompt)

# 결과 활용
- 점수 7점 미만: 재생성
- 점수 7~8점: 경고 표시 후 저장
- 점수 8점 이상: 즉시 저장
```

### Phase 4: 로깅 시스템 구축
```python
# BigQuery 테이블 스키마
CREATE TABLE shop_summary_logs (
  shop_seq INT64,
  shop_name STRING,
  category STRING,
  success BOOL,
  validation_result STRING,  -- '통과' or 실패 원인
  llm_judge_score FLOAT64,
  token_count INT64,
  response_time_ms INT64,
  similar_examples ARRAY<STRUCT<shop_name STRING, similarity FLOAT64>>,
  created_at TIMESTAMP
);

# 로깅 코드 (섹션 10 이후 추가)
log_data = {
    'shop_seq': shop_seq,
    'success': validation_passed,
    'llm_judge_score': judge_result['score'],
    'token_count': response.usage_metadata.total_token_count,
    ...
}
bigquery_client.insert_rows_json(table_id, [log_data])
```

---

## 📖 참고 자료

### 네이버 플레이스 관련
- [원문 블로그 포스트](https://medium.com/naver-place-dev/backoffice-ai-agent-%EA%B5%AC%EC%B6%95%EA%B8%B0-rag-mcp-%EA%B8%B0%EB%B0%98-%ED%94%8C%EB%A0%88%EC%9D%B4%EC%8A%A4ai-%ED%8A%B9%ED%99%94-%EC%A7%80%EC%8B%9D-%EA%B2%80%EC%83%89-%EC%8B%9C%EC%8A%A4%ED%85%9C-9a66b4afa1aa)

### MCP 관련
- [Anthropic MCP Documentation](https://modelcontextprotocol.io/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)

### RAG 관련
- [BEIR Benchmark](https://github.com/beir-cellar/beir)
- [RRF (Reciprocal Rank Fusion)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)

### 임베딩 & 검색
- [Milvus Documentation](https://milvus.io/docs)
- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)
- [Cross-Encoder Reranking](https://www.sbert.net/examples/applications/cross-encoder/README.html)

---

## 💬 결론

네이버 플레이스 개발팀의 사례는 **체계적인 평가 기반 RAG 최적화 사례**입니다. 20개 실험을 통해 Hybrid Search, Chunking, Reranking을 정량적으로 비교하여 최적 조합을 찾았습니다.

### 우리 프로젝트(요약문 생성)에 적용 가능한 핵심

1. **Hybrid Search** → 유사 요약문 검색 정확도 향상 (전문 용어 인식)
2. **Chunking 최적화** → Knowledge Base 긴 리뷰 문맥 유지
3. **LLM-as-a-Judge** → 요약문 품질 정량화 (0~10점)
4. **로깅 시스템** → 실패 패턴 분석 → 프롬프트 개선
5. **평가 체계 우선** → v1.0~v5.0 성능 비교 가능

### 즉시 적용 가능한 개선

| Phase | 내용 | 예상 효과 |
|-------|------|----------|
| 1주차 | Chunking 최적화 | Knowledge Base 품질 향상 |
| 2주차 | Hybrid Search | 예시 검색 정확도 +15% |
| 1주차 | LLM-as-a-Judge | 품질 정량화, A/B 테스트 가능 |
| 1주차 | 로깅 시스템 | 실패 원인 추적, 개선 루프 |

---

**다음 단계**: Phase 1부터 순차 적용하여 생성 성공률 70% → 85% 향상 목표
