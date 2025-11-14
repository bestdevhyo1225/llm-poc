"""
Qdrant 안전한 초기화 헬퍼 함수
Jupyter Notebook에서 여러 번 실행해도 안전하게 동작
"""

import os
import shutil
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams


class QdrantClientManager:
    """
    Qdrant 클라이언트 싱글톤 관리
    같은 경로에 대해 하나의 인스턴스만 유지
    """
    _instances = {}

    @classmethod
    def get_client(cls, path: str = "./qdrant_data") -> QdrantClient:
        """
        Qdrant 클라이언트 가져오기 (없으면 생성)

        Args:
            path: Qdrant 데이터 저장 경로

        Returns:
            QdrantClient 인스턴스
        """
        # 절대 경로로 변환 (중복 방지)
        abs_path = os.path.abspath(path)

        # 이미 생성된 클라이언트가 있으면 재사용
        if abs_path in cls._instances:
            print(f"✅ 기존 Qdrant 클라이언트 재사용: {abs_path}")
            return cls._instances[abs_path]

        # 디렉토리 없으면 생성
        if not os.path.exists(abs_path):
            os.makedirs(abs_path, exist_ok=True)
            print(f"📁 Qdrant 데이터 디렉토리 생성: {abs_path}")

        try:
            # 새 클라이언트 생성
            client = QdrantClient(path=abs_path)
            cls._instances[abs_path] = client
            print(f"✅ Qdrant 클라이언트 생성 완료: {abs_path}")
            return client

        except RuntimeError as e:
            if "already accessed" in str(e):
                # 다른 프로세스가 잠금을 걸고 있는 경우
                print(f"⚠️  다른 인스턴스가 {abs_path}를 사용 중입니다.")
                print(f"해결 방법:")
                print(f"1. Jupyter Kernel 재시작: Kernel > Restart Kernel")
                print(f"2. 또는 다른 경로 사용: QdrantClient(path='./qdrant_data_2')")
                raise
            else:
                raise

    @classmethod
    def close_all(cls):
        """모든 클라이언트 연결 종료"""
        for path, client in cls._instances.items():
            try:
                # Qdrant 로컬은 명시적 close가 없으므로 참조만 제거
                print(f"🔒 Qdrant 클라이언트 종료: {path}")
            except Exception as e:
                print(f"⚠️  종료 중 에러 ({path}): {e}")

        cls._instances.clear()
        print("✅ 모든 Qdrant 클라이언트 종료 완료")

    @classmethod
    def delete_storage(cls, path: str = "./qdrant_data"):
        """
        Qdrant 스토리지 완전 삭제 (재생성용)

        주의: 모든 데이터가 삭제됩니다!
        """
        abs_path = os.path.abspath(path)

        # 클라이언트 먼저 닫기
        if abs_path in cls._instances:
            del cls._instances[abs_path]

        # 디렉토리 삭제
        if os.path.exists(abs_path):
            shutil.rmtree(abs_path)
            print(f"🗑️  Qdrant 스토리지 삭제 완료: {abs_path}")
        else:
            print(f"⚠️  경로가 존재하지 않음: {abs_path}")


def init_qdrant_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int = 768,
    distance: Distance = Distance.COSINE,
    enable_hybrid: bool = False,
    recreate: bool = False
):
    """
    Qdrant 컬렉션 초기화

    Args:
        client: QdrantClient 인스턴스
        collection_name: 컬렉션 이름
        vector_size: Dense 벡터 차원 (기본: 768)
        distance: 거리 메트릭 (기본: COSINE)
        enable_hybrid: Hybrid Search 활성화 (Dense + Sparse)
        recreate: True면 기존 컬렉션 삭제 후 재생성

    Returns:
        생성된 컬렉션 이름
    """
    # 컬렉션 존재 여부 확인
    collections = client.get_collections().collections
    collection_exists = any(c.name == collection_name for c in collections)

    if collection_exists:
        if recreate:
            print(f"🗑️  기존 컬렉션 삭제: {collection_name}")
            client.delete_collection(collection_name)
        else:
            print(f"✅ 기존 컬렉션 사용: {collection_name}")
            return collection_name

    # 컬렉션 생성
    if enable_hybrid:
        # Hybrid Search (Dense + Sparse)
        client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(size=vector_size, distance=distance)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams()
            }
        )
        print(f"✅ Hybrid 컬렉션 생성: {collection_name} (Dense: {vector_size}차원 + Sparse)")
    else:
        # Dense Only
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=distance)
        )
        print(f"✅ Dense 컬렉션 생성: {collection_name} ({vector_size}차원)")

    return collection_name


# ========================================
# Jupyter Notebook용 사용 예시
# ========================================

if __name__ == "__main__":
    # 예시 1: 기본 사용법
    print("\n" + "="*50)
    print("예시 1: 기본 사용법")
    print("="*50)

    # 클라이언트 생성 (여러 번 실행해도 안전)
    client = QdrantClientManager.get_client(path="./qdrant_data")

    # 컬렉션 생성 (존재하면 재사용)
    init_qdrant_collection(
        client=client,
        collection_name="fine_dining_examples",
        vector_size=768,
        enable_hybrid=False  # Dense only
    )


    # 예시 2: Hybrid Search 사용
    print("\n" + "="*50)
    print("예시 2: Hybrid Search")
    print("="*50)

    client = QdrantClientManager.get_client()

    init_qdrant_collection(
        client=client,
        collection_name="fine_dining_hybrid",
        vector_size=768,
        enable_hybrid=True  # Dense + Sparse
    )


    # 예시 3: 컬렉션 재생성
    print("\n" + "="*50)
    print("예시 3: 컬렉션 재생성")
    print("="*50)

    init_qdrant_collection(
        client=client,
        collection_name="test_collection",
        vector_size=768,
        recreate=True  # 기존 삭제 후 재생성
    )


    # 예시 4: 모든 클라이언트 종료
    print("\n" + "="*50)
    print("예시 4: 정리")
    print("="*50)

    QdrantClientManager.close_all()


    # 예시 5: 스토리지 완전 삭제 (재시작 시)
    print("\n" + "="*50)
    print("예시 5: 스토리지 완전 삭제 (주의!)")
    print("="*50)

    # QdrantClientManager.delete_storage("./qdrant_data")
    print("⚠️  주석 해제 후 실행 시 모든 데이터 삭제")
