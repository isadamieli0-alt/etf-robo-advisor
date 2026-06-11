# 🚀 배포 가이드 — 제출용 라이브 URL 만들기 (10분)

> 목표: 이 앱을 인터넷에 올려서 `https://...streamlit.app` 형태의 URL을 발급받고,
> 그 URL을 과제 설문지(https://forms.gle/YAaGNyvV5WDnXUfw8)에 제출합니다.

준비물: ① 구글 계정(GitHub 가입용) ② 약 10분. **비용 0원, 카드 등록 불필요.**

---

## STEP 1 — GitHub에 코드 올리기 (약 5분)

1. https://github.com 접속 → 우측 상단 **Sign up**으로 무료 가입 (이미 있으면 로그인)
2. 로그인 후 우측 상단 **+** → **New repository** 클릭
3. 설정:
   - **Repository name**: `etf-robo-advisor` (원하는 이름)
   - **Public** 선택 (⚠️ 반드시 Public — Private이면 무료 배포 불가)
   - 나머지는 건드리지 않고 **Create repository** 클릭
4. 생성된 저장소 화면에서 **uploading an existing file** 링크 클릭
5. 아래 **5개 파일을 끌어다 놓기**(드래그&드롭):
   - `app.py`
   - `requirements.txt`
   - `README.md`
   - `.gitignore`
   - `DEPLOYMENT.md`
6. 하단 **Commit changes** 클릭 → 업로드 완료

> 💡 `.gitignore`가 안 보이면, 점(.)으로 시작하는 파일이라 숨겨진 것입니다.
> 파일 선택창에서 직접 모두 선택해 올리면 됩니다. (없어도 배포에는 지장 없음)

---

## STEP 2 — Streamlit Community Cloud로 배포 (약 5분)

1. https://share.streamlit.io 접속
2. **Continue with GitHub** 클릭 → STEP 1에서 만든 GitHub 계정으로 로그인·권한 승인
3. **Create app** (또는 **New app**) 클릭 → **Deploy a public app from GitHub** 선택
4. 입력란 설정:
   - **Repository**: `(내 아이디)/etf-robo-advisor` 선택
   - **Branch**: `main`
   - **Main file path**: `app.py`
5. **Deploy!** 클릭
6. 2~4분간 자동 설치·빌드 진행 (화면에 로그가 흐름). 완료되면 앱이 자동으로 뜹니다.

---

## STEP 3 — URL 복사 & 제출

1. 배포 완료된 앱 화면의 **주소창 URL**을 복사
   (예: `https://etf-robo-advisor-xxxx.streamlit.app`)
2. 우측 상단 메뉴에서 **Settings → Sharing**이 **Public**인지 확인
   (교수님이 로그인 없이 접속 가능해야 함)
3. 시크릿 창(다른 브라우저)에서 그 URL이 잘 열리는지 직접 확인 ✅
4. 과제 제출 설문지에 URL 입력 → 제출 완료!
   👉 https://forms.gle/YAaGNyvV5WDnXUfw8

---

## ❓ 자주 막히는 곳

| 증상 | 원인 | 해결 |
|------|------|------|
| 첫 화면에 ETF 데이터가 안 뜸 | yfinance 첫 수집 지연 | **새로고침(F5)** 1~2회. 안 되면 내장 오프라인 데이터로 자동 전환됨 |
| 빌드 실패 (Error installing) | requirements 버전 충돌 | `requirements.txt`의 버전 번호(`==1.39.0` 등)를 모두 지우고 패키지 이름만 남긴 뒤 재배포 |
| "This app is private" | 저장소가 Private | GitHub 저장소 Settings → Danger Zone → Change visibility → Public |
| 화면이 너무 느림 | 무료 플랜 첫 구동(콜드스타트) | 정상입니다. 한 번 켜지면 빨라집니다 |

---

## ⚠️ 제출 직전 체크리스트

- [ ] 시크릿 창에서 URL이 로그인 없이 열린다
- [ ] 5개 탭(①설문 ②분석 ③포트폴리오 ④백테스트 ⑤목표달성확률)이 모두 작동한다
- [ ] ① 탭에서 설문 → 유형 분류가 나온다
- [ ] ③ 탭에서 포트폴리오 파이차트가 그려진다
- [ ] 설문지(forms.gle)에 URL을 제출했다
