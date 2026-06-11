"""
============================================================================
AI 기반 ETF Robo Advisor  |  세종대학교 경영전문대학원 스마트자산관리 기말 과제
============================================================================
PHASE 1  투자자 입력 시스템  (행동재무학 설문 → 위험성향 점수화 → 재무계획)
PHASE 2  ETF 데이터 엔진     (yfinance 수집 → Feature 계산, 실패 시 오프라인 폴백)
PHASE 3  ETF 군집화          (K-Means Clustering → 데이터 기반 자산군 생성)
PHASE 4  포트폴리오 엔진      (유형별 비중 → Sharpe 기반 선택 → 최종 포트폴리오)
PHASE 5  백테스트 + 몬테카를로 (5년 백테스트 → SPY 비교 → 목표달성확률)
배포: GitHub → Streamlit Community Cloud → 라이브 URL 제출
============================================================================
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# yfinance는 환경에 따라 설치/네트워크가 막힐 수 있으므로 안전하게 import
try:
    import yfinance as yf
    YF_AVAILABLE = True
except Exception:
    YF_AVAILABLE = False

# ----------------------------------------------------------------------------
# 페이지 설정 & 면책 문구
# ----------------------------------------------------------------------------
st.set_page_config(page_title="AI ETF Robo Advisor", page_icon="📊", layout="wide")
st.title("📊 AI 기반 ETF Robo Advisor")
st.caption("세종대학교 경영전문대학원 · 정윤정(25200206)")
st.warning(
    "⚠️ **본 앱은 교육용 시뮬레이션입니다.** 실제 투자 권유·자문·매매 추천이 아니며, "
    "과거 성과는 미래 수익을 보장하지 않습니다."
)

# ETF Universe (투자 대상 종목군) — 가이드 4번 항목과 동일한 20개
ETF_UNIVERSE = ["SPY", "QQQ", "SCHD", "VIG", "SOXX", "IWM", "BND", "IEF",
                "TLT", "HYG", "GLD", "DBC", "VNQ", "XLP", "XLV", "BIL",
                "XLK", "VTV", "AGG", "SHY"]

RF = 0.02  # 무위험수익률(Risk-free Rate) 가정 2%

# 각 ETF 한 줄 설명 (UI 가독성용)
ETF_DESC = {
    "SPY": "S&P500 대형주", "QQQ": "나스닥100 성장주", "SCHD": "미국 배당성장주",
    "VIG": "배당성장주", "SOXX": "반도체", "IWM": "미국 소형주",
    "BND": "미국 종합채권", "IEF": "미국 중기국채", "TLT": "미국 장기국채",
    "HYG": "하이일드채권", "GLD": "금", "DBC": "원자재", "VNQ": "부동산리츠",
    "XLP": "필수소비재", "XLV": "헬스케어", "BIL": "초단기국채",
    "XLK": "기술섹터", "VTV": "미국 가치주", "AGG": "미국 종합채권", "SHY": "단기국채",
}


# ============================================================================
# PHASE 2 — ETF 데이터 엔진
# ============================================================================
@st.cache_data(ttl=3600, show_spinner="ETF 데이터를 수집하는 중입니다...")
def load_prices_online(tickers, period="5y"):
    """yfinance로 일별 수정종가 수집. 개별 실패 종목은 건너뛴다."""
    prices, failed = {}, []
    for t in tickers:
        try:
            df = yf.download(t, period=period, progress=False, auto_adjust=True)
            if df is not None and len(df) > 200:
                close = df["Close"]
                if isinstance(close, pd.DataFrame):
                    close = close.iloc[:, 0]
                prices[t] = close
            else:
                failed.append(t)
        except Exception:
            failed.append(t)
    if not prices:
        return pd.DataFrame(), failed
    price_df = pd.DataFrame(prices).dropna(how="all").ffill().dropna()
    return price_df, failed


@st.cache_data(ttl=3600)
def make_offline_prices(tickers, years=5, seed=42):
    """
    네트워크/yfinance 실패 시 사용하는 오프라인 폴백 데이터.
    각 ETF의 실제 성격(기대수익·변동성)을 반영한 기하 브라운 운동(GBM)으로
    5년치 일별 가격 경로를 합성한다. → 배포 후 빈 화면 사고 방지.
    """
    rng = np.random.default_rng(seed)
    n = int(years * 252)
    # (연 기대수익, 연 변동성) — 자산군 성격을 반영한 가정치
    profile = {
        "SPY": (0.10, 0.16), "QQQ": (0.14, 0.22), "SCHD": (0.09, 0.14),
        "VIG": (0.09, 0.13), "SOXX": (0.18, 0.32), "IWM": (0.08, 0.22),
        "BND": (0.02, 0.05), "IEF": (0.02, 0.06), "TLT": (0.02, 0.14),
        "HYG": (0.04, 0.09), "GLD": (0.06, 0.15), "DBC": (0.04, 0.18),
        "VNQ": (0.07, 0.20), "XLP": (0.07, 0.12), "XLV": (0.09, 0.14),
        "BIL": (0.02, 0.005), "XLK": (0.16, 0.24), "VTV": (0.08, 0.15),
        "AGG": (0.02, 0.05), "SHY": (0.015, 0.02),
    }
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n)
    # 공통 시장 충격(상관관계 생성용)
    market = rng.standard_normal(n)
    prices = {}
    for t in tickers:
        mu, sig = profile.get(t, (0.07, 0.15))
        beta = 0.2 + sig * 3  # 변동성 큰 자산일수록 시장과 더 동조
        idio = rng.standard_normal(n)
        shock = (beta * market + idio) / np.sqrt(beta ** 2 + 1)
        daily = (mu - 0.5 * sig ** 2) / 252 + (sig / np.sqrt(252)) * shock
        path = 100 * np.exp(np.cumsum(daily))
        prices[t] = pd.Series(path, index=dates)
    return pd.DataFrame(prices)


def compute_features(price_df):
    """ETF별 1행(Row) Feature 데이터셋 계산 (가이드 5번 항목)."""
    feats = []
    spy = price_df["SPY"].pct_change().dropna() if "SPY" in price_df else None
    gld = price_df["GLD"].pct_change().dropna() if "GLD" in price_df else None
    rets_all = price_df.pct_change().dropna()

    for t in price_df.columns:
        p = price_df[t].dropna()
        r = p.pct_change().dropna()
        years = len(p) / 252
        cagr = (p.iloc[-1] / p.iloc[0]) ** (1 / years) - 1
        vol = r.std() * np.sqrt(252)
        sharpe = (cagr - RF) / vol if vol > 0 else 0
        cum = (1 + r).cumprod()
        mdd = ((cum - cum.cummax()) / cum.cummax()).min()
        ret_1y = p.iloc[-1] / p.iloc[-252] - 1 if len(p) > 252 else cagr
        ret_3y = p.iloc[-1] / p.iloc[-756] - 1 if len(p) > 756 else cagr
        ma200 = p.rolling(200).mean().iloc[-1]
        gap200 = (p.iloc[-1] - ma200) / ma200 if ma200 > 0 else 0
        corr_spy = r.corr(spy) if spy is not None else 0
        corr_gld = r.corr(gld) if gld is not None else 0
        corr_avg = rets_all.corr()[t].drop(t).mean()
        feats.append({
            "ETF": t, "설명": ETF_DESC.get(t, ""),
            "CAGR": cagr, "Volatility": vol, "Sharpe": sharpe, "MDD": mdd,
            "Ret_1Y": ret_1y, "Ret_3Y": ret_3y, "Gap_MA200": gap200,
            "Corr_SPY": corr_spy, "Corr_GLD": corr_gld, "Corr_Avg": corr_avg,
        })
    return pd.DataFrame(feats).set_index("ETF")


def filter_universe(feat_df):
    """가이드 15p 필터링: 저효율(Sharpe<0) & 과도낙폭(MDD<-60%) 제거."""
    keep = feat_df[(feat_df["Sharpe"] > 0) & (feat_df["MDD"] > -0.60)]
    return keep if len(keep) >= 6 else feat_df  # 너무 적게 남으면 원본 유지


# ============================================================================
# PHASE 3 — K-Means 군집화
# ============================================================================
def cluster_etfs(feat_df, k=3, seed=42):
    """위험-수익 특성 기반 데이터 군집화 → 데이터 기반 자산군 생성."""
    cols = ["CAGR", "Volatility", "Sharpe", "MDD", "Corr_Avg"]
    X = StandardScaler().fit_transform(feat_df[cols])
    km = KMeans(n_clusters=k, random_state=seed, n_init=10)
    labels = km.fit_predict(X)
    out = feat_df.copy()
    out["Cluster"] = labels
    # 군집 평균 변동성 순으로 방어/성장 라벨 부여
    order = out.groupby("Cluster")["Volatility"].mean().sort_values().index
    names = {}
    label_pool = ["방어형(저변동)", "성장형(중변동)", "고성장형(고변동)"]
    for i, c in enumerate(order):
        names[c] = label_pool[i] if i < len(label_pool) else f"군집{c}"
    out["군집명"] = out["Cluster"].map(names)
    return out


# ============================================================================
# PHASE 1 — 투자성향 설문 (행동재무학 10문항)
# ============================================================================
def risk_survey():
    """가이드 6~13p 점수표를 그대로 반영한 10문항 설문."""
    st.subheader("PHASE 1 · 투자성향 설문")
    st.caption("행동재무학(Behavioral Finance) 기반 10문항으로 위험성향 점수를 산출합니다.")
    sc = 0
    c1, c2 = st.columns(2)

    with c1:
        age = st.radio("1. 나이", ["35세 미만", "35~49세", "50~64세", "65세 이상"])
        sc += {"35세 미만": 15, "35~49세": 10, "50~64세": 5, "65세 이상": 2}[age]

        horizon = st.radio("2. 투자기간", ["1~2년", "3~4년", "5~9년", "10년 이상"])
        sc += {"1~2년": 3, "3~4년": 8, "5~9년": 15, "10년 이상": 20}[horizon]

        loss = st.radio("3. 감내 가능한 최대 손실", ["5% 이하", "10%", "20%", "30% 이상"])
        sc += {"5% 이하": 2, "10%": 8, "20%": 15, "30% 이상": 22}[loss]

        exp = st.radio("4. 투자 경험", ["거의 없음", "보통", "많음"])
        sc += {"거의 없음": 3, "보통": 8, "많음": 13}[exp]

        crash = st.radio("5. 시장 급락 시 행동", ["즉시 매도", "일부 매도", "그대로 보유", "추가 매수"])
        sc += {"즉시 매도": 0, "일부 매도": 5, "그대로 보유": 12, "추가 매수": 18}[crash]

    with c2:
        fomo = st.radio("6. FOMO(추격매수) 성향", ["거의 없음", "보통", "강함"])
        sc += {"거의 없음": 3, "보통": 7, "강함": 10}[fomo]

        check = st.radio("7. 투자앱 확인 빈도", ["하루 여러 번", "하루 1회", "주 1~2회", "거의 안 봄"])
        sc += {"하루 여러 번": 2, "하루 1회": 5, "주 1~2회": 8, "거의 안 봄": 10}[check]

        goal = st.radio("8. 투자 목적", ["원금 보존", "안정적 자산증식", "적극적 수익추구", "단기 고수익"])
        sc += {"원금 보존": 2, "안정적 자산증식": 7, "적극적 수익추구": 12, "단기 고수익": 15}[goal]

        stress = st.radio("9. 시장 하락 시 스트레스", ["매우 큼", "큼", "보통", "거의 없음"])
        sc += {"매우 큼": 2, "큼": 5, "보통": 8, "거의 없음": 12}[stress]

        aversion = st.radio("10. 손실회피 성향", ["손실이 매우 두렵다", "다소 두렵다", "수익기회가 더 중요"])
        sc += {"손실이 매우 두렵다": 2, "다소 두렵다": 6, "수익기회가 더 중요": 13}[aversion]

    return sc


def classify(score):
    """가이드 13p 유형 분류표."""
    if score <= 30:
        return "안정형", "원금 보존이 최우선. 변동성을 최소화합니다."
    elif score <= 50:
        return "안정추구형", "안정성을 우선하되 약간의 수익을 추구합니다."
    elif score <= 70:
        return "균형형", "안정과 성장의 균형을 추구합니다."
    elif score <= 85:
        return "적극형", "성장 비중을 확대해 적극적으로 수익을 추구합니다."
    else:
        return "공격형", "고성장 자산 중심으로 최대 수익을 추구합니다."


# ============================================================================
# PHASE 4 — 포트폴리오 엔진
# ============================================================================
# 유형별 군집 목표비중 (방어형 / 성장형 / 고성장형)
TYPE_WEIGHTS = {
    "안정형":     {"방어형(저변동)": 0.75, "성장형(중변동)": 0.20, "고성장형(고변동)": 0.05},
    "안정추구형": {"방어형(저변동)": 0.60, "성장형(중변동)": 0.30, "고성장형(고변동)": 0.10},
    "균형형":     {"방어형(저변동)": 0.40, "성장형(중변동)": 0.40, "고성장형(고변동)": 0.20},
    "적극형":     {"방어형(저변동)": 0.20, "성장형(중변동)": 0.45, "고성장형(고변동)": 0.35},
    "공격형":     {"방어형(저변동)": 0.10, "성장형(중변동)": 0.40, "고성장형(고변동)": 0.50},
}


def build_portfolio(clustered, inv_type, top_n=2):
    """군집 목표비중 × Sharpe 기반 ETF 선택 → 최종 포트폴리오 비중."""
    target = TYPE_WEIGHTS[inv_type]
    weights = {}
    for cname, cweight in target.items():
        members = clustered[clustered["군집명"] == cname]
        if members.empty:
            continue
        picks = members.sort_values("Sharpe", ascending=False).head(top_n)
        # 군집 내에서는 Sharpe 비례 배분
        s = picks["Sharpe"].clip(lower=0.01)
        sub = (s / s.sum()) * cweight
        for etf, w in sub.items():
            weights[etf] = weights.get(etf, 0) + w
    total = sum(weights.values())
    if total > 0:
        weights = {k: v / total for k, v in weights.items()}
    return weights


# ============================================================================
# PHASE 5 — 백테스트 + 몬테카를로
# ============================================================================
def backtest(price_df, weights):
    """포트폴리오 5년 백테스트 → 누적수익·지표 계산."""
    rets = price_df.pct_change().dropna()
    cols = [c for c in weights if c in rets.columns]
    w = np.array([weights[c] for c in cols])
    port_ret = rets[cols] @ w
    cum = (1 + port_ret).cumprod()
    years = len(port_ret) / 252
    cagr = cum.iloc[-1] ** (1 / years) - 1
    vol = port_ret.std() * np.sqrt(252)
    sharpe = (cagr - RF) / vol if vol > 0 else 0
    mdd = ((cum - cum.cummax()) / cum.cummax()).min()
    return {"cum": cum, "port_ret": port_ret, "CAGR": cagr,
            "Vol": vol, "Sharpe": sharpe, "MDD": mdd}


def monte_carlo(cagr, vol, init, monthly, years, goal, n=3000, seed=42):
    """몬테카를로 시뮬레이션(Monte Carlo Simulation)으로 목표달성확률 계산."""
    rng = np.random.default_rng(seed)
    months = int(years * 12)
    mu_m = (1 + cagr) ** (1 / 12) - 1
    sig_m = vol / np.sqrt(12)
    finals = np.empty(n)
    paths = np.empty((n, months + 1))
    for i in range(n):
        bal = init
        paths[i, 0] = bal
        for m in range(months):
            bal = bal * (1 + rng.normal(mu_m, sig_m)) + monthly
            paths[i, m + 1] = bal
        finals[i] = bal
    prob = (finals >= goal).mean()
    return prob, finals, paths


# ============================================================================
# 메인 UI
# ============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["① 투자성향 설문", "② ETF 분석·군집화", "③ 포트폴리오 추천",
     "④ 백테스트", "⑤ 목표달성확률"]
)

# --- 데이터 로드 (온라인 우선, 실패 시 오프라인 폴백) ---
data_source = "오프라인 합성 데이터(폴백)"
if YF_AVAILABLE:
    price_df, failed = load_prices_online(ETF_UNIVERSE)
    if not price_df.empty and len(price_df.columns) >= 8:
        data_source = "yfinance 실시간 데이터"
    else:
        price_df = make_offline_prices(ETF_UNIVERSE)
else:
    price_df = make_offline_prices(ETF_UNIVERSE)

feat_df = compute_features(price_df)
feat_df = filter_universe(feat_df)
clustered = cluster_etfs(feat_df, k=3)

# --- TAB 1: 설문 ---
with tab1:
    score = risk_survey()
    inv_type, desc = classify(score)
    st.session_state["score"] = score
    st.session_state["inv_type"] = inv_type
    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("위험성향 점수", f"{score} / 130")
    m2.metric("투자자 유형", inv_type)
    st.info(f"**{inv_type}** — {desc}")

# --- TAB 2: ETF 분석·군집화 ---
with tab2:
    st.subheader("PHASE 2~3 · ETF 분석 및 K-Means 군집화")
    st.caption(f"데이터 출처: {data_source}")
    show = clustered.copy()
    for c in ["CAGR", "Volatility", "MDD", "Ret_1Y", "Ret_3Y"]:
        show[c] = (show[c] * 100).round(1).astype(str) + "%"
    show["Sharpe"] = show["Sharpe"].round(2)
    st.dataframe(
        show[["설명", "군집명", "CAGR", "Volatility", "Sharpe", "MDD"]],
        use_container_width=True
    )
    fig = px.scatter(
        clustered.reset_index(), x="Volatility", y="CAGR",
        color="군집명", text="ETF", size=clustered["Sharpe"].clip(lower=0.1).values,
        labels={"Volatility": "변동성(연율)", "CAGR": "연평균수익률"},
        title="위험-수익 평면 위의 ETF 군집"
    )
    fig.update_traces(textposition="top center")
    st.plotly_chart(fig, use_container_width=True)

# --- TAB 3: 포트폴리오 추천 ---
with tab3:
    st.subheader("PHASE 4 · 맞춤형 포트폴리오 추천")
    inv_type = st.session_state.get("inv_type", "균형형")
    st.info(f"현재 투자자 유형: **{inv_type}** (① 탭에서 설문을 완료하면 자동 반영)")
    weights = build_portfolio(clustered, inv_type)
    st.session_state["weights"] = weights
    if weights:
        wdf = pd.DataFrame({
            "ETF": list(weights.keys()),
            "설명": [ETF_DESC.get(k, "") for k in weights],
            "비중(%)": [round(v * 100, 1) for v in weights.values()],
        }).sort_values("비중(%)", ascending=False)
        cc1, cc2 = st.columns([1, 1])
        with cc1:
            st.dataframe(wdf, use_container_width=True, hide_index=True)
        with cc2:
            pie = go.Figure(go.Pie(labels=wdf["ETF"], values=wdf["비중(%)"], hole=0.4))
            pie.update_layout(title="포트폴리오 자산배분", height=350)
            st.plotly_chart(pie, use_container_width=True)
    else:
        st.error("포트폴리오를 생성할 수 없습니다. 데이터를 확인하세요.")

# --- TAB 4: 백테스트 ---
with tab4:
    st.subheader("PHASE 5-1 · 5년 백테스트 (vs SPY)")
    weights = st.session_state.get("weights", {})
    if weights:
        bt = backtest(price_df, weights)
        spy_cum = (1 + price_df["SPY"].pct_change().dropna()).cumprod()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("연평균수익률(CAGR)", f"{bt['CAGR']*100:.1f}%")
        c2.metric("변동성", f"{bt['Vol']*100:.1f}%")
        c3.metric("샤프지수(Sharpe)", f"{bt['Sharpe']:.2f}")
        c4.metric("최대낙폭(MDD)", f"{bt['MDD']*100:.1f}%")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=bt["cum"].index, y=bt["cum"].values,
                                 name="내 포트폴리오", line=dict(width=3)))
        fig.add_trace(go.Scatter(x=spy_cum.index, y=spy_cum.values,
                                 name="SPY(시장)", line=dict(dash="dash")))
        fig.update_layout(title="누적수익률 비교", yaxis_title="누적배수", height=400)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("③ 탭에서 포트폴리오를 먼저 생성하세요.")

# --- TAB 5: 목표달성확률 ---
with tab5:
    st.subheader("PHASE 5-2 · 몬테카를로 목표달성확률")
    weights = st.session_state.get("weights", {})
    if weights:
        bt = backtest(price_df, weights)
        c1, c2, c3, c4 = st.columns(4)
        init = c1.number_input("초기 투자금(만원)", value=1000, step=100) * 10000
        monthly = c2.number_input("월 적립금(만원)", value=50, step=10) * 10000
        years = c3.number_input("투자기간(년)", value=10, step=1)
        goal = c4.number_input("목표금액(만원)", value=15000, step=1000) * 10000
        if st.button("목표달성확률 계산", type="primary"):
            prob, finals, paths = monte_carlo(
                bt["CAGR"], bt["Vol"], init, monthly, years, goal)
            st.metric("🎯 목표달성확률", f"{prob*100:.1f}%")
            pct = np.percentile(paths, [10, 50, 90], axis=0)
            xm = np.arange(paths.shape[1])
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=xm, y=pct[2]/10000, name="상위10%", line=dict(dash="dot")))
            fig.add_trace(go.Scatter(x=xm, y=pct[1]/10000, name="중앙값(50%)", line=dict(width=3)))
            fig.add_trace(go.Scatter(x=xm, y=pct[0]/10000, name="하위10%", line=dict(dash="dot")))
            fig.add_hline(y=goal/10000, line_color="red",
                          annotation_text="목표금액", annotation_position="top left")
            fig.update_layout(title="자산 성장 시뮬레이션(만원)",
                              xaxis_title="개월", yaxis_title="자산(만원)", height=420)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("③ 탭에서 포트폴리오를 먼저 생성하세요.")

st.divider()
st.caption("© 2026 정윤정 · 세종대학교 경영전문대학원 · 교육용 프로토타입")
