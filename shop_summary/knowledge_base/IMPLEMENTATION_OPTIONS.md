# 🎯 Knowledge Base 구축 방향 정리

## 현재 상황 분석

### ❌ 현재 방식의 문제점: "LLM 지식 기반"은 진짜 RAG가 아님

```
현재: LLM 지식으로 생성 → Chroma 저장 → 검색 → LLM에게 다시 제공
```

**문제:**
1. **순환 논리**: LLM이 만든 내용을 다시 LLM에게 주는 것
2. **외부 지식이 아님**: LLM의 내부 지식을 구조화한 것일 뿐
3. **할루시네이션 증폭**: 잘못 생성된 내용이 knowledge base에 저장되면 계속 참고됨
4. **검증 불가능**: 실제 출처가 없어 사실 확인 어려움

### ✅ 진짜 RAG 시스템이라면

```
외부 소스 크롤링 → Chroma 저장 → 검색 → LLM에게 제공
```

**장점:**
1. **실제 외부 지식**: 미쉐린 가이드, 블로그 리뷰 등 실제 문서
2. **검증 가능**: URL로 출처 확인
3. **최신성**: 크롤링 시점 기준 최신 정보
4. **신뢰도**: 할루시네이션 아닌 실제 사실

---

## 📊 3가지 구현 옵션 비교

| 항목 | 옵션 1: 네이버 블로그 | 옵션 2: 하이브리드 | 옵션 3: LLM 지식 유지 |
|------|---------------------|------------------|---------------------|
| **구현 난이도** | 중간 | 높음 | 없음 (현재 상태) |
| **구현 기간** | 1주 | 2-3주 | 0일 |
| **데이터 품질** | 중상 | 최상 | 중하 |
| **신뢰도** | ✅ 검증 가능 | ✅ 검증 가능 | ❌ 검증 불가 |
| **커버리지** | 100% | 100% | 100% |
| **비용** | 무료 (API 한도 내) | 무료~소량 | $200 (현재) |
| **유지보수** | 쉬움 | 복잡 | 없음 |

---

## 옵션 1: 네이버 블로그 중심 ⭐ 추천

### 개념
```
매장 + 소스타입 → 네이버 블로그 검색 → 상위 블로그 크롤링 → LLM 요약 → Chroma 저장
```

### 아키텍처
```python
# 소스 타입별 검색 키워드 매핑
SOURCE_KEYWORDS = {
    # 파인다이닝
    "michelin_review": ["미쉐린", "별점", "가이드"],
    "blueribbon_review": ["블루리본", "서베이"],
    "chef_interview": ["셰프", "인터뷰", "철학"],
    "course_description": ["코스", "메뉴", "구성"],
    "brand_philosophy": ["철학", "공간", "분위기", "전통"],

    # 웨이팅 핫플레이스
    "signature_menu": ["시그니처", "메뉴", "추천", "인기"],
    "atmosphere": ["분위기", "인테리어", "공간"],
    "popularity": ["웨이팅", "인기", "줄서는", "핫플"],
    "price_value": ["가격", "가성비", "비용"],
    "location_access": ["위치", "찾아가는법", "주차", "교통"],

    # 중저가 예약 매장
    "menu_composition": ["메뉴", "구성", "종류"],
    "value_proposition": ["가성비", "가격", "가치"],
    "dining_atmosphere": ["분위기", "경험", "서비스"],
    "reservation_parking": ["예약", "주차", "방문"],
    "chef_approach": ["셰프", "조리", "철학"],
}

def collect_from_naver_blog(shop_name: str, source_type: str) -> dict:
    """네이버 블로그에서 실제 데이터 수집"""

    # 1. 검색 키워드 생성
    keywords = SOURCE_KEYWORDS[source_type]
    query = f"{shop_name} {' '.join(keywords[:2])}"

    # 2. 네이버 블로그 검색 API 호출
    blogs = naver_blog_search_api(
        query=query,
        display=10,  # 상위 10개
        sort="sim"   # 정확도순
    )

    if not blogs:
        return {"success": False, "reason": "검색 결과 없음"}

    # 3. 상위 블로그 크롤링
    blog_texts = []
    for blog in blogs[:5]:  # 상위 5개만
        try:
            content = crawl_blog_content(blog['link'])
            blog_texts.append({
                "content": content,
                "url": blog['link'],
                "title": blog['title'],
                "date": blog['postdate']
            })
        except:
            continue

    if not blog_texts:
        return {"success": False, "reason": "크롤링 실패"}

    # 4. LLM으로 소스 타입에 맞게 요약
    combined_text = "\n\n".join([
        f"[블로그 {i+1}] {b['title']}\n{b['content']}"
        for i, b in enumerate(blog_texts)
    ])

    prompt = f"""
    다음은 "{shop_name}"에 대한 블로그 리뷰들입니다.

    {combined_text}

    위 내용을 바탕으로 "{source_type}"에 해당하는 정보를 300-800자로 요약하세요.
    실제 블로그 내용만 사용하고, 추측하지 마세요.
    """

    summary = llm_summarize(prompt)

    return {
        "success": True,
        "text": summary,
        "sources": [b['url'] for b in blog_texts],
        "method": "naver_blog"
    }
```

### 장점
- ✅ **공식 API**: 네이버 개발자 센터 제공 (하루 25,000건 무료)
- ✅ **100% 커버**: 거의 모든 매장에 블로그 리뷰 존재
- ✅ **실제 외부 데이터**: 방문자의 실제 경험
- ✅ **출처 명시**: URL로 검증 가능
- ✅ **구현 용이**: 1주일 내 가능

### 단점
- ⚠️ **품질 편차**: 블로그마다 정보 품질 다름
- ⚠️ **광고 블로그**: 협찬 글 필터링 필요
- ⚠️ **키워드 의존**: 검색 키워드 튜닝 필요

### 예상 처리 시간
- 매장당: 20-25초 (블로그 검색 + 크롤링 + 요약)
- 10,000개: **약 70시간**

---

## 옵션 2: 하이브리드 (최고 품질)

### 개념
```
1순위: 공식 출처 (미쉐린, 블루리본, 공식 웹사이트)
2순위: 네이버 블로그
3순위: LLM 지식 (폴백)
```

### 아키텍처
```python
def collect_source_hybrid(shop_name: str, source_type: str) -> dict:
    """하이브리드 수집: 최고 품질 우선"""

    # 1순위: 공식 출처
    if source_type == "michelin_review":
        result = crawl_michelin_guide(shop_name)
        if result["success"]:
            return result

    elif source_type == "blueribbon_review":
        result = crawl_blueribbon(shop_name)
        if result["success"]:
            return result

    elif source_type in ["course_description", "brand_philosophy"]:
        result = crawl_official_website(shop_name)
        if result["success"]:
            return result

    # 2순위: 네이버 블로그
    result = collect_from_naver_blog(shop_name, source_type)
    if result["success"]:
        return result

    # 3순위: LLM 지식 (폴백)
    return collect_with_llm_knowledge(shop_name, source_type)
```

### 장점
- ✅ **최고 품질**: 공식 출처 우선
- ✅ **100% 커버**: 폴백으로 LLM 지식 사용
- ✅ **신뢰도 최상**: 검증 가능한 출처

### 단점
- ❌ **구현 복잡**: 여러 크롤러 개발 필요
- ❌ **유지보수 비용**: 각 사이트 구조 변경 시 수정
- ❌ **처리 시간**: 각 출처별 시도로 시간 증가

### 예상 처리 시간
- 매장당: 30-40초
- 10,000개: **약 100시간**

---

## 옵션 3: LLM 지식 유지 (현실적)

### 개념
```
현재 방식 유지 + 명칭 변경 + 검증 강화
```

### 변경 사항
1. **명칭 변경**
   - "RAG" → "LLM Knowledge Base"
   - "외부 소스" → "LLM 내부 지식"

2. **검증 강화**
   ```python
   def validate_llm_knowledge(shop_name: str, source_text: str) -> float:
       """LLM 지식의 신뢰도 점수 계산"""

       # 1. 여러 번 생성해서 일관성 확인
       texts = [generate_source(shop_name) for _ in range(3)]
       similarity = calculate_similarity(texts)

       # 2. 신뢰도 점수
       if similarity > 0.8:
           return 0.9  # 높은 일관성
       elif similarity > 0.6:
           return 0.7  # 중간 일관성
       else:
           return 0.5  # 낮은 일관성 (수동 검토 필요)
   ```

3. **메타데이터 추가**
   ```python
   metadata = {
       "source_method": "llm_knowledge",
       "confidence": 0.7,
       "verification_required": True,
       "generated_at": timestamp
   }
   ```

### 장점
- ✅ **추가 작업 없음**: 현재 코드 그대로
- ✅ **빠른 처리**: 41시간 (변화 없음)
- ✅ **저렴한 비용**: $200 (변화 없음)

### 단점
- ❌ **검증 불가**: 여전히 출처 불명
- ❌ **할루시네이션 위험**: 여전히 존재
- ❌ **최신성 부족**: 학습 데이터 기준

---

## 🎯 추천 전략

### 단계별 접근

#### Phase 1: 현재 LLM 지식으로 시작 (1개월)
```
- 10,000개 매장 Knowledge Base 구축
- "LLM Knowledge Base"로 명칭 변경
- 검증 강화 시스템 추가
- 실제 운영하며 한계 파악
```

#### Phase 2: 네이버 블로그 통합 (2개월)
```
- 네이버 블로그 크롤러 개발
- 500개 매장으로 파일럿 테스트
- LLM vs 블로그 품질 비교
- 점진적으로 전환
```

#### Phase 3: 하이브리드 완성 (3개월)
```
- 미쉐린, 블루리본 크롤러 추가
- 공식 웹사이트 크롤러 추가
- 품질별 우선순위 정립
```

---

## 💡 즉시 조치 사항

### 1. CLAUDE.md 업데이트
- 현재 방식이 "LLM Knowledge Base"임을 명시
- 진짜 RAG로 전환 계획 추가
- 한계와 개선 방향 문서화

### 2. 소스 메타데이터 추가
```python
metadata = {
    "collection_method": "llm_knowledge",  # 명확히 표시
    "verification_status": "pending",
    "confidence_score": 0.7,
    "requires_external_validation": True
}
```

### 3. 다음 단계 준비
- 네이버 개발자 센터 계정 생성
- 블로그 검색 API 신청
- 키워드 매핑 정의

---

## 질문 리스트 (내일 논의)

1. **우선순위**: 3가지 옵션 중 어떤 것을 선택?
2. **일정**: 언제까지 완료 목표?
3. **품질 vs 속도**: 빠른 구축 vs 높은 품질?
4. **리소스**: 개발 투입 가능 시간?
5. **예산**: API 비용 예산 존재 여부?

---

생성일: 2025-11-11
상태: 방향 정립 필요
다음 액션: 내일 논의 후 결정
