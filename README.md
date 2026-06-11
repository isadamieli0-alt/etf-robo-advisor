# AI 기반 ETF Robo Advisor

세종대학교 경영전문대학원 · 스마트자산관리 기말 과제 · 정윤정(25200206)

행동재무학 설문으로 투자성향을 진단하고, ETF 과거 데이터를 머신러닝으로
군집화하여 투자자 유형별 맞춤 포트폴리오를 추천하는 Streamlit 웹앱입니다.

## 주요 기능 (PHASE 1~5)
1. **투자성향 설문** — 행동재무학 기반 10문항 → 위험성향 점수 → 5단계 유형 분류
2. **ETF 데이터 엔진** — yfinance 수집 + Feature 계산 (실패 시 오프라인 폴백 내장)
3. **K-Means 군집화** — 위험-수익 특성으로 데이터 기반 자산군 생성
4. **포트폴리오 엔진** — 유형별 비중 × Sharpe 기반 종목 선택
5. **백테스트 + 몬테카를로** — 5년 성과 검증 + 목표달성확률 계산

## 로컬 실행
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 배포
GitHub → Streamlit Community Cloud (DEPLOYMENT.md 참고)
