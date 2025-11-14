"""
Qdrant Hybrid Search (Dense + Sparse) 로컬 테스트
"""

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, PointStruct, SparseVector
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import numpy as np

# ========================================
# 1. 초기화
# ========================================

# 로컬 임베딩 모델 (384차원, 빠름)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Qdrant 메모리 모드 (파일 잠금 문제 없음)
client = QdrantClient(":memory:")

# ========================================
# 2. 컬렉션 생성 (핵심: Named Vectors)
# ========================================

client.create_collection(
    collection_name="test",
    vectors_config={
        "dense": VectorParams(size=384, distance=Distance.COSINE)  # Named vector
    },
    sparse_vectors_config={
        "sparse": SparseVectorParams()  # Named sparse vector
    }
)

print("✅ 컬렉션 생성 완료")

# ========================================
# 3. 테스트 데이터
# ========================================

docs = [
    "미쉐린 3스타 프렌치 파인다이닝, 계절 식재료를 활용한 모던 퀴진",
    "블루리본 이탈리안 레스토랑, 홈메이드 파스타와 리조또 전문",
    "강남 웨이팅 맛집, SNS에서 화제인 인기 브런치 카페"
]

# ========================================
# 4. Dense + Sparse 벡터 생성
# ========================================

# Dense: Sentence Transformer
dense_embeddings = model.encode(docs)
print(f"✅ Dense 임베딩 생성: {dense_embeddings.shape}")

# Sparse: BM25
tokenized_docs = [doc.split() for doc in docs]
bm25 = BM25Okapi(tokenized_docs)
print(f"✅ BM25 인덱싱 완료: {len(docs)}개 문서")

# ========================================
# 5. Qdrant에 삽입
# ========================================

points = []
for idx, (doc, dense) in enumerate(zip(docs, dense_embeddings)):
    # BM25 스코어 계산
    sparse_scores = bm25.get_scores(doc.split())
    sparse_idx = np.where(sparse_scores > 0)[0]

    points.append(PointStruct(
        id=idx,
        vector={
            "dense": dense.tolist(),  # Named vector와 매칭
            "sparse": SparseVector(
                indices=sparse_idx.tolist(),
                values=sparse_scores[sparse_idx].tolist()
            )
        },
        payload={"text": doc}
    ))

client.upsert(collection_name="test", points=points)
print(f"✅ {len(points)}개 포인트 삽입 완료")

# ========================================
# 6. 검색 테스트
# ========================================

# 테스트 쿼리
query = "프렌치 레스토랑"
query_dense = model.encode(query)
query_tokenized = query.split()
query_sparse_scores = bm25.get_scores(query_tokenized)
query_sparse_idx = np.where(query_sparse_scores > 0)[0]

# Hybrid 검색
results = client.query_points(
    collection_name="test",
    query=query_dense.tolist(),
    using="dense",  # Dense 벡터 사용
    limit=3
)

print(f"\n🔍 검색 쿼리: '{query}'")
print("=" * 60)

for result in results.points:
    print(f"Score: {result.score:.4f}")
    print(f"Text: {result.payload['text']}")
    print("-" * 60)

# ========================================
# 7. 컬렉션 정보 확인
# ========================================

collection_info = client.get_collection("test")
print(f"\n📊 컬렉션 정보:")
print(f"  - 총 벡터 수: {collection_info.points_count}")
print(f"  - Dense 벡터 차원: {collection_info.config.params.vectors['dense'].size}")
print(f"  - Sparse 벡터: {collection_info.config.params.sparse_vectors is not None}")

print("\n✅ 테스트 완료!")
