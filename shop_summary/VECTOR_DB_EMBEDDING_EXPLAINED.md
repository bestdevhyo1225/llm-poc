# 벡터 DB와 임베딩 동작 원리

이 문서는 RAG 시스템에서 벡터 DB에 실제로 저장되는 것과 유사도 계산 방식을 설명합니다.

---

## 🔍 벡터 DB에 실제로 저장되는 것

### ❌ 오해: 유사도를 저장한다?

**아닙니다!** 유사도는 저장하지 않습니다. **임베딩 벡터**를 저장합니다.

### ✅ 실제로 저장되는 데이터

```python
# 벡터 DB에 저장되는 것
{
    "document": "모수는 안성재 셰프가 운영하는 모던 한식 레스토랑으로...",  # 원본 텍스트
    "embedding": [0.123, -0.456, 0.789, ..., 0.234],  # ⭐ 768개의 숫자 (벡터)
    "metadata": {
        "shop_seq": 1,
        "shop_name": "모수",
        "title": "화덕 구이와 발효 기법의...",
        "summaries": ["...", "...", "..."]
    }
}
```

**핵심**: 유사도가 아니라 **임베딩 벡터(768차원 숫자 배열)**를 저장합니다!

---

## 🧮 임베딩 벡터란?

### 텍스트를 숫자로 변환

```python
# Vertex AI Text Embedding 모델 사용
text = "모수는 안성재 셰프가 운영하는 모던 한식 레스토랑으로..."

embedding = generate_embedding(text)
# 결과: [0.123, -0.456, 0.789, 0.234, -0.567, ..., 0.891]
#       ↑ 768개의 float 숫자
```

### 임베딩의 의미

- **의미적으로 유사한 텍스트 → 유사한 벡터**
- **의미적으로 다른 텍스트 → 다른 벡터**

예시:
```python
# 유사한 텍스트
"모던 한식 레스토랑" → [0.8, 0.6, 0.3, ...]
"창의적인 한식"      → [0.7, 0.5, 0.4, ...]  # 벡터가 비슷함

# 다른 텍스트
"모던 한식 레스토랑" → [0.8, 0.6, 0.3, ...]
"이탈리안 피자"      → [0.1, -0.5, 0.9, ...]  # 벡터가 다름
```

---

## 🔎 유사도는 검색할 때 계산됨

### 검색 프로세스

```python
# 1. 새 매장의 정보를 벡터로 변환
query_text = "밍글스는 강민구 셰프가 운영하는 한식 레스토랑으로..."
query_embedding = generate_embedding(query_text)
# 결과: [0.7, 0.5, 0.4, ..., 0.6] (768개)

# 2. Chroma가 벡터 DB의 모든 벡터와 비교
# 저장된 벡터들:
# - 모수: [0.8, 0.6, 0.3, ..., 0.5]
# - 에빗: [0.2, -0.3, 0.9, ..., 0.1]
# - 권숙수: [0.75, 0.55, 0.35, ..., 0.6]

# 3. 코사인 유사도 계산 (실시간)
similarity(밍글스, 모수) = cosine_similarity([0.7,0.5,0.4,...], [0.8,0.6,0.3,...])
                        = 0.87  # ⭐ 이때 계산됨!

similarity(밍글스, 에빗) = cosine_similarity([0.7,0.5,0.4,...], [0.2,-0.3,0.9,...])
                        = 0.34

similarity(밍글스, 권숙수) = cosine_similarity([0.7,0.5,0.4,...], [0.75,0.55,0.35,...])
                          = 0.92

# 4. Top-2 반환
results = [
    {"shop_name": "권숙수", "score": 0.92},
    {"shop_name": "모수", "score": 0.87}
]
```

---

## 📊 코사인 유사도 계산 방식

### 2차원 예시 (이해를 위해 단순화)

```
벡터 공간에서 각도로 유사도 측정:

      모수 [0.8, 0.6]
       ↗ (각도 작음 = 유사함)
      /
     / ← 밍글스 [0.7, 0.5]
    /
   ────────────────→

      에빗 [0.2, -0.3]
       ↘ (각도 큼 = 다름)
```

**각도가 작을수록 = 유사도 높음**

### 수식

```python
cosine_similarity(A, B) = (A · B) / (||A|| × ||B||)

# A · B: 내적 (dot product)
# ||A||, ||B||: 벡터의 크기 (norm)

# 결과값 범위: -1 ~ 1
# 1에 가까울수록 유사함
```

---

## 🎯 전체 흐름 요약

### 저장 단계

```python
# 1. 텍스트 → 벡터 변환
collected_info = "모수는 안성재 셰프가..."
embedding = generate_embedding(collected_info)  # [0.8, 0.6, 0.3, ...]

# 2. 벡터 DB에 저장
collection.add(
    documents=[collected_info],     # 원본 텍스트
    embeddings=[embedding],          # ⭐ 768차원 벡터 (유사도 아님!)
    metadatas=[{"shop_name": "모수", ...}]
)
```

### 검색 단계

```python
# 1. 쿼리 텍스트 → 벡터 변환
query = "밍글스는 강민구 셰프가..."
query_embedding = generate_embedding(query)  # [0.7, 0.5, 0.4, ...]

# 2. 벡터 DB에서 유사 벡터 검색
results = collection.query(
    query_embeddings=[query_embedding],  # 쿼리 벡터
    n_results=2  # Top-2
)
# ⭐ 이 시점에 Chroma가 코사인 유사도 계산!

# 3. 유사도 점수와 함께 반환
# [
#   {"shop_name": "권숙수", "distance": 0.16},  # distance → similarity 변환 필요
#   {"shop_name": "모수", "distance": 0.26}
# ]
```

---

## 💡 정리

| 항목 | 설명 |
|------|------|
| **저장되는 것** | 768차원 임베딩 벡터 (숫자 배열) |
| **저장되지 않는 것** | 유사도 (검색 시 실시간 계산) |
| **임베딩 모델** | Vertex AI text-embedding-004 |
| **유사도 계산 시점** | `collection.query()` 호출 시 |
| **유사도 계산 방법** | 코사인 유사도 (벡터 간 각도) |
| **검색 속도** | HNSW 인덱스로 빠름 (Chroma 자동) |

---

## 🔬 파인다이닝 카테고리 예시

### 벡터 DB 구조

```
Chroma 벡터 DB
├── fine_dining_examples (하나의 컬렉션)
│   ├── [Document 1] 모수 (shop_seq=1, 768차원 벡터)
│   ├── [Document 2] 밍글스 (shop_seq=2, 768차원 벡터)
│   ├── [Document 3] 권숙수 (shop_seq=3, 768차원 벡터)
│   ├── [Document 4] 에빗 (shop_seq=4, 768차원 벡터)
│   └── ... (계속 추가됨)
```

### 워크플로우 (누적 학습 과정)

#### 1단계: 첫 번째 매장 처리 (모수)

```python
# 벡터 DB: 비어있음 (count: 0)
query = "모수의 collected_info"
similar_examples = retrieve_similar_examples(query, collection, top_k=2)
# 결과: [] (유사 사례 없음)

# RAG 없이 Few-shot 예시만으로 생성
generate_summary(...)

# 검증 통과 → 벡터 DB에 저장
store_successful_example(..., shop_name="모수", ...)
# 벡터 DB: count: 1
```

#### 2단계: 두 번째 매장 처리 (밍글스)

```python
# 벡터 DB: 모수 (count: 1)
query = "밍글스의 collected_info"
similar_examples = retrieve_similar_examples(query, collection, top_k=2)
# 결과: [{"shop_name": "모수", "score": 0.82}] (1개 발견)

# RAG 컨텍스트 포함하여 생성
# 프롬프트: [과거 성공 사례: 모수] + 밍글스 정보
generate_summary(...)

# 검증 통과 → 벡터 DB에 저장
store_successful_example(..., shop_name="밍글스", ...)
# 벡터 DB: count: 2
```

#### 3단계: 세 번째 매장 처리 (권숙수)

```python
# 벡터 DB: 모수, 밍글스 (count: 2)
query = "권숙수의 collected_info"
similar_examples = retrieve_similar_examples(query, collection, top_k=2)
# 결과: [
#   {"shop_name": "밍글스", "score": 0.87},
#   {"shop_name": "모수", "score": 0.79}
# ] (Top-2 발견)

# RAG 컨텍스트 포함하여 생성
# 프롬프트: [과거 성공 사례: 밍글스, 모수] + 권숙수 정보
generate_summary(...)

# 검증 통과 → 벡터 DB에 저장
store_successful_example(..., shop_name="권숙수", ...)
# 벡터 DB: count: 3
```

---

## ✅ 핵심 포인트

1. **공유 지식 베이스**: 파인다이닝 카테고리의 모든 매장이 `fine_dining_examples` 컬렉션 공유

2. **독립 검색**: 각 매장 처리 시 해당 매장의 `collected_info`로 유사도 검색 수행

3. **Top-K 검색**: 가장 유사한 2개만 선택하여 컨텍스트로 제공

4. **누적 학습**: 처리할수록 컬렉션에 더 많은 사례가 쌓여 검색 품질 향상

5. **카테고리 격리**:
   - `fine_dining_examples` ← 파인다이닝 매장만
   - `mid_price_examples` ← 중저가 매장만
   - `waiting_hotplace_examples` ← 웨이팅 핫플 매장만

6. **실시간 유사도 계산**: 벡터는 저장하지만, 유사도는 검색 시점에 계산

---

## 🚀 결론

**벡터 DB는 "텍스트의 의미를 숫자로 표현한 좌표"를 저장하고, 검색 시 "좌표 간 거리"를 계산하여 유사한 텍스트를 찾습니다!**

- **저장**: 텍스트 → 임베딩 벡터 (768개 숫자) → Chroma
- **검색**: 쿼리 텍스트 → 임베딩 벡터 → 코사인 유사도 계산 → Top-K 반환
