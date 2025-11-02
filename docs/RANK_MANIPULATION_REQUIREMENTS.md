# 순위 조작 요구사항 문서

작성일: 2025-11-02
버전: 2.0

---

## 📋 목표

쿠팡 검색 결과 페이지에서 **특정 상품의 순위를 변경**하되, **광고 및 특수 섹션(베스트셀러, 한정특가)의 위치는 원래 위치에 고정**되어야 한다.

---

## 🎯 핵심 요구사항

### 1. 순위 조작 대상

#### ✅ 조작 대상 (재정렬 가능)
- **일반 상품**: 광고가 아닌 자연 검색 결과
- 순위는 1등, 2등, 3등... 으로 표시됨 (워터마크 존재)

#### 🚫 조작 불가 (원래 위치 고정)
- **광고 상품**: `data-ad-id` 속성 또는 특정 class 포함
- **베스트셀러 섹션**: `class*="best-seller"` 포함
- **한정특가 섹션**: `class*="limited-time-offer"` 포함
- **기타 특수 섹션**: 프로모션, 추천 등

### 2. 재정렬 규칙

```
예시: 15등 상품을 3등으로 이동

[변경 전]
광고, 1등, 2등, 3등, 광고, 4등, ..., 베스트셀러, ..., 15등

[변경 후]
광고, 1등, 2등, (15등), 광고, 3등, ..., 베스트셀러, ..., 14등
     ↑                          ↑                ↑
   원위치                      원위치            원위치
```

**규칙:**
- 광고: 원래 DOM index 유지
- 베스트셀러: 원래 DOM index 유지
- 한정특가: 원래 DOM index 유지
- 일반 상품: 재정렬된 순서대로 빈 자리에 배치

---

## 🔍 현재 DOM 구조

### 기본 구조
```html
<ul id="product-list">
  <li data-id="12345" class="ProductUnit_productUnit__xxx">광고</li>         <!-- DOM index: 0 -->
  <li data-id="67890" class="ProductUnit_productUnit__xxx">1등</li>          <!-- DOM index: 1 -->
  <li data-id="11111" class="ProductUnit_productUnit__xxx">2등</li>          <!-- DOM index: 2 -->
  <li data-id="22222" class="ProductUnit_productUnit__xxx">3등</li>          <!-- DOM index: 3 -->
  <li data-id="33333" class="ProductUnit_productUnit__xxx">광고</li>         <!-- DOM index: 4 -->
  <li data-id="44444" class="limited-time-offer">한정특가 섹션</li>          <!-- DOM index: 5 -->
  <li data-id="55555" class="ProductUnit_productUnit__xxx">4등</li>          <!-- DOM index: 6 -->
  ...
  <li data-id="99999" class="best-seller">베스트셀러 섹션</li>               <!-- DOM index: 20 -->
  ...
</ul>
```

### 특수 섹션 감지 방법

#### 방법 1: data-ad-id 속성 (광고)
```python
is_ad = element.get_attribute('data-ad-id') is not None
```

#### 방법 2: class 기반 (특수 섹션)
```python
element_class = element.get_attribute('class') or ''
is_special = any(keyword in element_class.lower() for keyword in [
    'best-seller',
    'limited-time-offer',
    'time-deal',
    'special-offer'
])
```

#### 방법 3: 링크 여부
```python
# 특수 섹션은 상품 링크가 없을 수 있음
links = element.find_elements(By.CSS_SELECTOR, "a[href*='/vp/products/']")
has_product_link = len(links) > 0
```

---

## ❌ 현재 알고리즘의 문제점

### 알고리즘 1: 순차 재배치 (기존)
```python
for idx, item_info in enumerate(items_info):
    if item_info.get('is_ad'):
        container.appendChild(ad_element)
    else:
        container.appendChild(organic_element)
```

**문제:**
- appendChild는 항상 마지막에 추가
- 광고가 DOM index 0이면 광고를 먼저 추가 → 맨 앞에 고정
- 결과: 광고/특수 섹션이 의도한 위치가 아닌 곳에 배치됨

### 알고리즘 2: 일반 상품 먼저 + insertBefore (현재)
```python
# 1단계: 일반 상품 먼저 추가
for product in reordered_products:
    container.appendChild(product)

# 2단계: 광고를 원래 위치에 삽입
for ad in ads:
    container.insertBefore(ad, current_children[ad_dom_idx])
```

**문제:**
- insertBefore 시점에 current_children가 이미 변경됨
- DOM index 계산이 복잡하고 불안정
- 다수의 광고/특수 섹션이 있을 때 위치 계산 오류 가능성

---

## ✅ 기대하는 동작

### 입력
```python
items_info = [
    {"dom_index": 0, "is_ad": True, "type": "광고"},
    {"dom_index": 1, "is_ad": False, "rank": 1},
    {"dom_index": 2, "is_ad": False, "rank": 2},
    {"dom_index": 3, "is_ad": False, "rank": 3},
    {"dom_index": 4, "is_ad": True, "type": "광고"},
    {"dom_index": 5, "is_ad": True, "type": "특수섹션(limited-time-offer)"},
    {"dom_index": 6, "is_ad": False, "rank": 4},
    ...
    {"dom_index": 20, "is_ad": True, "type": "특수섹션(best-seller)"},
    ...
]

source_rank = 15  # 15등 상품
target_rank = 3   # 3등으로 이동
```

### 출력 (DOM 순서)
```
[0] 광고 (원본 DOM 0)
[1] 일반 1등
[2] 일반 2등
[3] 일반 15등  ← 이동된 상품
[4] 광고 (원본 DOM 4)
[5] 특수섹션 - 한정특가 (원본 DOM 5)
[6] 일반 3등
[7] 일반 4등
...
[20] 특수섹션 - 베스트셀러 (원본 DOM 20)
...
[32] 일반 14등
[33] 일반 16등
...
```

**핵심:**
- 광고/특수 섹션은 정확히 원래 DOM index에 위치
- 일반 상품은 재정렬된 순서대로 빈 자리에 배치
- 워터마크는 재정렬 후 1~10등에 다시 생성

---

## 🔧 고려사항

### 1. DOM 조작 제약사항
- **Stale Element Reference**: DOM 변경 후 기존 WebElement는 무효화됨
- **appendChild vs insertBefore**: appendChild는 항상 끝에 추가, insertBefore만 중간 삽입 가능
- **cloneNode**: 요소를 복제하면 이벤트 핸들러/데이터 손실 가능성

### 2. 성능 고려
- 36개 항목 기준: 27개 일반 상품 + 9개 광고/특수 섹션
- DOM 조작은 한 번에 처리 (리플로우 최소화)
- JavaScript execute_script 사용으로 성능 향상

### 3. 워터마크 관리
- 순위 변경 후 1~10등의 워터마크는 완전히 제거 후 재생성
- 워터마크 class: `RankMark_rank1__xxx`, `RankMark_rank2__xxx`, ...
- 기존 워터마크 스타일을 백업하여 동일하게 재생성

---

## 💡 새로운 알고리즘 아이디어

### 방안 1: 빈 슬롯 계산 방식
```
1. 전체 DOM index 배열 생성: [0, 1, 2, ..., 35]
2. 광고/특수 섹션의 DOM index를 제거: [1, 2, 3, 6, 7, ...]
3. 남은 슬롯에 재정렬된 일반 상품을 순서대로 매핑
4. 최종 배열을 한 번에 DOM에 적용
```

**장점:**
- 위치 계산이 명확하고 안정적
- insertBefore/appendChild 혼용 없음

**단점:**
- 구현 복잡도 증가

### 방안 2: 템플릿 배열 사용
```
1. 빈 배열 생성: [None] * 36
2. 광고/특수 섹션을 원래 위치에 배치: arr[0] = ad1, arr[4] = ad2, ...
3. None 슬롯에 재정렬된 일반 상품 순서대로 채움
4. 배열 순서대로 DOM에 appendChild
```

**장점:**
- 직관적이고 구현 간단
- 위치 오류 가능성 낮음

**단점:**
- 메모리 사용량 약간 증가

### 방안 3: Virtual DOM 재구성
```
1. 전체 DOM을 JSON으로 직렬화
2. 메모리에서 순서 재정렬
3. innerHTML로 한 번에 교체
```

**장점:**
- 가장 빠른 성능

**단점:**
- 이벤트 핸들러 손실 위험
- 쿠팡 페이지의 JavaScript 동작 파괴 가능성

---

## 📊 테스트 케이스

### 케이스 1: 광고가 첫 번째 (DOM index 0)
```
[변경 전] 광고(0), 1등(1), 2등(2), 3등(3), ...
[변경 후] 광고(0), 15등(1), 1등(2), 2등(3), ...
```
**검증:** 광고가 여전히 첫 번째인지 확인

### 케이스 2: 특수 섹션이 중간 (DOM index 5)
```
[변경 전] 1등(0), 2등(1), 3등(2), 광고(3), 광고(4), 한정특가(5), 4등(6), ...
[변경 후] 1등(0), 2등(1), 15등(2), 광고(3), 광고(4), 한정특가(5), 3등(6), ...
```
**검증:** 한정특가 섹션이 여전히 5번째인지 확인

### 케이스 3: 다수의 광고 (9개)
```
현재 실제 케이스: 광고 9개 (DOM index: 0, 4, 5, 19, 20, 22, 33, 34, 35)
```
**검증:** 모든 광고가 원래 위치에 있는지 확인

---

## 🚀 다음 단계

1. **새로운 알고리즘 설계**
   - 위 3가지 방안 중 선택
   - 구현 전 pseudo-code 작성

2. **프로토타입 구현**
   - 별도 브랜치에서 개발
   - 기존 코드와 분리

3. **테스트**
   - 3가지 케이스 모두 통과
   - 다양한 페이지 구조에서 검증

4. **성능 측정**
   - DOM 조작 시간
   - 메모리 사용량

5. **안정성 검증**
   - 100회 반복 테스트
   - 다양한 상품 수 (20~50개)

---

## 📝 참고사항

### 현재 코드 위치
- `rank_manipulator.py`: `_rebuild_dom_with_fixed_ads()` (line 136~247)
- `rank_modifier.py`: `_reconstruct_dom()` (line 143~191)
- `product_finder.py`: `analyze_product_list_structure()` (line 45~130)

### 관련 이슈
- 베스트셀러/한정특가가 맨 위로 올라오는 문제 (해결 시도 중)
- Stale Element Reference 에러 (DOM 재구성 후 발생 가능)
- 워터마크 재생성 타이밍 문제

---

**마지막 업데이트:** 2025-11-02
**상태:** 새로운 알고리즘 설계 필요
