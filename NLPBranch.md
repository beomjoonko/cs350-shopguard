1. 현재 상태: Crawling = Main, URL = Supplementary
Crawling 데이터가 기본값으로 주어졌다고 가정하고 URL 값만 계산해서 넣음

2. 정상적인 URL도 Phising으로 분류 (쿠팡처럼 길쭉한 URL을 위험으로 분류)
  스모크 테스트 결과 (크롤러 stub 상태 = URL classifier 단독)

  ┌──────────────────────────────────────────────────────────┬─────────────┐
  │                           URL                            │    score    │
  ├──────────────────────────────────────────────────────────┼─────────────┤
  │ https://en.wikipedia.org/wiki/Phishing                   │ 6.90 ✅     │
  │                                                          │ (SAFE)      │
  ├──────────────────────────────────────────────────────────┼─────────────┤
  │ https://www.coupang.com/vp/products/123?vendorItemId=456 │ 91.69 ⚠️     │
  ├──────────────────────────────────────────────────────────┼─────────────┤
  │ http://bt-104804.weeblysite.com/                         │ 99.98 ✅    │
  │                                                          │ (CRITICAL)  │
  ├──────────────────────────────────────────────────────────┼─────────────┤
  │ http://192.210.150.19/eTzMQwJ134.bin                     │ 100.00 ✅   │
  │                                                          │ (CRITICAL)  │
  └──────────────────────────────────────────────────────────┴─────────────┘

  기존 pytest 3개 다 통과.

  주목할 점 (예상했던 도메인 미스매치)

  Coupang URL이   스모크 테스트 결과 (크롤러 stub 상태 = URL classifier 단독)

  ┌──────────────────────────────────────────────────────────┬─────────────┐
  │                           URL                            │    score    │
  ├──────────────────────────────────────────────────────────┼─────────────┤
  │ https://en.wikipedia.org/wiki/Phishing                   │ 6.90 ✅     │
  │                                                          │ (SAFE)      │
  ├──────────────────────────────────────────────────────────┼─────────────┤
  │ https://www.coupang.com/vp/products/123?vendorItemId=456 │ 91.69 ⚠️     │
  ├──────────────────────────────────────────────────────────┼─────────────┤
  │ http://bt-104804.weeblysite.com/                         │ 99.98 ✅    │
  │                                                          │ (CRITICAL)  │
  ├──────────────────────────────────────────────────────────┼─────────────┤
  │ http://192.210.150.19/eTzMQwJ134.bin                     │ 100.00 ✅   │
  │                                                          │ (CRITICAL)  │
  └──────────────────────────────────────────────────────────┴─────────────┘

  기존 pytest 3개 다 통과.

  주목할 점 (예상했던 도메인 미스매치)

  Coupang URL이 **91.69 (CRITICAL)**로 잡혔습니다 — 이게 이전 대화에서
  경고드렸던 그대로의 현상입니다:
  - 학습 데이터: URLHaus 악성 + Wikipedia/StackOverflow 정상 → 짧고 깔끔한
  URL이 정상
  - 실제 e-commerce URL: 길고 숫자 많고 query param 많음 → 모델이 phishing으로
   오판

  발표/시연 때 이걸 어떻게 다룰지 옵션:
  1. 솔직하게: "URL classifier는 일반 phishing 탐지용이고, e-commerce 도메인은
   content 분석에 의존" + 실제 크롤러 구현 시 0.3 weight로 보조 신호화
  2. 화이트리스트 추가: 메이저 e-commerce 도메인(coupang.com, aliexpress.com,
  temu.com)은 URL classifier bypass
  3. 재학습: e-commerce URL 데이터 추가해서 재학습 (시간 부담 큼)

  url_model_artifacts/_validate.py는 남겨뒀으니 feature 정의 바뀌면 다시
  돌려보실 수 있습니다. 로 잡혔습니다 — 이게 이전 대화에서
  경고드렸던 그대로의 현상입니다:
  - 학습 데이터: URLHaus 악성 + Wikipedia/StackOverflow 정상 → 짧고 깔끔한
  URL이 정상
  - 실제 e-commerce URL: 길고 숫자 많고 query param 많음 → 모델이 phishing으로
   오판

  발표/시연 때 이걸 어떻게 다룰지 옵션:
  1. 솔직하게: "URL classifier는 일반 phishing 탐지용이고, e-commerce 도메인은
   content 분석에 의존" + 실제 크롤러 구현 시 0.3 weight로 보조 신호화
  2. 화이트리스트 추가: 메이저 e-commerce 도메인(coupang.com, aliexpress.com,
  temu.com)은 URL classifier bypass
  3. 재학습: e-commerce URL 데이터 추가해서 재학습 (시간 부담 큼)

  url_model_artifacts/_validate.py는 남겨뒀으니 feature 정의 바뀌면 다시
  돌려보실 수 있습니다.

3. 데이터셋 RE-ENGINEERING 뒤지게 힘듬. 클로드도 힘들어함 
모든 FEATURE를 완전 주먹구구식으로 계산, www.example.com에서 example을 알아내기 위해 .으로 parsing하는 방법을 썼기 때문에 example.co.kr이면 co를 내놓음.
자세한 것은 ai-worker/worker/pipeline/url_classifier.py에서
