# Snowflake Cortex AI 모델 가이드

리뷰/블로그 데이터 기반 매장 요약문 생성을 위한 Snowflake Cortex AI 모델 선택 가이드

## 추천 모델 (우선순위)

### 1. mistral-large2 ⭐ (최우선 추천)

```python
from snowflake.cortex import Complete

response = Complete(
    'mistral-large2',
    f"""다음 리뷰와 블로그 데이터를 기반으로 매장 요약문을 작성해주세요.

리뷰 데이터: {reviews}
블로그 데이터: {blogs}

JSON 형식으로 작성:
{{
  "title": "15-30자 제목",
  "summaries": ["문장1 (40-60자)", "문장2", "문장3"]
}}"""
)
```

**선택 이유**:
- ✅ **다국어 최적화** (한국어 품질 우수)
- ✅ **긴 컨텍스트 처리** (여러 리뷰/블로그 한번에 처리)
- ✅ **구조화된 출력** (JSON 생성 우수)
- ✅ **일관성 있는 톤앤매너** 유지
- ⚖️ 비용/성능 균형

---

### 2. claude-3-7-sonnet (최고 품질)

```python
response = Complete('claude-3-7-sonnet', prompt)
```

**선택 이유**:
- ✅ **최고 품질의 한국어**
- ✅ **뉴앙스 이해** (리뷰 감정, 맥락 파악)
- ✅ **창의적인 요약** (자연스러운 문장)
- ❌ 비용이 가장 높음

---

### 3. snowflake-arctic (SQL/분석 특화)

```python
response = Complete('snowflake-arctic', prompt)
```

**선택 이유**:
- ✅ Snowflake 데이터와 통합 시 최적
- ✅ SQL 쿼리와 함께 사용 가능
- ⚠️ 한국어 품질은 mistral-large2보다 낮을 수 있음

---

## 모델 비교표

| 모델 | 한국어 품질 | 컨텍스트 | 비용 | 추천도 |
|------|------------|----------|------|--------|
| **mistral-large2** | ⭐⭐⭐⭐ | 32K | $$ | 🥇 |
| **claude-3-7-sonnet** | ⭐⭐⭐⭐⭐ | 200K | $$$ | 🥈 |
| **snowflake-arctic** | ⭐⭐⭐ | 4K | $ | 🥉 |
| llama3.1-70b | ⭐⭐⭐ | 128K | $$ | - |

---

## 사용 가능한 모델 목록 (2025년 기준)

### 대규모 모델 (Large Models) - 고성능

| 모델 | 특징 | 추천 용도 |
|------|------|-----------|
| **claude-3-7-sonnet** | 일반 추론 및 멀티모달 기능 리더 | 복잡한 도메인 추론, 이미지 분석 |
| **deepseek-r1** | 강화 학습 기반, 높은 성능 | 수학, 코드, 복잡한 추론 작업 |
| **mistral-large2** | 코드 생성, 다국어 분석 최적화 | 복잡한 작업, 멀티링구얼 |
| **llama3.1-405b** | 128K 컨텍스트 윈도우 | 긴 문서 처리, 대용량 컨텍스트 |
| **snowflake-llama3.1-405b** | SwiftKV 최적화, 75% 비용 절감 | 비용 효율적인 대규모 작업 |

### 중간 규모 모델 (Medium Models) - 균형

| 모델 | 특징 |
|------|------|
| **llama3.1-70b** | 128K 컨텍스트 |
| **snowflake-llama3.3-70b** | Snowflake 최적화 |
| **snowflake-arctic** | SQL 생성과 코딩 특화 |
| **mixtral-8x7b** | MoE 아키텍처 |

### 소규모 모델 (Small Models) - 빠르고 저렴

| 모델 | 컨텍스트 윈도우 |
|------|----------------|
| **llama3.1-8b** | 128K |
| **mistral-7b** | 32K |
| **gemma-7b** | - |

---

## 실전 추천 전략

### 프로덕션 환경

```python
# 1차: mistral-large2 (비용 효율)
response = Complete('mistral-large2', prompt)

# 품질 검증 실패 시 2차: claude-3-7-sonnet (최고 품질)
if validation_failed(response):
    response = Complete('claude-3-7-sonnet', prompt)
```

### 현재 Gemini 2.5 Pro 대체

현재 Vertex AI의 Gemini 2.5 Pro를 사용 중이라면:
- **Gemini 2.5 Pro** ≈ **claude-3-7-sonnet** (품질 우선)
- **Gemini 2.5 Pro** → **mistral-large2** (비용 절감)

---

## 테스트 코드

```python
from snowflake.cortex import Complete
import json

def generate_shop_summary(shop_name, reviews, blogs, model='mistral-large2'):
    """
    리뷰와 블로그 데이터를 기반으로 매장 요약문 생성

    Args:
        shop_name: 매장명
        reviews: 리뷰 데이터
        blogs: 블로그 데이터
        model: 사용할 Cortex AI 모델 (기본값: mistral-large2)

    Returns:
        dict: title과 summaries를 포함한 JSON 객체
    """
    prompt = f"""당신은 음식점 요약문 작성 전문가입니다.

매장명: {shop_name}

리뷰 데이터:
{reviews}

블로그 데이터:
{blogs}

위 정보를 바탕으로 다음 형식의 JSON을 작성하세요:
{{
  "title": "매장의 핵심 특징을 담은 15-30자 제목",
  "summaries": [
    "셰프 철학/브랜드 정체성 (40-60자)",
    "코스 구성/시그니처 메뉴 (40-60자)",
    "공간/분위기/미식 경험 (40-60자)"
  ]
}}

규칙:
- "최고의", "완벽한" 등 과장 표현 금지
- 구체적이고 객관적으로 작성
- 이모지 사용 금지
"""

    response = Complete(model, prompt)
    return json.loads(response)

# 사용 예시
result = generate_shop_summary(
    shop_name="스시 사이토",
    reviews="신선한 재료와 정성스러운 손맛이 느껴지는 오마카세...",
    blogs="전통 에도마에 스타일의 오마카세를 선보이는...",
    model='mistral-large2'
)

print(json.dumps(result, ensure_ascii=False, indent=2))
```

---

## 기본 사용법

### Snowflake Notebooks 환경 (별도 설치 불필요)

```python
from snowflake.cortex import Complete, Summarize, Sentiment, Translate

# 텍스트 생성
response = Complete(
    model='mistral-large2',
    prompt='서울에서 가볼만한 파인다이닝 레스토랑 3곳을 추천해주세요.'
)

# 텍스트 요약
summary = Summarize(long_review_text)

# 감정 분석 (0.0 ~ 1.0)
sentiment_score = Sentiment("음식이 정말 맛있고 서비스도 훌륭했습니다!")

# 번역
translated = Translate(
    text='This restaurant is amazing',
    from_language='en',
    to_language='ko'
)
```

### Snowpark DataFrame과 함께 사용

```python
from snowflake.snowpark import Session
from snowflake.snowpark.functions import col

# DataFrame에서 감정 분석 적용
df = session.table('REVIEWS')

df_with_sentiment = df.select(
    col('REVIEW_TEXT'),
    col('REVIEW_TEXT').call_function('SNOWFLAKE.CORTEX.SENTIMENT')
    .alias('SENTIMENT_SCORE')
)

df_with_sentiment.show()
```

---

## 로컬 환경 설정 (선택사항)

로컬 Python 환경에서 사용하려면:

```bash
pip install snowflake-snowpark-python
```

```python
from snowflake.snowpark import Session
from snowflake.cortex import Complete

# 연결 설정
connection_parameters = {
    "account": "your_account",
    "user": "your_user",
    "password": "your_password",
    "role": "your_role",
    "warehouse": "your_warehouse",
    "database": "your_database",
    "schema": "your_schema"
}

session = Session.builder.configs(connection_parameters).create()

# 사용
response = Complete('mistral-large2', 'Hello!')
```

---

## 최종 결론

**매장 요약문 생성을 위한 최적 모델: mistral-large2**

- 한국어 품질 우수
- 비용/성능 균형
- 일관된 톤앤매너 유지
- 구조화된 JSON 출력

품질이 더 중요한 경우 **claude-3-7-sonnet** 사용 권장
