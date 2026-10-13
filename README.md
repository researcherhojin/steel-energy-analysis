# 제철소 전력 사용 분석 (2018)

철강 공장 한 곳의 1년치 15분 단위 전력 기록을 분석하여, **언제 전력을 많이 쓰는지·예측할 수 있는지·평소와 다른 날은 언제인지·어디서 줄일 수 있는지**를 정리한 프로젝트입니다.

**📄 [보고서 (PDF)](<outputs/v2/제철소 전력 분석 보고서.pdf>)** · **📊 [대시보드 (PDF)](<outputs/v2/제철소 전력 2018 대시보드.pdf>)** · **📓 [분석 노트북](notebooks/analysis.ipynb)**

> 데이터: UCI *Steel Industry Energy Consumption* (대우제철 광양 공장, 2018) · 라이선스: 코드 MIT, 데이터 CC BY 4.0

---

## 핵심 결과

### 1. 전력 사용은 평일 낮에 집중됩니다
- 평일 08–18시는 1년 시간의 30%이지만, 이때 1년 사용량의 **64%**(약 3분의 2)를 씁니다.
- 근거: 보고서 2장

### 2. 15분 뒤 사용량을 예측할 수 있습니다
- 15분 뒤 사용량을 평균 **3.94 kWh** 오차(오차율 16%)로 예측합니다.
- 직전 15분 값을 그대로 쓰는 것보다 오차가 24% 작습니다.
- 근거: 보고서 4장

### 3. '부하 구분' 열은 실제 부하가 아니라 요금 시간표입니다
- 원본의 `Load_Type`(Light=경부하, Medium=중간부하, Maximum=최대부하)은 **계절별 요금 시간표**입니다.
- 맞힌 정도는 평일·주말 구분과 시각·계절만으로 0.88, 과거 사용량까지 쓰면 0.96입니다.
- 근거: 보고서 3장, 부록 C

### 4. 평소와 다른 날은 대부분 달력 일정과 겹칩니다
- 평일 공휴일 15일 중 **7일**, 공휴일이 아닌 평일 **5일**이 휴무였고, 이상 판정은 **2일**입니다.
- 사유는 계량 데이터만으로 알 수 없으므로 운영 기록으로 확인해야 합니다.
- 근거: 보고서 5장

### 5. 무효전력량과 요금을 줄일 여지가 있습니다
- 역률을 0.95까지 보상하면 무효전력량이 **39%** 줄어듭니다.
- 최대부하 시간대 사용량 10%를 경부하 시간대로 옮기면 연 **481만 원**(가정 요금 기준)을 아낍니다.
- 근거: 보고서 6장

<details>
<summary><b>용어 설명</b></summary>

| 용어 | 뜻 |
|---|---|
| 오차율 | 15분 단위 예측 오차의 절댓값 합 ÷ 실제 사용량 합 (WAPE) |
| 맞힌 정도 | macro-F1. 경부하·중간부하·최대부하별 F1 점수의 평균 (1이 만점) |
| 역률 | 공급된 전력 중 실제 일을 한 전력의 비율 (1에 가까울수록 좋음) |
| 무효전력량 (kVarh) | 전동기·변압기가 자기장을 만드는 데 쓰는 전력량. 일은 하지 않지만 설비 용량을 차지함 |

</details>

## 해석상 유의사항

| 항목 | 내용 |
|---|---|
| 금액은 가정값 | 데이터에 요금 정보가 없어, 산업용 계시별 요금을 단순화한 예시 단가(`config.TARIFF_ASSUMPTIONS`)를 적용했습니다. 금액의 크기보다 방향을 참고하십시오. |
| 단일 공장, 1년치 | 생산량·공정·설비 정보가 없어 사용량 변화의 원인은 추정에 그칩니다. |
| 일부 분류 점수는 탐색적 | 11–12월 평가 결과를 본 뒤 모델을 수정했습니다. 위의 0.88과 0.96은 별도의 역방향 분할(3–12월 학습, 1–2월 평가)에서 낸 값입니다. |
| 이상 판정은 사후 점검용 | 판정 기준을 1년 전체 자료로 정했으므로 실시간 경보로는 쓸 수 없습니다. |

## 결과물

| 결과물 | 대상 독자 | 바로 보기 | 직접 생성 시 |
|---|---|---|---|
| 보고서 | 공장·에너지 관리자 | [PDF](<outputs/v2/제철소 전력 분석 보고서.pdf>) | `build/report.html` |
| 대시보드 | 수치를 직접 탐색하려는 사용자 | [PDF](<outputs/v2/제철소 전력 2018 대시보드.pdf>) | `build/dashboard.html` |
| 분석 노트북 | 분석 과정을 검토하려는 분석가 | [노트북](notebooks/analysis.ipynb) | `notebooks/analysis.ipynb` |

- 세 결과물의 수치는 모두 같은 분석 결과 파일(`outputs/analysis.json`)에서 나오므로 서로 일치합니다.
- PDF는 정적 사본입니다. 대시보드의 탭·필터는 HTML 버전에서 사용할 수 있습니다.
- HTML은 차트와 글꼴을 인터넷에서 불러오므로 열람 시 인터넷 연결이 필요합니다.

## 실행 방법

**준비물:** [uv](https://docs.astral.sh/uv/) 하나만 설치하면 됩니다. Python 3.12는 uv가 자동으로 내려받습니다.

| 운영체제 | uv 설치 명령 |
|---|---|
| macOS · Linux | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Windows (PowerShell) | `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 \| iex"` |

**1단계. 내려받기와 설치**

```bash
git clone https://github.com/researcherhojin/steel-energy-analysis.git
cd steel-energy-analysis
uv sync
```

**2단계. 테스트 (1–3분)**

```bash
uv run pytest
```

**3단계. 분석과 결과물 생성**

```bash
uv run python -m steelenergy.pipeline
uv run python web/build.py
uv run python notebooks/build_notebook.py
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb
```

차례로 분석(→ `outputs/analysis.json`), 보고서·대시보드 생성(→ `build/*.html`), 노트북 생성과 실행입니다. 명령은 모든 운영체제에서 같으며, 한 줄씩 차례로 실행하면 됩니다.

> **지원 환경:** Windows 10·11(x86 64비트, ARM64), macOS(Apple Silicon, Intel), Linux(x86_64, ARM64). 32비트 Windows는 지원하지 않습니다.
> 단계별 설명과 문제 해결은 [WORKFLOW.md](WORKFLOW.md)를, 설치 환경 세부 사항은 [WORKFLOW.md 2장](WORKFLOW.md#2-준비물)을 참고하십시오.

## 데이터

| 항목 | 내용 |
|---|---|
| 출처 | V E, S., Shin, C., & Cho, Y. (2021). *Steel Industry Energy Consumption* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C52G8C |
| 관련 논문 | Sathishkumar V E, Shin C., Cho Y. (2021). Efficient energy consumption prediction model for a data analytic-enabled industry building in a smart city. *Building Research & Information*, 49(1), 127–143. |
| 라이선스 | CC BY 4.0 |
| 파일 | `Steel_industry_data.csv`(35,040행), 원본 압축 파일 `steel+industry+energy+consumption.zip` (내용 동일) |

원본에는 다음 두 가지 특이점이 있으며, 분석 코드(`src/steelenergy/io.py`)가 자동으로 보정합니다.
- 날짜가 일/월/연 순서로 기록되어 있습니다.
- 매일 마지막 기록(24:00)이 같은 날짜의 00:00으로 찍혀 있습니다.

## 저장소 구조

```
src/steelenergy/   분석 코드 (모든 계산 함수)
notebooks/         분석 노트북과 노트북 생성기
web/               보고서·대시보드 템플릿과 빌드 스크립트
tests/             테스트
build/             생성된 보고서·대시보드 HTML (git 관리 대상 아님)
outputs/           analysis.json(실행 시 생성)과 보관용 PDF(v1/, v2/)
```

`outputs/v1/`, `outputs/v2/`의 PDF는 다시 만들 수 없는 보관본입니다. 상세 구조는 [WORKFLOW.md 9장](WORKFLOW.md#9-폴더-구조)에 있습니다.

## 관련 문서

| 문서 | 내용 |
|---|---|
| [WORKFLOW.md](WORKFLOW.md) | 재현 절차: 단계별 설명, 설정 변경, 검증, 문제 해결 |
| [CLAUDE.md](CLAUDE.md) | Claude Code용 작업 규칙(영어). 코드 구조와 분석 규칙 요약으로도 활용 가능 |

## 라이선스

- **코드와 문서:** [MIT License](LICENSE)
- **데이터**(`Steel_industry_data.csv`, `steel+industry+energy+consumption.zip`): 원 저작자의 CC BY 4.0을 따르며, 재사용 시 [데이터](#데이터) 절의 출처를 표기해야 합니다.
