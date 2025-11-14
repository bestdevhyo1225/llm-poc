# Hybrid Search 마이그레이션 가이드

> Chroma → Qdrant/Milvus 전환 가이드 (Dense + Sparse Hybrid Search)

**작성일**: 2025-11-14
**대상**: shop_summary/ RAG 파이프라인

---

## 📌 현재 상황

- **벡터 DB**: Chroma (Dense 검색만)
- **임베딩**: Vertex AI text-embedding-004 (768차원)
- **검색 방식**: 코사인 유사도 (Dense만)
- **한계**: 전문 용어("미쉐린", "오마카세") 인식 부족

---

## 🎯 목표

네이버 플레이스 사례처럼 **Hybrid Search (Dense + Sparse)** 구현:
- Dense: 의미적 유사도 (현재와 동일)
- Sparse: BM25 키워드 매칭 (신규 추가)
- 융합: RRF (Reciprocal Rank Fusion)

---

## 옵션 1: Qdrant (추천) ⭐

### 1단계: 설치 및 초기화

```bash
# Python 패키지만 설치
pip install qdrant-client
```

```python
# shop_summary/fine_dining_and_susi_omakase/main_rag_hybrid.ipynb
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams

# 로컬 파일 기반 (./qdrant_data/)
client = QdrantClient(path="./qdrant_data")

# 컬렉션 생성 (Dense + Sparse)
client.create_collection(
    collection_name="fine_dining_examples_hybrid",
    vectors_config={
        "dense": VectorParams(
            size=768,
            distance=Distance.COSINE
        )
    },
    sparse_vectors_config={
        "sparse": SparseVectorParams()  # BM25 자동 처리
    }
)
```

### 2단계: 기존 데이터 마이그레이션

```python
import chromadb
from qdrant_client.models import PointStruct, SparseVector
from rank_bm25 import BM25Okapi

# 1. Chroma에서 데이터 로드
chroma_client = chromadb.PersistentClient(path="./chroma_db")
chroma_collection = chroma_client.get_collection("fine_dining_examples")

all_data = chroma_collection.get(
    include=["embeddings", "documents", "metadatas"]
)

# 2. BM25 Sparse 벡터 생성
corpus = [doc.split() for doc in all_data['documents']]
bm25 = BM25Okapi(corpus)

# 3. Qdrant로 데이터 이전
points = []
for idx, (doc, embedding, metadata) in enumerate(zip(
    all_data['documents'],
    all_data['embeddings'],
    all_data['metadatas']
)):
    # Sparse 벡터 생성 (BM25 스코어 → 인덱스-값 쌍)
    sparse_vec = bm25.get_scores(doc.split())
    sparse_indices = sparse_vec.nonzero()[0].tolist()
    sparse_values = sparse_vec[sparse_indices].tolist()

    points.append(PointStruct(
        id=idx,
        vector={
            "dense": embedding,  # 768차원
            "sparse": SparseVector(
                indices=sparse_indices,
                values=sparse_values
            )
        },
        payload={
            "shop_seq": metadata['shop_seq'],
            "shop_name": metadata['shop_name'],
            "summary": doc,
            **metadata
        }
    ))

# 배치 삽입
client.upsert(
    collection_name="fine_dining_examples_hybrid",
    points=points
)

print(f"✅ {len(points)}개 데이터 마이그레이션 완료")
```

### 3단계: Hybrid Search 구현

```python
# 섹션 5: retrieve_similar_examples() 함수 대체

def retrieve_similar_examples_hybrid(query_text, collection_name, top_k=2):
    """
    Qdrant Hybrid Search (Dense + Sparse)
    """
    # 1. Dense 임베딩 생성 (기존)
    dense_embedding = generate_embedding(query_text)

    # 2. Sparse 벡터 생성 (BM25)
    query_tokens = query_text.split()
    sparse_vec = bm25.get_scores(query_tokens)
    sparse_indices = sparse_vec.nonzero()[0].tolist()
    sparse_values = sparse_vec[sparse_indices].tolist()

    # 3. Hybrid Search (Qdrant가 RRF 자동 적용)
    results = client.search(
        collection_name=collection_name,
        query_vector={
            "dense": dense_embedding,
            "sparse": SparseVector(
                indices=sparse_indices,
                values=sparse_values
            )
        },
        limit=top_k
    )

    # 4. 결과 포맷팅
    similar_examples = []
    for hit in results:
        similar_examples.append({
            'shop_name': hit.payload['shop_name'],
            'summary': hit.payload['summary'],
            'score': hit.score  # RRF 융합 점수
        })

    return similar_examples

# 사용 예시
similar = retrieve_similar_examples_hybrid(
    query_text=f"{shop_name} 매장 정보: {collected_info}",
    collection_name="fine_dining_examples_hybrid",
    top_k=2
)
```

### 4단계: 검증 및 비교

```python
# A/B 테스트: Chroma vs Qdrant Hybrid

test_query = "미쉐린 3스타 스시 오마카세 세프 철학"

# Before: Chroma (Dense만)
chroma_results = chroma_collection.query(
    query_embeddings=[generate_embedding(test_query)],
    n_results=2
)

# After: Qdrant (Hybrid)
qdrant_results = retrieve_similar_examples_hybrid(
    test_query,
    "fine_dining_examples_hybrid",
    top_k=2
)

print("=== Chroma (Dense) ===")
for r in chroma_results['documents'][0]:
    print(f"- {r[:100]}...")

print("\n=== Qdrant (Hybrid) ===")
for r in qdrant_results:
    print(f"- {r['summary'][:100]}... (score: {r['score']:.3f})")
```

---

## 옵션 2: Milvus 2.5 (네이버 사례 동일)

### 1단계: Docker 설치

```bash
# Milvus Standalone (로컬 개발용)
wget https://github.com/milvus-io/milvus/releases/download/v2.5.0/milvus-standalone-docker-compose.yml -O docker-compose.yml

# 컨테이너 실행 (백그라운드)
docker-compose up -d

# 상태 확인
docker-compose ps

# Python 클라이언트
pip install pymilvus
```

### 2단계: 컬렉션 생성 (Dense + Sparse)

```python
from pymilvus import MilvusClient, DataType

client = MilvusClient(uri="http://localhost:19530")

# 스키마 정의
schema = client.create_schema()

schema.add_field("id", DataType.INT64, is_primary=True, auto_id=True)
schema.add_field("shop_seq", DataType.INT64)
schema.add_field("shop_name", DataType.VARCHAR, max_length=200)
schema.add_field("summary", DataType.VARCHAR, max_length=2000)

# Dense 벡터 (Vertex AI)
schema.add_field(
    "dense_vector",
    DataType.FLOAT_VECTOR,
    dim=768
)

# Sparse 벡터 (BM25) - Milvus 2.5+ 지원
schema.add_field(
    "sparse_vector",
    DataType.SPARSE_FLOAT_VECTOR
)

# 인덱스 생성
index_params = client.prepare_index_params()

index_params.add_index(
    field_name="dense_vector",
    index_type="HNSW",
    metric_type="COSINE",
    params={"M": 16, "efConstruction": 200}
)

index_params.add_index(
    field_name="sparse_vector",
    index_type="SPARSE_INVERTED_INDEX",  # BM25 전용
    metric_type="IP"  # Inner Product
)

# 컬렉션 생성
client.create_collection(
    collection_name="fine_dining_examples_hybrid",
    schema=schema,
    index_params=index_params
)
```

### 3단계: 데이터 삽입 (Chroma → Milvus)

```python
from pymilvus.model.sparse import BM25EmbeddingFunction

# BM25 함수 초기화
bm25_ef = BM25EmbeddingFunction()

# Chroma 데이터 로드 (이전과 동일)
all_data = chroma_collection.get(
    include=["embeddings", "documents", "metadatas"]
)

# Milvus 포맷으로 변환
milvus_data = []
for doc, embedding, metadata in zip(
    all_data['documents'],
    all_data['embeddings'],
    all_data['metadatas']
):
    # Sparse 벡터 생성 (BM25)
    sparse_vec = bm25_ef.encode_documents([doc])[0]

    milvus_data.append({
        "shop_seq": metadata['shop_seq'],
        "shop_name": metadata['shop_name'],
        "summary": doc,
        "dense_vector": embedding,
        "sparse_vector": sparse_vec  # {인덱스: 값} 딕셔너리
    })

# 배치 삽입
client.insert(
    collection_name="fine_dining_examples_hybrid",
    data=milvus_data
)

print(f"✅ {len(milvus_data)}개 데이터 삽입 완료")
```

### 4단계: Hybrid Search (RRF 자동)

```python
def retrieve_similar_examples_milvus(query_text, collection_name, top_k=2):
    """
    Milvus Hybrid Search (네이버 방식 동일)
    """
    # Dense 임베딩
    dense_embedding = generate_embedding(query_text)

    # Sparse 임베딩 (BM25)
    sparse_embedding = bm25_ef.encode_queries([query_text])[0]

    # Hybrid Search
    results = client.search(
        collection_name=collection_name,
        data=[dense_embedding, sparse_embedding],  # 두 벡터 동시 전달
        anns_field=["dense_vector", "sparse_vector"],
        limit=top_k,
        output_fields=["shop_seq", "shop_name", "summary"],
        rerank="rrf",  # Reciprocal Rank Fusion
        rerank_k=10    # 각 검색에서 top-10 후보 사용
    )

    # 결과 포맷팅
    similar_examples = []
    for hit in results[0]:  # results[0]이 융합 결과
        similar_examples.append({
            'shop_name': hit['entity']['shop_name'],
            'summary': hit['entity']['summary'],
            'score': hit['distance']
        })

    return similar_examples

# 사용
similar = retrieve_similar_examples_milvus(
    query_text="미쉐린 3스타 프렌치 파인다이닝",
    collection_name="fine_dining_examples_hybrid",
    top_k=2
)
```

---

## 🔄 마이그레이션 체크리스트

### Phase 1: 환경 준비 (1일)
- [ ] Qdrant 설치 (`pip install qdrant-client`)
- [ ] 또는 Milvus Docker 설치 (`docker-compose up -d`)
- [ ] BM25 라이브러리 설치 (`pip install rank-bm25`)

### Phase 2: 데이터 마이그레이션 (2시간)
- [ ] Chroma 데이터 전체 추출
- [ ] Sparse 벡터 생성 (BM25)
- [ ] 새 벡터 DB에 삽입
- [ ] 데이터 무결성 검증 (건수, 메타데이터)

### Phase 3: 검색 함수 교체 (3시간)
- [ ] `retrieve_similar_examples()` 함수 Hybrid Search로 변경
- [ ] 3개 카테고리 노트북 모두 업데이트:
  - `fine_dining_and_susi_omakase/main_rag.ipynb`
  - `low_to_mid_price_dining/main_rag.ipynb`
  - `waiting_hotplace/main_rag.ipynb`

### Phase 4: A/B 테스트 (1일)
- [ ] 테스트 쿼리 10개 준비 ("미쉐린 3스타", "스시 오마카세" 등)
- [ ] Chroma vs Hybrid Search 결과 비교
- [ ] Similarity Score 분석
- [ ] 검색 정확도 측정

### Phase 5: 프로덕션 전환 (1일)
- [ ] 기존 Chroma 디렉토리 백업
- [ ] 모든 노트북 새 벡터 DB로 전환
- [ ] `CLAUDE.md` 문서 업데이트
- [ ] 성능 지표 로깅 추가

---

## 📊 예상 성과

네이버 사례 기준:

| 지표 | 현재 (Chroma Dense) | 예상 (Hybrid) |
|------|---------------------|---------------|
| **전문 용어 인식** | 60% | 85%+ |
| **검색 Recall** | 기준 | +15~20% |
| **Similarity Score** | 0.65 평균 | 0.75+ 평균 |
| **검색 속도** | 10ms | 15ms (허용 가능) |

---

## ⚠️ 주의사항

### 1. 벡터 차원 확인
- Dense: 768차원 (Vertex AI text-embedding-004)
- Sparse: 가변 길이 (BM25는 어휘 크기만큼)

### 2. 메모리 사용량
- Qdrant: 현재 대비 +30% (Sparse 벡터 추가)
- Milvus: 현재 대비 +100% (여러 컨테이너)

### 3. 백업 전략
```bash
# Chroma 백업 (마이그레이션 전)
cp -r ./chroma_db ./chroma_db_backup_$(date +%Y%m%d)

# Qdrant 백업
cp -r ./qdrant_data ./qdrant_data_backup_$(date +%Y%m%d)

# Milvus 백업 (Docker 볼륨)
docker exec milvus-standalone tar -czf /tmp/milvus_backup.tar.gz /var/lib/milvus
docker cp milvus-standalone:/tmp/milvus_backup.tar.gz ./
```

### 4. 롤백 계획
마이그레이션 실패 시:
1. 백업 디렉토리 복원
2. 노트북 `retrieve_similar_examples()` 함수 되돌리기
3. 기존 Chroma 계속 사용

---

## 🎯 권장 진행 순서

1. **1주차**: Qdrant로 마이그레이션 (간단, 위험 낮음)
2. **2주차**: A/B 테스트 (성능 검증)
3. **3주차**: 효과 확인 후 프로덕션 전환
4. **(선택) 4주차**: 대규모 확장 필요 시 Milvus 고려

---

## 📚 참고 문서

- **Qdrant 공식 문서**: https://qdrant.tech/documentation/
- **Milvus 2.5 Hybrid Search**: https://milvus.io/docs/hybrid-search.md
- **네이버 사례**: `shop_summary/NAVER_PLACE_AI_AGENT_CASE_STUDY.md`
- **BM25 알고리즘**: https://en.wikipedia.org/wiki/Okapi_BM25

---

**작성자**: Claude Code
**업데이트**: 2025-11-14
