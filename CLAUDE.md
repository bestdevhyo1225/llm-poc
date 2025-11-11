# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 개요

RAG(Retrieval-Augmented Generation)를 활용하여 음식점 요약문을 생성하는 LLM PoC 프로젝트입니다. Gemini 2.5 Pro와 Chroma 벡터 데이터베이스를 사용하여 3개 음식점 카테고리에 대해 고품질의 일관된 요약문을 생성합니다.

## 아키텍처

### 3개의 독립적인 RAG 파이프라인

시스템은 톤앤매너 일관성을 유지하기 위해 카테고리별 독립 RAG 파이프라인을 사용합니다:

- **파인다이닝 / 스시 오마카세**: `shop_summary/fine_dining_and_susi_omakase/`
- **중저가 예약 매장**: `shop_summary/low_to_mid_price_dining/`
- **웨이팅 핫플레이스**: `shop_summary/waiting_hotplace/`

각 카테고리는 다음 2개 노트북을 포함합니다:
- `main.ipynb` - RAG 없는 기본 버전
- `main_rag.ipynb` - Chroma 벡터 DB를 활용한 RAG 강화 버전

### RAG 워크플로우

1. **쿼리**: 새로운 매장 정보를 Vertex AI Text Embedding으로 768차원 벡터로 변환
2. **검색**: Chroma가 카테고리별 컬렉션에서 코사인 유사도 검색 수행
3. **증강**: 유사도 상위 2개 예시를 컨텍스트로 포맷팅
4. **생성**: Gemini 2.5 Pro가 검색된 예시를 참고하여 요약문 생성
5. **저장**: 성공한 요약문을 벡터 DB에 저장하여 향후 활용

### 벡터 데이터베이스 구조

```
./chroma_db/
├── fine_dining_examples (컬렉션)
├── mid_price_examples (컬렉션)
└── waiting_hotplace_examples (컬렉션)
```

**컬렉션을 분리한 이유**: 각 카테고리는 고유한 톤앤매너와 스타일을 가집니다. 격리를 통해 카테고리 간 오염을 방지하고 작성 일관성을 유지합니다.

## 핵심 기술 스택

- **LLM**: Gemini 2.5 Pro via Vertex AI (temperature: 0.5)
- **임베딩**: Vertex AI Text Embedding Model (text-embedding-004, 768차원)
- **벡터 DB**: Chroma (로컬, 영구 저장, HNSW 인덱싱)
- **인증**: 서비스 계정 키 위치 `/home/ubuntu/keys/wad-dw-data-engineer.json`

## 개발 워크플로우

### 환경 설정

```bash
# 의존성 설치
pip install google-cloud-aiplatform google-genai python-dotenv chromadb

# 인증 정보 설정
export GOOGLE_APPLICATION_CREDENTIALS="/home/ubuntu/keys/wad-dw-data-engineer.json"

# Python 버전
pyenv local llm-poc  # .python-version 참고
```

### 노트북 실행 방법

각 RAG 노트북은 2가지 처리 모드를 지원합니다:

**단일 매장 모드** (테스트/튜닝용):
1. 섹션 6에서 `MODE = "single"` 설정
2. `SHOP_SEQ`와 `SHOP_NAME` 입력
3. 섹션 7 실행: 수집된 정보 붙여넣기
4. 섹션 8 실행: RAG로 요약문 생성
5. 섹션 9 실행: 결과 검증
6. 섹션 10 실행: 벡터 DB에 저장

**다중 매장 모드** (배치 처리용):
1. 섹션 6에서 `MODE = "multi"` 설정
2. `SHOPS` 리스트와 `COLLECTED_INFO` 딕셔너리 정의
3. 섹션 7 건너뛰기
4. 섹션 8 실행: RAG로 전체 요약문 생성
5. 섹션 9 실행: 전체 결과 검증
6. 섹션 10 실행: 성공한 결과 저장

### 핵심 RAG 함수

각 `main_rag.ipynb`의 섹션 5에 위치:

- `generate_embedding(text)` - Vertex AI로 텍스트를 768차원 벡터로 변환
- `retrieve_similar_examples(query_text, collection, top_k=2)` - Chroma에서 유사 예시 검색
- `format_rag_context(similar_examples)` - 검색된 예시를 LLM 프롬프트 형식으로 포맷
- `store_successful_example(...)` - 검증된 요약문을 벡터 DB에 저장

### 출력 구조

모든 요약문은 다음 JSON 형식을 따릅니다:
```json
{
  "shop_seq": 12345,
  "shop_name": "매장명",
  "title": "15-30자 길이의 설명적 제목",
  "summaries": [
    "문장 1: 셰프 철학 / 브랜드 정체성 (40-60자)",
    "문장 2: 코스 구성 / 시그니처 메뉴 (40-60자)",
    "문장 3: 공간 / 분위기 / 미식 경험 (40-60자)"
  ]
}
```

## 중요한 구현 세부사항

### 카테고리 격리가 핵심

**절대로** 카테고리 간 교차 검색하지 마세요. 각 카테고리 에이전트는 자신의 컬렉션만 쿼리해야 합니다:
- 파인다이닝은 `fine_dining_examples`만 검색
- 중저가는 `mid_price_examples`만 검색
- 웨이팅 핫플은 `waiting_hotplace_examples`만 검색

### 유사도 점수 해석

Chroma는 거리(0-2)를 반환하므로, 유사도(0-1)로 변환해야 합니다:
```python
similarity = 1.0 - (distance / 2.0)
```

- 0.9-1.0: 거의 동일 (복사 의심)
- 0.7-0.9: 매우 유사 (훌륭한 참고 자료)
- 0.5-0.7: 관련성 있음 (참고 가능)
- <0.5: 관련성 낮음 (필터링 권장)

### Top-K 선택

실험 결과 `top_k=2`가 기본값:
- Top-1: 다양성 부족
- Top-2: 최적의 균형 (권장)
- Top-3+: 수익 체감, 비용/지연시간 증가

### 자가 개선 시스템

RAG 시스템은 시간이 지남에 따라 학습합니다:
- 1일차: 예시 없음, Few-shot 프롬프트만 사용 (~70% 성공률)
- 1주차: 20개 예시 (~78% 성공률)
- 1개월: 80개 예시 (~85% 성공률)
- 3개월: 200개 이상 예시 (~90% 성공률)

### 비용 구조

- Gemini 2.5 Pro: $1.25/1M input tokens
- Vertex AI 임베딩: 무료 (월 100만 요청까지)
- Chroma: 무료 (로컬 저장, 매장당 ~2KB)
- 매장당 평균 비용: ~$0.0025

## 일반적인 문제

### Chroma 컬렉션이 비어있음

컬렉션이 비어있을 때(초기 상태), `retrieve_similar_examples()`는 `[]`를 반환합니다. 이것은 정상입니다 - 첫 번째 매장들은 Few-shot 예시만으로 생성되고, 이후 저장되어 향후 사용됩니다.

### 낮은 유사도 점수

모든 검색된 예시의 유사도가 0.5 미만인 경우, 최소 점수 필터링을 고려하세요:
```python
filtered_results = [r for r in results if r.get('score', 0) >= 0.5]
```

### 검증 실패

검증 항목:
- 구조: `title`과 정확히 3개의 `summaries`가 있어야 함
- 길이: 각 요약문은 40-60자 권장 (<30 또는 >100일 경우 경고)

### 벡터 DB 백업

Chroma는 `./chroma_db/` 디렉토리에 데이터를 저장합니다:
```bash
# 백업
cp -r ./chroma_db ./chroma_db_backup_$(date +%Y%m%d)

# 복원
cp -r ./chroma_db_backup_20250110 ./chroma_db
```

## 문서

`shop_summary/` 내 주요 문서:
- `RAG_IMPLEMENTATION.md` - 완전한 RAG 통합 가이드
- `RAG_ARCHITECTURE_OVERVIEW.md` - 예시가 포함된 상세 아키텍처 설명
- `VECTOR_DB_EMBEDDING_EXPLAINED.md` - 벡터 임베딩 개념

## 프로젝트 설정

- **GCP 프로젝트**: wad-dw
- **위치**: us-central1
- **모델**: gemini-2.5-pro
- **Temperature**: 0.5
- **Max Output Tokens**: 4096
- **응답 형식**: JSON
