# 리뷰 & 블로그 데이터를 위한 청킹(Chunking) 전략 가이드

> 음식점 리뷰, 블로그 등 비정형 텍스트 데이터에 최적화된 문서 분할 전략

---

## 📊 청킹 기법 비교표

| 기법 | 특징 | 장점 | 단점 | 적합한 상황 |
|------|------|------|------|------------|
| **Fixed-size** | 고정된 문자/토큰 수로 분할 | • 구현 간단<br>• 예측 가능한 크기<br>• 빠른 처리 | • 문맥 단절<br>• 문장이 중간에 잘림<br>• 의미 무시 | • 단순 테스트<br>• 토큰 제한이 엄격한 경우 |
| **Recursive Character** | 구분자 우선순위로 재귀적 분할<br>(문단 → 문장 → 단어) | • 자연스러운 경계<br>• 유연한 분할<br>• LangChain 기본값 | • 구분자 의존적<br>• 언어별 커스터마이징 필요 | • 일반적인 RAG 시스템<br>• 다양한 문서 타입 |
| **Sentence-based** | 문장 단위로 분할 후 묶음 | • 문법적 완결성<br>• 자연스러운 읽기<br>• 의미 보존 | • 크기 불균등<br>• 언어별 라이브러리 필요 | • Q&A 시스템<br>• 요약/번역 |
| **Semantic** | 임베딩 유사도로 의미적 분할 | • 의미론적 일관성 최고<br>• 맥락 보존 | • 계산 비용 높음<br>• 느린 속도<br>• 복잡한 구현 | • 고품질 검색<br>• 복잡한 문서<br>• 학술/법률 문서 |
| **Token-based** | LLM 토크나이저로 정확한 토큰 수 제한 | • 정확한 토큰 수 제어<br>• API 비용 최적화 | • 모델별 토크나이저 필요<br>• 느린 처리 | • GPT/Claude 등 토큰 제한<br>• 비용 최적화 중요 시 |
| **Sliding Window** | 겹치는 윈도우로 이동하며 분할 | • 경계 정보 보존<br>• 검색 누락 방지 | • 중복 데이터<br>• 저장 공간↑<br>• 비용↑ | • 정보 손실 민감<br>• 복잡한 참조 관계 |

---

## 🎯 리뷰 & 블로그 데이터에 최적화된 전략

### 리뷰/블로그 데이터의 특징

- 📝 **비정형 텍스트**: 구조가 일정하지 않음
- 💬 **문장 단위 의견**: 문장 단위로 의견/감정 표현
- 📏 **다양한 길이**: 짧은 한줄평부터 긴 리뷰까지
- 🇰🇷 **한국어 데이터**: 문장 구조가 중요
- 🔗 **문맥 중요**: 앞뒤 문장 연결이 중요

---

## 1️⃣ Recursive Character Splitting (최우선 권장) ⭐⭐⭐⭐⭐

### 개요
구분자 우선순위에 따라 재귀적으로 문서를 분할하는 방식. LangChain의 기본 전략.

### 코드 예시

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,      # 리뷰/블로그는 300-500자 권장
    chunk_overlap=50,    # 문맥 유지를 위한 적절한 overlap
    separators=[
        "\n\n",  # 문단
        "\n",    # 줄바꿈
        ". ",    # 문장 (마침표 + 공백)
        ".",     # 마침표
        "! ",    # 느낌표
        "? ",    # 물음표
        " ",     # 공백
        "",      # 문자
    ]
)

# 사용
reviews = [
    "진짜 맛있어요! 웨이팅 2시간 했는데 기다린 보람이 있었습니다. 파스타는 면이 쫄깃하고...",
    "분위기 좋고 음식도 괜찮았어요. 다만 가격이 좀 비싼 편이라...",
]

chunks = text_splitter.split_text("\n\n".join(reviews))
```

### 장점

- ✅ 리뷰의 자연스러운 문단 구조 유지
- ✅ 감정 표현 (!, ?)도 경계로 활용
- ✅ 길이가 다양한 리뷰에도 유연하게 대응
- ✅ 프로덕션 검증됨 (LangChain)
- ✅ 설정 커스터마이징 용이

### 권장 설정

| 데이터 타입 | chunk_size | chunk_overlap | 비고 |
|------------|-----------|--------------|------|
| 짧은 리뷰 (100-300자) | 200-300 | 30-50 | 문장 완결성 중요 |
| 중간 리뷰 (300-600자) | 300-400 | 50-80 | 균형잡힌 설정 |
| 긴 블로그 (600자+) | 400-600 | 80-100 | 문맥 보존 중요 |

---

## 2️⃣ Sentence-based Chunking (대안) ⭐⭐⭐⭐

### 개요
문장 단위로 분할한 후, 크기 제한에 맞춰 문장들을 묶는 방식.

### 코드 예시

```python
import kss

def sentence_based_chunking(text: str, max_chunk_size: int = 300):
    """
    문장 단위 청킹 (한국어 kss 사용)

    Args:
        text: 원본 텍스트
        max_chunk_size: 최대 청크 크기 (문자 수)
    """
    # kss로 한국어 문장 분리
    sentences = kss.split_sentences(text)

    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_chunk_size:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

# 사용
review = "음식이 정말 맛있었어요. 특히 파스타가 일품이었습니다. 다만 가격이 조금 비쌌어요."
chunks = sentence_based_chunking(review, max_chunk_size=100)
```

### 장점

- ✅ 리뷰는 문장 단위로 의견이 명확함
- ✅ "맛있어요", "별로에요" 같은 평가가 문장 단위로 분리
- ✅ kss는 한국어 문장 분리에 특화
- ✅ Q&A 검색에 유리
- ✅ 감정 분석, 평점 예측에 적합

### 사용 시기

- 짧은 리뷰 (100-300자)
- 한 문장이 하나의 의견을 담는 경우
- 감정 분석이나 평점 예측 용도
- 한국어 텍스트 처리

---

## 3️⃣ Semantic Chunking (고품질 필요 시) ⭐⭐⭐⭐⭐

### 개요
임베딩 유사도를 계산하여 의미적으로 관련된 문장들을 같은 청크로 묶는 방식.

### 코드 예시

```python
import kss
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def semantic_chunking_for_reviews(
    text: str,
    model: SentenceTransformer,
    threshold: float = 0.6,
    max_chunk_size: int = 400
):
    """
    의미론적 유사도 기반 청킹

    Args:
        text: 원본 텍스트
        model: 임베딩 모델
        threshold: 유사도 임계값 (낮을수록 더 많이 분할)
        max_chunk_size: 최대 청크 크기
    """
    # 문장 분리
    sentences = kss.split_sentences(text)

    if len(sentences) <= 1:
        return [text]

    # 각 문장 임베딩
    embeddings = model.encode(sentences)

    chunks = []
    current_chunk = sentences[0]

    for i in range(1, len(sentences)):
        # 이전 문장과의 유사도 계산
        sim = cosine_similarity([embeddings[i-1]], [embeddings[i]])[0][0]

        # 유사도가 높으면 같은 주제 → 같은 청크
        # 크기 초과 시에도 분할
        if sim >= threshold and len(current_chunk) + len(sentences[i]) <= max_chunk_size:
            current_chunk += " " + sentences[i]
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentences[i]

    chunks.append(current_chunk.strip())
    return chunks

# 사용
model = SentenceTransformer('all-MiniLM-L6-v2')
review = """
음식은 정말 맛있었습니다. 파스타 면발이 쫄깃하고 소스도 풍부했어요.
분위기도 너무 좋았어요. 인테리어가 세련되고 조명이 은은했습니다.
가격은 조금 비싼 편이에요. 하지만 음식 퀄리티를 생각하면 납득할 만해요.
"""
chunks = semantic_chunking_for_reviews(review, model, threshold=0.6)
```

### 장점

- ✅ "맛", "분위기", "서비스" 등 주제별로 자동 분할
- ✅ 리뷰가 여러 주제를 다룰 때 유용
- ✅ 의미적 일관성 최고
- ✅ 검색 정확도 향상

### 사용 시기

- 긴 블로그 리뷰 (1000자 이상)
- 여러 측면을 다루는 리뷰 (맛, 분위기, 서비스 등)
- 고품질 검색이 중요한 경우
- 처리 시간/비용 여유가 있을 때

### 주의사항

- ⚠️ 임베딩 계산 비용 (문장 수 × 임베딩 비용)
- ⚠️ 처리 시간이 다른 방법보다 느림
- ⚠️ threshold 값 튜닝 필요 (0.5-0.7 권장)

---

## 📋 실전 권장 설정

### 🍽️ 음식점 리뷰 (현재 프로젝트)

```python
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Recursive Character Splitting 권장
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,       # 리뷰 평균 길이 고려
    chunk_overlap=50,     # 문맥 유지
    separators=[
        "\n\n",   # 문단
        "\n",     # 줄바꿈
        ". ",     # 문장 (마침표 + 공백)
        ".",      # 마침표
        "! ",     # 느낌표
        "? ",     # 물음표
        " ",      # 공백
        ""        # 문자
    ]
)
```

**선택 이유**:
- 음식점 리뷰는 "맛", "분위기", "서비스" 등이 문단으로 나뉨
- 자연스러운 경계 유지가 중요
- 프로덕션 안정성 검증됨
- LangChain 생태계와 호환

---

## 📊 상황별 비교 요약

| 상황 | 1순위 | 2순위 | 3순위 |
|------|-------|-------|-------|
| **일반 리뷰/블로그** | Recursive Character | Sentence-based | Semantic |
| **짧은 한줄평** | Sentence-based | Recursive Character | Fixed-size |
| **긴 리뷰 (1000자+)** | Recursive Character | Semantic | Sentence-based |
| **고품질 검색 필요** | Semantic | Recursive Character | Sentence-based |
| **빠른 프로토타입** | Recursive Character | Fixed-size | Sentence-based |
| **한국어 특화** | Sentence-based (kss) | Recursive Character | Semantic |

---

## 🎯 최종 추천

### 음식점 리뷰/블로그 데이터라면

1. **지금 바로 시작**: `RecursiveCharacterTextSplitter` (LangChain)
   - 프로덕션 검증 완료
   - 설정 간단
   - 유지보수 용이

2. **한국어 최적화 필요**: `Sentence-based + kss`
   - 한국어 문장 구조 정확히 파악
   - 문장 단위 의견 분리
   - 감정 분석에 유리

3. **최고 품질 필요**: `Semantic Chunking`
   - 의미적 일관성 최고
   - 주제별 자동 분류
   - 검색 정확도 향상

---

## 🔧 설정 가이드

### chunk_size 선택 기준

| 텍스트 길이 | chunk_size | 근거 |
|-----------|-----------|------|
| 짧은 리뷰 (100-300자) | 200-300 | 대부분 1-2개 청크로 처리 |
| 중간 리뷰 (300-600자) | 300-400 | 2-3개 청크로 균형있게 분할 |
| 긴 블로그 (600자+) | 400-600 | 문맥 보존하며 적절히 분할 |

### chunk_overlap 선택 기준

| 목적 | overlap 비율 | overlap 값 (chunk_size=300 기준) |
|------|-------------|-------------------------------|
| 최소 중복 | 10-15% | 30-45 |
| 균형 (권장) | 15-20% | 45-60 |
| 문맥 중시 | 20-30% | 60-90 |

### separators 최적화

**기본 설정** (범용):
```python
separators=["\n\n", "\n", ". ", ".", " ", ""]
```

**리뷰 최적화** (감정 표현 포함):
```python
separators=["\n\n", "\n", ". ", ".", "! ", "? ", " ", ""]
```

**블로그 최적화** (구조화된 문서):
```python
separators=["\n\n\n", "\n\n", "\n", ". ", ".", " ", ""]
```

---

## 📈 성능 비교

### 처리 속도 (1000개 문서 기준)

| 기법 | 처리 시간 | 상대 속도 |
|------|----------|----------|
| Fixed-size | ~0.5초 | ⚡⚡⚡⚡⚡ |
| Recursive Character | ~1초 | ⚡⚡⚡⚡ |
| Sentence-based | ~3초 | ⚡⚡⚡ |
| Semantic | ~30초 | ⚡ |
| Token-based | ~5초 | ⚡⚡ |

### 검색 품질 (주관적 평가)

| 기법 | 정확도 | 일관성 | 문맥 보존 |
|------|--------|--------|----------|
| Fixed-size | ⭐⭐ | ⭐⭐⭐ | ⭐ |
| Recursive Character | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Sentence-based | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Semantic | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Token-based | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## 💡 실전 팁

### 1. 청크 크기 결정하기

```python
# 데이터 분석
texts = [...]  # 리뷰 데이터
lengths = [len(text) for text in texts]

print(f"평균 길이: {np.mean(lengths):.0f}자")
print(f"중앙값: {np.median(lengths):.0f}자")
print(f"75 백분위수: {np.percentile(lengths, 75):.0f}자")

# 75 백분위수의 70-80%를 chunk_size로 설정
recommended_chunk_size = int(np.percentile(lengths, 75) * 0.75)
```

### 2. Overlap 최적화

```python
# 문맥이 중요한 경우: overlap = chunk_size * 0.2
chunk_overlap = int(chunk_size * 0.2)

# 검색 속도가 중요한 경우: overlap = chunk_size * 0.1
chunk_overlap = int(chunk_size * 0.1)
```

### 3. 청크 품질 검증

```python
def validate_chunks(chunks):
    """청크 품질 검증"""
    issues = []

    for i, chunk in enumerate(chunks):
        # 너무 짧은 청크
        if len(chunk) < 50:
            issues.append(f"청크 {i}: 너무 짧음 ({len(chunk)}자)")

        # 문장이 중간에 잘린 경우
        if not chunk.strip()[-1] in ['.', '!', '?', '요', '다', '네', '죠']:
            issues.append(f"청크 {i}: 문장 미완성")

    return issues
```

---

## 🔗 참고 자료

- [LangChain Text Splitters](https://python.langchain.com/docs/modules/data_connection/document_transformers/)
- [kss (Korean Sentence Splitter)](https://github.com/hyunwoongko/kss)
- [Sentence Transformers](https://www.sbert.net/)

---

## 📝 관련 문서

- `qdrant_test_1.ipynb`: 청킹 기법 실전 구현 및 비교
- `RAG_IMPLEMENTATION.md`: RAG 시스템 전체 가이드
- `RAG_ARCHITECTURE_OVERVIEW.md`: 아키텍처 상세 설명

---

**작성일**: 2025-11-17
**프로젝트**: llm-poc (음식점 요약문 생성)
**위치**: `shop_summary/qdrant_poc/`
