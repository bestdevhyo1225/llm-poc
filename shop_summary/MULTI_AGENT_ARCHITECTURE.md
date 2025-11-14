# Multi-Agent 매장 요약문 생성 시스템 아키텍처 설계

> Database 기반 Multi-Agent LLM 시스템으로 매장 요약문을 자동 생성하는 아키텍처 설계 문서

**작성일**: 2025-11-14
**버전**: 1.0

---

## 📋 목차

1. [시스템 개요](#시스템-개요)
2. [아키텍처 패턴 제안](#아키텍처-패턴-제안)
3. [구현 프레임워크 비교](#구현-프레임워크-비교)
4. [핵심 설계 고려사항](#핵심-설계-고려사항)
5. [추천 구현 로드맵](#추천-구현-로드맵)
6. [추가 고급 기법](#추가-고급-기법)
7. [최종 추천 아키텍처](#최종-추천-아키텍처)

---

## 시스템 개요

### 요구사항

**목표**: Database에서 매장 정보와 리뷰 데이터를 조회하여, Multi-Agent 기반으로 고품질 요약문 생성

**Agent 구성**:
- **Agent #1 (Extraction)**: 매장 정보/리뷰 데이터에서 카테고리별 핵심 정보 추출
  - Output: `{category, summary, evidences}`
- **Agent #2 (Generation)**: 추출된 정보 기반으로 최종 요약문 생성
  - Output: `{title, summaries[3]}`
- **Agent #3 (Validation)**: 생성된 요약문 검증 및 수정 지침 제공
  - Output: `{is_valid, issues, modification_instructions}`

**Retry 메커니즘**: Agent #3 검증 실패 시 Agent #2로 재시도 (최대 3회)

### 카테고리별 추출 초점

#### 파인다이닝/스시오마카세
- 매장 특징 및 평가 (restaurant_review)
- 시그니처 메뉴 설명 (signature_menu)
- 분위기 (atmosphere)
- 방문 팁 (visit_tips)

#### 웨이팅 핫플레이스
- 시그니처 메뉴 (signature_menu)
- 분위기/공간 (atmosphere)
- 인기도/웨이팅 (popularity)
- 가격/가성비 (price_value)
- 위치/접근성 (location_access)

#### 중저가 예약 매장
- 메뉴 구성 (menu_composition)
- 가성비/가치 (value_proposition)
- 분위기/경험 (dining_atmosphere)
- 예약/주차 (reservation_parking)
- 셰프 접근법 (chef_approach)

---

## 아키텍처 패턴 제안

### 1. Sequential Pipeline Pattern ⭐ 추천

```
DB → Agent #1 (추출) → Agent #2 (생성) → Agent #3 (검증) → Output
                              ↑                      ↓
                              └──────── (재시도) ─────┘
```

**특징**:
- 가장 직관적이고 구현/디버깅 용이
- 각 Agent가 순차적으로 실행되어 상태 관리 간단
- Retry loop를 통한 Self-Correction 구현

**적용 방법**:
- **Agent #1**: Extraction Agent (카테고리별 정보 추출)
- **Agent #2**: Generation Agent (요약문 생성)
- **Agent #3**: Validation Agent (검증 + 수정 지침 생성)
- **Orchestrator**: 재시도 로직 관리 (최대 3회)

**장점**: 단순성, 명확한 책임 분리, 낮은 복잡도
**단점**: 병렬 처리 불가, 단일 실패 시 전체 재시작

---

### 2. Supervisor-Worker Pattern

```
                    Supervisor Agent
                          │
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                  ↓
  Extractor Agent   Generator Agent   Validator Agent
        │                 │                  │
        └─────────→ Context Pool ←──────────┘
```

**특징**:
- 중앙 Supervisor가 전체 워크플로우 조율
- Worker Agent들은 독립적으로 작동
- Context Pool을 통한 공유 메모리

**적용 방법**:
- **Supervisor**: 작업 분배, 재시도 결정, 최종 승인
- **Workers**: 각자 전문화된 작업 수행
- **Context Pool**: 매장 정보, 추출 결과, 생성 결과, 검증 피드백 저장

**장점**: 유연한 작업 분배, 확장성
**단점**: Supervisor 로직 복잡도 증가

---

### 3. Graph-Based Workflow (LangGraph 스타일)

```
Start → Extract → Generate → Validate → Success?
                     ↑           │         │
                     │           ├─ Yes → End
                     │           └─ No ─┐
                     └───────────────────┘
                         (retry < 3)
```

**특징**:
- 각 단계를 노드로, 전환 조건을 엣지로 표현
- 조건부 분기와 루프 구현 용이
- 복잡한 워크플로우 시각화 가능

**적용 방법**:
- **Node 1**: Extraction (DB 쿼리 + 정보 추출)
- **Node 2**: Generation (요약문 생성)
- **Node 3**: Validation (검증)
- **Edge**: 검증 결과에 따라 End 또는 Node 2로 재시도

**장점**: 시각적 명확성, 복잡한 조건 처리
**단점**: 초기 설정 복잡, 프레임워크 의존성

---

### 4. Reflexion Pattern (자기 반성 기반)

```
Agent #2 (Generator)
    │
    ↓ [생성]
 Output
    │
    ↓ [자기 평가]
Agent #2 + Memory (과거 시도 기억)
    │
    ↓ [개선]
 Refined Output
```

**특징**:
- Generator Agent가 스스로 출력을 평가하고 개선
- 과거 시도 이력을 메모리에 저장하여 학습
- 외부 Validator 대신 Self-Reflection 활용

**적용 방법**:
- **Agent #1**: 추출 (동일)
- **Agent #2**: 생성 + Self-Critique + Self-Refine
- **Memory System**: 과거 실패 사례와 피드백 저장
- **Retry Loop**: Self-reflection 결과 기반

**장점**: Agent 수 감소, 자가 개선 능력
**단점**: 높은 토큰 비용, Self-bias 문제

---

### 5. Multi-LLM Hybrid Pattern ⭐ 추천 (프로덕션용)

```
                    Gemini 2.0 Flash (빠른 추출)
                           ↓
                    Gemini 2.5 Pro (정교한 생성)
                           ↓
         Gemini 2.0 Flash (빠른 검증) + 규칙 기반 검증
                           ↓
                    재시도 필요 시 2.5 Pro
```

**특징**:
- 작업별로 적합한 모델 사용 (비용/성능 최적화)
- 빠른 작업은 경량 모델, 복잡한 작업은 고성능 모델
- 규칙 기반 + LLM 기반 검증 결합

**적용 방법**:
- **Agent #1**: Gemini 2.0 Flash (추출은 빠르게)
- **Agent #2**: Gemini 2.5 Pro (생성은 정교하게)
- **Agent #3**: Hybrid Validation
  - 규칙 기반 (구조, 길이, 금지어 체크)
  - LLM 기반 (의미론적 일관성, 품질 평가)

**장점**: 비용 효율, 높은 품질, 빠른 속도
**단점**: 다중 모델 관리 복잡도

---

### 6. Assembly Line with RAG Augmentation

```
DB → RAG Retrieval → Agent #1 → Agent #2 → Agent #3
     (유사 매장)      (추출)      (생성)      (검증)
         ↓              ↓           ↓
    Context Pool ──────────────────┘
```

**특징**:
- 현재 RAG 시스템과 Multi-Agent 결합
- 유사 매장 예시를 컨텍스트로 활용
- 각 Agent가 RAG 검색 결과 공유

**적용 방법**:
- **RAG**: 입력 매장과 유사한 매장 요약문 검색
- **Agent #1**: RAG 컨텍스트 + DB 데이터로 추출
- **Agent #2**: RAG 예시 스타일 학습하여 생성
- **Agent #3**: RAG 예시 기반 품질 기준으로 검증

**장점**: 기존 시스템 활용, 일관성 향상
**단점**: RAG + Multi-Agent 복잡도

---

## 구현 프레임워크 비교

| 프레임워크 | 적합한 패턴 | 학습 곡선 | 프로덕션 준비 | 권장 용도 |
|-----------|------------|----------|--------------|----------|
| **LangGraph** | Graph-based, Sequential | 높음 | ⭐⭐⭐⭐⭐ | 복잡한 워크플로우, 엔터프라이즈 |
| **CrewAI** | Role-based, Supervisor | 낮음 | ⭐⭐⭐⭐ | 빠른 프로토타입, 팀 기반 |
| **AutoGen** | Conversational, Multi-agent | 중간 | ⭐⭐⭐ | 코드 생성, 대화형 시스템 |
| **Custom (Vertex AI)** | 모든 패턴 | 중간 | ⭐⭐⭐⭐ | 기존 인프라 활용 |

### 권장 선택

#### 초기 프로토타입
- **프레임워크**: CrewAI
- **이유**: 빠른 구현, 낮은 학습 곡선, 우수한 문서화

#### 프로덕션 배포
- **프레임워크**: LangGraph
- **이유**: 안정성, 모니터링 기능, 엔터프라이즈급 지원

#### GCP 생태계 활용
- **프레임워크**: Custom Vertex AI Agent Builder
- **이유**: 기존 인프라 활용, GCP 네이티브 통합 (2025년 GA)

---

## 핵심 설계 고려사항

### 1. Context Engineering

Agent 간 전달되는 컨텍스트 구조:

```python
{
  "shop_data": {
    "shop_seq": 12345,
    "shop_name": "모수 서울",
    "reviews": [...],
    "basic_info": {...}
  },
  "extracted_info": {
    "category": "restaurant_review",
    "summary": "한국 미식의 위상을 높인 이노베이티브 한식",
    "evidences": ["현지 식재료", "창의적 한식", "모던한 플레이팅"]
  },
  "rag_examples": [
    {
      "shop_name": "유사 매장 1",
      "title": "...",
      "summaries": [...]
    }
  ],
  "retry_count": 0,
  "previous_attempts": [
    {
      "attempt": 1,
      "output": {...},
      "validation_result": {...}
    }
  ]
}
```

**설계 원칙**:
- 각 Agent는 필요한 정보만 선택적으로 접근
- 이전 시도 이력을 포함하여 Self-Improvement 유도
- RAG 예시를 컨텍스트로 포함하여 스타일 일관성 확보

---

### 2. Memory Management

#### Short-term Memory
- **범위**: 현재 요청의 Agent 간 공유 상태
- **구현**: In-memory dictionary 또는 Redis
- **생명주기**: 요청 완료 시 소멸

#### Long-term Memory
- **범위**: 성공/실패 사례 저장
- **구현**: Chroma Vector DB (RAG 용)
- **활용**: 유사 매장 검색, 스타일 학습

#### Episodic Memory
- **범위**: Agent #3의 수정 지침 히스토리
- **구현**: 구조화된 로그 (BigQuery/Cloud Logging)
- **활용**: 반복되는 실패 패턴 분석, 프롬프트 개선

---

### 3. Retry Strategy

Exponential Backoff + Modification Injection 전략:

```python
retry_policies = {
    "attempt_1": {
        "timeout": 30,  # seconds
        "modifications": [],
        "temperature": 0.5
    },
    "attempt_2": {
        "timeout": 45,
        "modifications": ["더 구체적으로", "예시 스타일 참고"],
        "temperature": 0.7  # 약간 창의적으로
    },
    "attempt_3": {
        "timeout": 60,
        "modifications": ["RAG 예시와 동일한 구조", "금지어 제거"],
        "temperature": 0.3  # 보수적으로
    }
}
```

**재시도 중단 조건**:
- 3회 연속 실패
- 동일한 출력 2회 반복 (개선 불가 판단)
- Timeout 초과

---

### 4. Validation Strategy (Agent #3 설계)

#### Option A: 규칙 기반 (현재 시스템)

```python
def rule_based_validation(summary):
    checks = {
        "structure": has_required_fields(summary),  # title, summaries
        "length": check_length_constraints(summary),  # 40-60자
        "forbidden_words": not has_forbidden_words(summary),  # 최고의, 완벽한
        "duplication": not has_duplicate_sentences(summary),  # 문장 간 70% 이상 유사
        "special_chars": not has_emojis(summary)
    }
    return all(checks.values()), checks
```

**장점**: 빠름 (0.1초), 저비용, 명확한 기준
**단점**: 의미론적 품질 평가 불가

---

#### Option B: LLM 기반

```python
def llm_based_validation(summary, extracted_info):
    prompt = f"""
    다음 요약문을 평가하세요:
    {summary}

    추출된 정보:
    {extracted_info}

    평가 기준:
    1. 정보 정확성: 추출된 정보와 일치하는가?
    2. 톤앤매너: 카테고리에 맞는 스타일인가?
    3. 의미론적 일관성: 3개 문장이 조화로운가?
    4. 가독성: 자연스럽고 명확한가?

    JSON 형식으로 평가 결과를 반환하세요.
    """
    return gemini_call(prompt)
```

**장점**: 의미론적 품질 평가, 컨텍스트 이해
**단점**: 느림 (2-3초), 고비용, 일관성 낮음

---

#### Option C: Hybrid ⭐ 추천

```python
def hybrid_validation(summary, extracted_info):
    # Phase 1: 규칙 기반 (빠른 실패)
    rule_valid, rule_checks = rule_based_validation(summary)

    if not rule_valid:
        return False, {
            "method": "rule_based",
            "checks": rule_checks,
            "suggestions": generate_rule_suggestions(rule_checks)
        }

    # Phase 2: LLM 기반 (정교한 평가)
    llm_result = llm_based_validation(summary, extracted_info)

    return llm_result.is_valid, {
        "method": "hybrid",
        "rule_checks": rule_checks,
        "llm_evaluation": llm_result
    }
```

**장점**: 빠른 실패 처리 + 정교한 품질 평가
**단점**: 구현 복잡도

---

### 5. Feedback Loop Design

Agent #3 → Agent #2 피드백 구조:

```python
{
  "validation_result": "FAIL",
  "retry_attempt": 1,
  "issues": [
    {
      "type": "length_violation",
      "severity": "high",  # high, medium, low
      "location": "summaries[0]",
      "current_value": "모수 서울은 한국 미식의 위상을 높였다는 평가를 받는 이노베이티브 한식 다이닝입니다. 현지 식재료에 대한 존중을 바탕으로 창의적인 한식을 선보입니다. (68자)",
      "expected": "40-60자",
      "suggestion": "첫 문장을 45자로 단축하세요. '현지 식재료에 대한 존중을 바탕으로' 부분을 축약 가능"
    },
    {
      "type": "tone_inconsistency",
      "severity": "medium",
      "location": "title",
      "current_value": "최고의 이노베이티브 한식",
      "suggestion": "'최고의'는 금지어입니다. '식재료에 대한 존중이 돋보이는'으로 변경"
    },
    {
      "type": "duplication",
      "severity": "low",
      "location": "summaries[1] vs summaries[2]",
      "suggestion": "두 문장이 모두 '메뉴'에 대해 언급합니다. 한 문장은 공간/분위기로 변경"
    }
  ],
  "modification_instructions": """
  1. 첫 번째 문장 길이를 60자 이내로 단축
  2. 제목에서 '최고의' 제거 및 대체 표현 사용
  3. 세 번째 문장을 메뉴가 아닌 분위기/경험으로 변경

  예시 참고:
  - 제목: "식재료에 대한 존중이 돋보이는 이노베이티브 퀴진"
  - 문장1: "모수 서울은 현지 식재료를 존중하는 이노베이티브 한식 다이닝입니다."
  """
}
```

**피드백 설계 원칙**:
- 구체적인 위치 명시 (location)
- 현재 값과 기대 값 제공
- 실행 가능한 수정 제안 (actionable)
- 우선순위 구분 (severity)

---

## 추천 구현 로드맵

### Phase 1: 기본 Sequential Pipeline (2주)

**목표**: 3개 Agent + Retry loop 구현

```python
def process_shop(shop_seq, category):
    """
    매장 요약문 생성 메인 함수
    """
    # 1. DB 조회
    shop_data = query_database(shop_seq)

    # 2. Agent #1: 정보 추출
    extracted = extraction_agent(
        shop_data=shop_data,
        category=category,
        source_types=get_source_types(category)
    )

    # 3. Agent #2: 요약문 생성 (최대 3번 재시도)
    context = {
        "shop_data": shop_data,
        "extracted_info": extracted,
        "previous_attempts": []
    }

    for attempt in range(1, 4):
        # 요약문 생성
        summary = generation_agent(
            context=context,
            retry_config=get_retry_config(attempt)
        )

        # 4. Agent #3: 검증
        validation = validation_agent(
            summary=summary,
            extracted_info=extracted,
            category=category
        )

        if validation["is_valid"]:
            # 성공: Vector DB 저장
            save_to_vector_db(summary, category)
            log_success(shop_seq, attempt)
            return summary

        # 실패: 피드백 저장 후 재시도
        context["previous_attempts"].append({
            "attempt": attempt,
            "output": summary,
            "validation": validation
        })

        log_retry(shop_seq, attempt, validation)

    # 3회 모두 실패
    log_failure(shop_seq, context)
    return None
```

**구현 작업**:
- [ ] DB 연결 및 쿼리 함수
- [ ] Agent #1 프롬프트 설계 (카테고리별)
- [ ] Agent #2 프롬프트 설계 (Few-shot 예시 포함)
- [ ] Agent #3 규칙 기반 검증 로직
- [ ] Retry orchestration 구현
- [ ] 로깅 시스템 구축

---

### Phase 2: RAG 통합 (1주)

**목표**: 유사 매장 예시 검색 및 컨텍스트 주입

```python
def process_shop_with_rag(shop_seq, category):
    shop_data = query_database(shop_seq)

    # RAG: 유사 매장 검색 (추가)
    similar_shops = retrieve_similar_examples(
        query_text=shop_data["description"],
        collection=f"{category}_examples",
        top_k=2
    )

    extracted = extraction_agent(
        shop_data=shop_data,
        category=category,
        rag_context=similar_shops  # RAG 컨텍스트 주입
    )

    context = {
        "shop_data": shop_data,
        "extracted_info": extracted,
        "rag_examples": similar_shops,  # RAG 예시 포함
        "previous_attempts": []
    }

    # 나머지 동일...
```

**구현 작업**:
- [ ] Chroma 컬렉션 초기화
- [ ] 임베딩 생성 함수 (Vertex AI)
- [ ] 유사도 검색 함수
- [ ] 프롬프트에 RAG 예시 포맷 추가

---

### Phase 3: Multi-LLM 최적화 (1주)

**목표**: 작업별 최적 모델 적용

```python
# 모델 선택 전략
MODEL_CONFIG = {
    "extraction": {
        "model": "gemini-2.0-flash-exp",
        "temperature": 0.3,
        "max_tokens": 2048,
        "reason": "빠른 정보 추출"
    },
    "generation": {
        "model": "gemini-2.5-pro",
        "temperature": 0.5,
        "max_tokens": 4096,
        "reason": "고품질 요약문 생성"
    },
    "validation_llm": {
        "model": "gemini-2.0-flash-exp",
        "temperature": 0.1,
        "max_tokens": 1024,
        "reason": "빠른 검증"
    }
}

def get_model_config(agent_type):
    return MODEL_CONFIG[agent_type]
```

**구현 작업**:
- [ ] 다중 모델 초기화
- [ ] 모델별 프롬프트 최적화
- [ ] 비용/성능 모니터링
- [ ] A/B 테스트 (Flash vs Pro)

---

### Phase 4: 프로덕션 강화 (2주)

**목표**: LangGraph 전환 및 프로덕션 배포

```python
from langgraph.graph import StateGraph, END

# State 정의
class ShopSummaryState(TypedDict):
    shop_seq: int
    shop_data: dict
    extracted_info: dict
    summary: dict
    validation: dict
    retry_count: int

# Graph 정의
workflow = StateGraph(ShopSummaryState)

# Node 추가
workflow.add_node("extract", extraction_agent)
workflow.add_node("generate", generation_agent)
workflow.add_node("validate", validation_agent)

# Edge 추가
workflow.add_edge("extract", "generate")
workflow.add_edge("generate", "validate")

# 조건부 Edge
workflow.add_conditional_edges(
    "validate",
    should_retry,
    {
        "retry": "generate",
        "success": END,
        "failure": END
    }
)

# 시작점 설정
workflow.set_entry_point("extract")

# 컴파일
app = workflow.compile()
```

**구현 작업**:
- [ ] LangGraph 마이그레이션
- [ ] State 관리 최적화
- [ ] 에러 핸들링 강화
- [ ] 배치 처리 구현 (100개 매장 동시 처리)
- [ ] 모니터링 대시보드 (Grafana)
- [ ] 알람 시스템 (Slack 연동)

---

## 추가 고급 기법

### 1. Tree of Thought (ToT) - Agent #2 내부 사용

**개념**: Generation Agent가 여러 후보를 생성한 후 가장 좋은 것을 선택

```python
def generation_agent_with_tot(context):
    # 1. 3개 후보 생성
    candidates = []
    for i in range(3):
        candidate = generate_summary(
            context=context,
            temperature=0.5 + (i * 0.1)  # 다양성 확보
        )
        candidates.append(candidate)

    # 2. Self-evaluation
    evaluations = []
    for candidate in candidates:
        score = self_evaluate(
            candidate=candidate,
            criteria=["정보 충실도", "가독성", "톤앤매너"]
        )
        evaluations.append(score)

    # 3. 최고 점수 선택
    best_idx = evaluations.index(max(evaluations))
    return candidates[best_idx]
```

**장점**: 품질 향상 (10-15%)
**단점**: 토큰 비용 3배 증가

**적용 시나리오**:
- 파인다이닝 (높은 품질 요구)
- 1차 시도 실패 후 2차 시도

---

### 2. Chain-of-Thought Prompting - Agent #1에 적용

**개념**: 단계별 추론 과정을 명시하여 정확도 향상

```python
extraction_prompt = """
당신은 매장 정보에서 핵심 정보를 추출하는 전문가입니다.

다음 단계를 따라 정보를 추출하세요:

1단계: 리뷰에서 시그니처 메뉴 언급을 찾으세요
   - "시그니처", "대표 메뉴", "추천" 키워드 검색
   - 자주 언급되는 메뉴명 파악

2단계: 분위기 관련 키워드를 추출하세요
   - "분위기", "공간", "인테리어" 관련 표현
   - 형용사 중심으로 정리

3단계: 가격대를 판단하세요
   - 리뷰에 언급된 가격 정보
   - "가성비", "비싸다", "저렴하다" 표현

4단계: 접근성을 평가하세요
   - 위치 정보
   - "역에서", "주차" 관련 정보

매장 정보:
{shop_data}

각 단계별로 생각을 작성한 후, 최종 JSON 형식으로 정리하세요.
"""
```

**장점**: 추출 정확도 향상, 디버깅 용이
**단점**: 프롬프트 길이 증가

---

### 3. Constitutional AI - Agent #3에 적용

**개념**: 명확한 원칙(Constitution)을 정의하여 검증

```python
VALIDATION_PRINCIPLES = {
    "factuality": {
        "principle": "요약문은 과장 없이 사실 기반이어야 한다",
        "violations": ["최고의", "완벽한", "최상의", "독보적인"],
        "severity": "high"
    },
    "tone_consistency": {
        "principle": "카테고리별 톤앤매너를 준수해야 한다",
        "examples": {
            "fine_dining": "존중, 정교함, 미식 경험",
            "waiting_hotplace": "활기참, 인기, 접근성",
            "mid_price": "가성비, 편안함, 실용성"
        },
        "severity": "high"
    },
    "diversity": {
        "principle": "3개 문장이 중복 없이 다른 측면을 다뤄야 한다",
        "check": "문장 간 유사도 < 70%",
        "severity": "medium"
    },
    "readability": {
        "principle": "자연스럽고 명확한 문장이어야 한다",
        "check": "문장 길이 40-60자, 특수문자 없음",
        "severity": "medium"
    }
}

def constitutional_validation(summary, category):
    violations = []

    for principle_name, principle in VALIDATION_PRINCIPLES.items():
        is_violated = check_principle(summary, principle, category)
        if is_violated:
            violations.append({
                "principle": principle_name,
                "description": principle["principle"],
                "severity": principle["severity"]
            })

    return len(violations) == 0, violations
```

**장점**: 명확한 기준, 일관성, 설명 가능성
**단점**: 원칙 정의 필요, 유지보수

---

### 4. Active Learning Loop

**개념**: 실패 사례를 재학습 데이터로 활용하여 시스템 개선

```python
# 실패 사례 수집
def collect_failed_cases():
    """
    BigQuery에서 검증 실패 사례 조회
    """
    query = """
    SELECT
        shop_seq,
        shop_data,
        extracted_info,
        failed_summary,
        validation_issues
    FROM failed_summaries
    WHERE retry_count = 3
    AND created_at > DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
    """
    return bigquery_client.query(query).to_dataframe()

# 실패 패턴 분석
def analyze_failure_patterns(failed_cases):
    """
    반복되는 실패 원인 분석
    """
    issue_counts = defaultdict(int)

    for case in failed_cases:
        for issue in case["validation_issues"]:
            issue_counts[issue["type"]] += 1

    # 상위 5개 실패 원인
    top_issues = sorted(
        issue_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]

    return top_issues

# 프롬프트 자동 개선
def improve_prompts(failure_patterns):
    """
    실패 패턴 기반으로 프롬프트 수정
    """
    for issue_type, count in failure_patterns:
        if issue_type == "length_violation":
            # Generation 프롬프트에 강조 추가
            add_prompt_constraint(
                "각 문장은 반드시 40-60자로 작성하세요. "
                "이는 필수 요구사항입니다."
            )

        elif issue_type == "tone_inconsistency":
            # Few-shot 예시 추가
            add_few_shot_examples(
                category=get_problem_category(issue_type),
                count=3
            )

# 주간 자동 개선
def weekly_improvement_job():
    """
    매주 일요일 자동 실행
    """
    failed_cases = collect_failed_cases()
    failure_patterns = analyze_failure_patterns(failed_cases)
    improve_prompts(failure_patterns)

    # 개선 내역 알림
    send_slack_notification(
        f"프롬프트 자동 개선 완료: {len(failure_patterns)}개 패턴 반영"
    )
```

**장점**: 지속적인 품질 향상, 무인 운영
**단점**: 복잡한 파이프라인, 모니터링 필요

---

## 최종 추천 아키텍처

### 프로토타입 단계 (1-2주)

**패턴**: Sequential Pipeline + Reflexion
**프레임워크**: Custom Vertex AI (기존 인프라 활용)
**검증**: Hybrid (규칙 + LLM)

```
DB Query
   ↓
Agent #1: Extraction (Gemini 2.0 Flash)
   ↓
Agent #2: Generation (Gemini 2.5 Pro) ←──┐
   ↓                                      │
Agent #3: Validation (Rule + Flash)      │
   ↓                                      │
Success? ──No (retry<3)──────────────────┘
   ↓ Yes
Save to Vector DB + Log
```

**예상 성능**:
- 처리 시간: 5-10초/매장
- 성공률: 75-80% (1차 시도)
- 비용: $0.003/매장

---

### 프로덕션 단계 (1-2개월 후)

**패턴**: Multi-LLM Hybrid + RAG Augmentation
**프레임워크**: LangGraph (모니터링, 확장성)
**검증**: 규칙 기반 → LLM (2단계)
**최적화**: Agent #1/3은 Flash, Agent #2는 Pro

```
DB Query + RAG Retrieval (유사 매장 검색)
   ↓
Agent #1: Extraction (Flash, CoT)
   ↓
Agent #2: Generation (Pro, ToT) ←──────┐
   ↓                                    │
Agent #3a: Rule Validation ──No──→ Retry
   ↓ Pass                               │
Agent #3b: LLM Validation (Flash)       │
   ↓                                    │
Success? ──No (retry<3)─────────────────┘
   ↓ Yes
Save to Vector DB + Active Learning Pool
```

**예상 성능**:
- 처리 시간: 8-15초/매장
- 성공률: 90-95% (1차 시도)
- 비용: $0.005/매장

**배치 처리**:
- 100개 매장 동시 처리 (병렬)
- 총 처리 시간: 15-20분
- 시간당 처리량: 300-400개 매장

---

### 장기 로드맵 (3-6개월)

**Phase 5: Self-Improving System**
- Active Learning Loop 구축
- 실패 패턴 자동 분석
- 프롬프트 자동 최적화
- Few-shot 예시 자동 선별

**Phase 6: Multi-Category Optimization**
- 카테고리별 전문 모델 Fine-tuning
- 카테고리 간 Transfer Learning
- Ensemble 방식 도입 (여러 Agent 결과 투표)

**Phase 7: Production Scale**
- 10,000개 매장 일일 처리
- Real-time 요약문 생성 API
- 멀티 리전 배포 (지연시간 최소화)

---

## 비용 분석

### 프로토타입 (Sequential Pipeline)

**가정**: 1,000개 매장 처리

| 항목 | 모델 | 토큰 | 단가 | 비용 |
|-----|------|------|------|------|
| Agent #1 | Flash | 2K input + 1K output | $0.10/$0.30 per 1M | $0.0005 |
| Agent #2 | Pro | 4K input + 2K output | $1.25/$5.00 per 1M | $0.0150 |
| Agent #3 | 규칙+Flash | 2K input + 0.5K output | $0.10/$0.30 per 1M | $0.0003 |
| **매장당** | - | - | - | **$0.0158** |
| **1,000개** | - | - | - | **$15.80** |

---

### 프로덕션 (Multi-LLM + RAG + ToT)

**가정**: 10,000개 매장 처리, 재시도율 20%

| 항목 | 모델 | 토큰 | 단가 | 비용 |
|-----|------|------|------|------|
| RAG Embedding | Vertex AI | 500 tokens | 무료 (100만/월) | $0.0000 |
| Agent #1 | Flash + CoT | 3K input + 1K output | $0.10/$0.30 per 1M | $0.0006 |
| Agent #2 (ToT) | Pro x3 | 12K input + 6K output | $1.25/$5.00 per 1M | $0.0450 |
| Agent #3a | 규칙 | 0 | $0 | $0.0000 |
| Agent #3b | Flash | 2K input + 0.5K output | $0.10/$0.30 per 1M | $0.0003 |
| 재시도 (20%) | Pro | 4K input + 2K output | $1.25/$5.00 per 1M | $0.0030 |
| **매장당** | - | - | - | **$0.0489** |
| **10,000개** | - | - | - | **$489.00** |

**연간 예상 비용** (100만 매장):
- 프로토타입: $15,800
- 프로덕션: $48,900

---

## 모니터링 지표

### 성능 지표 (KPIs)

```python
metrics = {
    "throughput": {
        "shops_per_hour": 300,
        "target": 400,
        "alert_threshold": 200
    },
    "quality": {
        "success_rate_first_attempt": 0.85,
        "target": 0.90,
        "alert_threshold": 0.75
    },
    "cost": {
        "cost_per_shop": 0.0489,
        "target": 0.0400,
        "alert_threshold": 0.0600
    },
    "latency": {
        "p50_seconds": 8,
        "p95_seconds": 15,
        "p99_seconds": 25,
        "alert_threshold_p95": 20
    }
}
```

### 대시보드 구성 (Grafana)

**Panel 1**: 시간당 처리량
- 그래프: 매시간 처리된 매장 수
- 알람: 200개 미만 시 Slack 알림

**Panel 2**: 성공률 추이
- 그래프: 1차/2차/3차 시도별 성공률
- 알람: 1차 성공률 75% 미만

**Panel 3**: 비용 추이
- 그래프: 일일 총 비용, 매장당 비용
- 알람: 일일 $100 초과

**Panel 4**: 검증 실패 원인
- 파이 차트: issue_type별 분포
- 테이블: 상위 10개 실패 원인

**Panel 5**: 레이턴시 분포
- 히스토그램: p50/p95/p99
- 알람: p95 > 20초

---

## 부록: 프레임워크별 샘플 코드

### A. LangGraph 구현 예시

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class ShopSummaryState(TypedDict):
    shop_seq: int
    shop_data: dict
    category: str
    extracted_info: Annotated[dict, operator.add]
    summary: dict
    validation: dict
    retry_count: int
    errors: list

def extraction_node(state: ShopSummaryState):
    """Agent #1: 정보 추출"""
    extracted = extraction_agent(
        shop_data=state["shop_data"],
        category=state["category"]
    )
    return {"extracted_info": extracted}

def generation_node(state: ShopSummaryState):
    """Agent #2: 요약문 생성"""
    summary = generation_agent(
        extracted_info=state["extracted_info"],
        retry_count=state["retry_count"]
    )
    return {"summary": summary}

def validation_node(state: ShopSummaryState):
    """Agent #3: 검증"""
    validation = validation_agent(
        summary=state["summary"],
        extracted_info=state["extracted_info"]
    )
    return {"validation": validation}

def should_retry(state: ShopSummaryState):
    """재시도 여부 결정"""
    if state["validation"]["is_valid"]:
        return "success"
    elif state["retry_count"] >= 3:
        return "failure"
    else:
        return "retry"

# Graph 구성
workflow = StateGraph(ShopSummaryState)

workflow.add_node("extract", extraction_node)
workflow.add_node("generate", generation_node)
workflow.add_node("validate", validation_node)

workflow.add_edge("extract", "generate")
workflow.add_edge("generate", "validate")

workflow.add_conditional_edges(
    "validate",
    should_retry,
    {
        "retry": "generate",
        "success": END,
        "failure": END
    }
)

workflow.set_entry_point("extract")
app = workflow.compile()

# 실행
result = app.invoke({
    "shop_seq": 12345,
    "shop_data": {...},
    "category": "fine_dining",
    "retry_count": 0,
    "errors": []
})
```

---

### B. CrewAI 구현 예시

```python
from crewai import Agent, Task, Crew, Process

# Agent 정의
extractor = Agent(
    role="Information Extractor",
    goal="매장 데이터에서 카테고리별 핵심 정보 추출",
    backstory="당신은 음식점 리뷰 분석 전문가입니다.",
    model="gemini-2.0-flash"
)

generator = Agent(
    role="Summary Generator",
    goal="추출된 정보를 바탕으로 고품질 요약문 생성",
    backstory="당신은 미식 작가이자 편집자입니다.",
    model="gemini-2.5-pro"
)

validator = Agent(
    role="Quality Validator",
    goal="생성된 요약문의 품질 검증 및 피드백 제공",
    backstory="당신은 콘텐츠 품질 관리 전문가입니다.",
    model="gemini-2.0-flash"
)

# Task 정의
extraction_task = Task(
    description="매장 정보에서 {category} 카테고리에 맞는 정보 추출",
    agent=extractor,
    expected_output="JSON 형식의 추출 결과 (category, summary, evidences)"
)

generation_task = Task(
    description="추출된 정보를 바탕으로 요약문 생성",
    agent=generator,
    expected_output="JSON 형식의 요약문 (title, summaries)",
    context=[extraction_task]  # extraction_task 결과를 컨텍스트로
)

validation_task = Task(
    description="생성된 요약문 검증",
    agent=validator,
    expected_output="검증 결과 (is_valid, issues, suggestions)",
    context=[extraction_task, generation_task]
)

# Crew 구성
crew = Crew(
    agents=[extractor, generator, validator],
    tasks=[extraction_task, generation_task, validation_task],
    process=Process.sequential,  # 순차 실행
    max_rpm=10  # 분당 최대 요청 수
)

# 실행
result = crew.kickoff(inputs={
    "shop_data": {...},
    "category": "fine_dining"
})
```

---

### C. Custom Vertex AI 구현 예시

```python
import vertexai
from vertexai.generative_models import GenerativeModel

# 초기화
vertexai.init(project="wad-dw", location="us-central1")

class MultiAgentPipeline:
    def __init__(self):
        self.flash = GenerativeModel("gemini-2.0-flash-exp")
        self.pro = GenerativeModel("gemini-2.5-pro")

    def extraction_agent(self, shop_data, category):
        """Agent #1: 정보 추출"""
        prompt = f"""
        매장 정보에서 {category} 카테고리에 맞는 정보를 추출하세요.

        매장 정보:
        {shop_data}

        JSON 형식으로 반환:
        {{
            "category": "...",
            "summary": "...",
            "evidences": [...]
        }}
        """

        response = self.flash.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 2048
            }
        )

        return json.loads(response.text)

    def generation_agent(self, extracted_info, retry_count):
        """Agent #2: 요약문 생성"""
        prompt = f"""
        다음 정보를 바탕으로 매장 요약문을 생성하세요.

        추출 정보:
        {extracted_info}

        요구사항:
        - title: 15-30자
        - summaries: 정확히 3개 문장, 각 40-60자

        JSON 형식으로 반환.
        """

        if retry_count > 0:
            prompt += f"\n\n이전 시도가 실패했습니다. {retry_count}번째 재시도입니다."

        response = self.pro.generate_content(
            prompt,
            generation_config={
                "temperature": 0.5 + (retry_count * 0.1),
                "max_output_tokens": 4096
            }
        )

        return json.loads(response.text)

    def validation_agent(self, summary, extracted_info):
        """Agent #3: 검증 (Hybrid)"""
        # Phase 1: 규칙 기반
        rule_valid, rule_issues = self.rule_validation(summary)

        if not rule_valid:
            return {
                "is_valid": False,
                "method": "rule_based",
                "issues": rule_issues
            }

        # Phase 2: LLM 기반
        prompt = f"""
        다음 요약문을 평가하세요.

        요약문:
        {summary}

        추출 정보:
        {extracted_info}

        평가 기준:
        1. 정보 정확성
        2. 톤앤매너
        3. 의미론적 일관성

        JSON 형식으로 평가 결과 반환.
        """

        response = self.flash.generate_content(prompt)
        llm_result = json.loads(response.text)

        return {
            "is_valid": llm_result["is_valid"],
            "method": "hybrid",
            "rule_checks": rule_issues,
            "llm_evaluation": llm_result
        }

    def rule_validation(self, summary):
        """규칙 기반 검증"""
        issues = []

        # 구조 체크
        if "title" not in summary or "summaries" not in summary:
            issues.append({"type": "structure", "message": "필수 키 누락"})

        # 길이 체크
        if len(summary.get("summaries", [])) != 3:
            issues.append({"type": "structure", "message": "summaries는 정확히 3개"})

        for i, s in enumerate(summary.get("summaries", [])):
            if not (40 <= len(s) <= 60):
                issues.append({
                    "type": "length",
                    "location": f"summaries[{i}]",
                    "message": f"길이 {len(s)}자 (40-60자 권장)"
                })

        # 금지어 체크
        forbidden = ["최고의", "완벽한", "최상의"]
        for word in forbidden:
            if word in str(summary):
                issues.append({
                    "type": "forbidden_word",
                    "message": f"'{word}' 사용 금지"
                })

        return len(issues) == 0, issues

    def process(self, shop_seq, shop_data, category):
        """메인 파이프라인"""
        # 1. 추출
        extracted = self.extraction_agent(shop_data, category)

        # 2. 생성 + 검증 (최대 3회)
        for attempt in range(3):
            summary = self.generation_agent(extracted, attempt)
            validation = self.validation_agent(summary, extracted)

            if validation["is_valid"]:
                return {
                    "success": True,
                    "summary": summary,
                    "attempts": attempt + 1
                }

        # 실패
        return {
            "success": False,
            "last_validation": validation,
            "attempts": 3
        }

# 사용
pipeline = MultiAgentPipeline()
result = pipeline.process(
    shop_seq=12345,
    shop_data={...},
    category="fine_dining"
)
```

---

## 참고 자료

### 논문 및 연구
- [Reflexion: Language Agents with Verbal Reinforcement Learning](https://arxiv.org/abs/2303.11366)
- [Tree of Thoughts: Deliberate Problem Solving with LLMs](https://arxiv.org/abs/2305.10601)
- [Self-Refine: Iterative Refinement with Self-Feedback](https://arxiv.org/abs/2303.17651)
- [Constitutional AI: Harmlessness from AI Feedback](https://arxiv.org/abs/2212.08073)

### 프레임워크 문서
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [CrewAI Documentation](https://docs.crewai.com/)
- [AutoGen Documentation](https://microsoft.github.io/autogen/)
- [Vertex AI Agent Builder](https://cloud.google.com/vertex-ai/docs/agent-builder)

### 아키텍처 패턴
- [AI Agent Orchestration Patterns - Azure](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Agentic AI Patterns - AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/agentic-ai-patterns/)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|-----|------|----------|--------|
| 1.0 | 2025-11-14 | 초안 작성 | Claude Code |

---

**문의**: 추가 질문이나 구체적인 구현 방법이 필요하시면 말씀해주세요.
