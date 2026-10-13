# 제철소 전력 사용 분석 (2018)

UCI Machine Learning Repository의 *Steel Industry Energy Consumption* 데이터셋(대우제철 광양 공장, 2018년, 15분 단위 기록)을 분석한 프로젝트입니다. 분석 파이프라인, 분석 노트북, 대시보드, 보고서를 하나의 저장소에서 재현할 수 있도록 구성했습니다.

## 목차

1. [개요](#개요)
2. [결과물](#결과물)
3. [핵심 결과](#핵심-결과)
4. [해석상 유의사항](#해석상-유의사항)
5. [실행 방법](#실행-방법)
6. [데이터](#데이터)
7. [저장소 구조](#저장소-구조)
8. [관련 문서](#관련-문서)

## 개요

본 분석은 다음 네 가지 질문에 답하는 것을 목표로 합니다.

1. 전력 사용은 어느 시간대에 집중되는가?
2. 사용량을 사전에 예측할 수 있는가?
3. 평소와 다른 사용 양상을 보인 날은 언제인가?
4. 요금과 무효전력량을 줄일 여지는 어디에 있는가?

아울러 원본 데이터의 '부하 구분'(`Load_Type`) 열이 실제로 무엇을 나타내는지 검증하였습니다.

## 결과물

| 결과물 | 바로 보기 | 생성 위치 | 주요 독자 |
|---|---|---|---|
| 보고서 | [PDF](<outputs/v2/제철소 전력 분석 보고서.pdf>) | `build/report.html` | 결론과 근거를 확인하려는 공장·에너지 관리자 |
| 대시보드 | [PDF](<outputs/v2/제철소 전력 2018 대시보드.pdf>) | `build/dashboard.html` | 월·시간대별 수치를 직접 탐색하려는 사용자 |
| 분석 노트북 | [노트북](notebooks/analysis.ipynb) | `notebooks/analysis.ipynb` | 분석 과정과 판단 근거를 검토하려는 분석가 |

- 세 결과물의 수치는 모두 동일한 분석 결과 파일(`outputs/analysis.json`)에서 생성되므로 서로 일치합니다.
- PDF는 HTML 결과물을 저장한 정적 사본입니다. 대시보드의 탭 전환·필터 등 상호작용 기능은 HTML 버전에서만 사용할 수 있습니다. 이전 판은 `outputs/v1/`에 보관되어 있습니다.
- HTML 보고서와 대시보드는 [실행 방법](#실행-방법)에 따라 생성할 수 있습니다. 차트 라이브러리와 글꼴을 인터넷에서 불러오므로 열람 시 인터넷 연결이 필요합니다.

## 핵심 결과

| 질문 | 답 | 자세히 |
|---|---|---|
| 언제 몰아서 쓰나 | 평일 08–18시는 1년 시간의 30%이지만, 이때 1년 사용량의 **64%**(약 3분의 2)를 씁니다. | 보고서 2장 |
| 미리 알 수 있나 | 15분 뒤 사용량을 평균 **3.94 kWh** 오차(오차율 16%)로 예측합니다. 직전 15분 값을 그대로 쓰는 것보다 오차가 24% 작습니다. | 보고서 4장 |
| 부하 구분의 정체 | 원본의 `Load_Type`(Light=경부하, Medium=중간부하, Maximum=최대부하)은 실제 부하가 아니라 **계절별 요금 시간표**입니다. 맞힌 정도는 평일·주말 구분과 시각·계절만으로 0.88, 과거 사용량까지 쓰면 0.96입니다. | 보고서 3장, 부록 C |
| 평소와 다른 날 | 평일 공휴일 15일 중 **7일**, 공휴일이 아닌 평일 **5일**이 휴무였고, 이상 판정은 **2일**입니다. 날짜는 대부분 달력 일정과 맞지만, 사유는 운영 기록으로 확인해야 합니다. | 보고서 5장 |
| 줄일 여지 | 역률을 0.95까지 보상하면 무효전력량이 **39%** 줄어듭니다. 최대부하 시간대 사용량 10%를 경부하 시간대로 옮기면 연 **481만 원**(가정 요금 기준)을 아낍니다. | 보고서 6장 |

**용어 정의**
- **오차율:** 15분 단위 예측 오차의 절댓값 합을 실제 사용량 합으로 나눈 값(WAPE)입니다.
- **맞힌 정도:** macro-F1입니다. 경부하·중간부하·최대부하 각각의 F1 점수를 평균한 값이며, 1이 만점입니다.
- **역률:** 공급된 전력 중 실제 일을 한 전력의 비율입니다. 1에 가까울수록 바람직합니다.
- **무효전력량(kVarh):** 전동기·변압기가 자기장을 형성하는 데 쓰이는 전력량입니다. 실제 일은 하지 않으나 설비 용량을 점유합니다.

## 해석상 유의사항

- **금액은 가정값입니다.** 데이터에 요금 정보가 없어 국내 산업용 계시별 요금(시간대별 차등 단가)을 단순화한 예시 단가(`config.TARIFF_ASSUMPTIONS`)를 적용하였습니다. 금액의 절대 크기보다 방향을 참고하는 수치입니다.
- **단일 공장의 1년치 자료입니다.** 생산량·공정·설비 정보가 없으므로 사용량 변화의 원인은 추정의 범위에 머뭅니다.
- **부하 구분 분류 점수 일부는 탐색적 결과입니다.** 11–12월 평가 결과를 확인한 뒤 모델을 수정하였기 때문입니다. 위 표의 0.88과 0.96은 시간 방향을 뒤집은 별도 분할(3–12월 학습, 1–2월 평가)에서 산출한 값입니다.
- **이상 판정은 사후 점검용입니다.** 판정 척도를 1년 전체 자료로 정하였으므로 실시간 경보로는 사용할 수 없습니다.

## 실행 방법

### 지원 환경

Windows 10·11(64비트 x86, ARM64), macOS(Apple Silicon, Intel), Linux(x86_64, ARM64)를 지원합니다. 32비트 Windows는 핵심 분석 패키지가 지원하지 않아 실행할 수 없습니다. 세부 사항은 [WORKFLOW.md 2장](WORKFLOW.md#2-준비물)을 참고하십시오.

### 준비

[uv](https://docs.astral.sh/uv/)만 설치하면 됩니다. Python 3.12는 uv가 운영체제와 CPU에 맞추어 자동으로 내려받습니다.
- **macOS·Linux:** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows PowerShell:** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

### 실행

아래 명령을 한 줄씩 차례로 실행합니다. 명령은 모든 운영체제에서 동일합니다.

```bash
git clone https://github.com/researcherhojin/steel-energy-analysis.git
cd steel-energy-analysis
uv sync
uv run pytest
uv run python -m steelenergy.pipeline
uv run python web/build.py
uv run python notebooks/build_notebook.py
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb
```

각 명령은 순서대로 저장소 내려받기, 폴더 이동, 패키지 설치, 테스트(1–3분), 분석(→ `outputs/analysis.json`), 보고서·대시보드 생성(→ `build/*.html`), 노트북 생성 및 실행을 수행합니다. 단계별 설명, 정상 출력 예시, 설정 변경 방법, 문제 해결은 [WORKFLOW.md](WORKFLOW.md)에 정리되어 있습니다.

## 데이터

- **출처:** V E, S., Shin, C., & Cho, Y. (2021). *Steel Industry Energy Consumption* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C52G8C
- **라이선스:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **관련 논문:** Sathishkumar V E, Shin C., Cho Y. (2021). Efficient energy consumption prediction model for a data analytic-enabled industry building in a smart city. *Building Research & Information*, 49(1), 127–143.
- **파일:** `Steel_industry_data.csv`(35,040행)와 원본 압축 파일 `steel+industry+energy+consumption.zip`. 두 파일의 내용은 동일합니다.

원본 데이터에는 다음 두 가지 특성이 있으며, 분석 코드(`src/steelenergy/io.py`)에서 모두 보정합니다.
- 날짜가 일/월/연 순서로 기록되어 있습니다.
- 매일 마지막 기록(24:00)이 같은 날짜의 00:00으로 기록되어 있습니다.

## 저장소 구조

```
src/steelenergy/   분석 코드 (모든 계산 함수)
notebooks/         분석 노트북과 노트북 생성기
web/               보고서·대시보드 템플릿과 빌드 스크립트
tests/             테스트
build/             생성된 보고서·대시보드 HTML (git 관리 대상 아님)
outputs/           analysis.json(실행 시 생성)과 보관용 PDF(v1/, v2/)
```

`outputs/v1/`, `outputs/v2/`의 PDF는 다시 생성할 수 없는 보관본이므로 삭제하지 마십시오. 상세 구조는 [WORKFLOW.md 9장](WORKFLOW.md#9-폴더-구조)을 참고하십시오.

## 관련 문서

| 문서 | 내용 |
|---|---|
| `README.md` | 본 문서. 분석 목적, 결과물, 핵심 결과 |
| [WORKFLOW.md](WORKFLOW.md) | 재현 절차: 실행, 분석 단계별 설명, 설정 변경, 검증, 문제 해결 |
| [CLAUDE.md](CLAUDE.md) | Claude Code가 이 저장소에서 작업할 때 따르는 규칙(영어). 코드 구조와 분석 규칙을 빠르게 파악하는 데에도 활용할 수 있습니다. |

**유지보수 참고:** '핵심 결과' 표의 수치와 문구는 테스트(`tests/test_docs.py`)가 분석 결과와 글자 단위로 대조합니다. 분석 변경으로 수치가 달라지면 표를 갱신하고, 표의 문장을 수정할 때는 테스트의 `expected` 목록도 함께 수정하십시오.
