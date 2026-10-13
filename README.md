# 제철소 전력 사용 분석 (2018)

제철소(철강 공장) 한 곳의 1년치 15분 단위 전력 기록을 분석한 저장소입니다. 데이터는 UCI의 Steel Industry Energy Consumption이며, 대우제철 광양 공장 자료입니다.

분석은 네 가지 질문에 답합니다.
1. 전력을 언제 몰아서 쓰는가?
2. 사용량을 미리 알 수 있는가?
3. 평소와 다르게 쓴 날은 언제인가?
4. 요금과 무효전력량을 줄일 여지는 어디에 있는가?

그 과정에서 원본의 '부하 구분' 열이 실제로 무엇을 뜻하는지도 밝혔습니다.

## 결과물

| 결과물 | 파일 | 이런 분께 |
|---|---|---|
| 보고서 | `build/report.html` | 결론과 근거만 빠르게 보고 싶은 분(공장·에너지 관리자) |
| 대시보드 | `build/dashboard.html` | 월·시간대를 골라 가며 수치를 직접 살펴보고 싶은 분 |
| 분석 노트북 | `notebooks/analysis.ipynb` | 분석 과정과 판단 근거를 따라가고 싶은 분(분석가) |

세 결과물의 숫자는 모두 같은 분석 결과 파일(`outputs/analysis.json`)에서 나오므로 서로 일치합니다.

**결과만 빨리 보려면**
- 노트북은 실행 결과가 담긴 채로 저장소에 들어 있어서 바로 열어 볼 수 있습니다.
- 보고서와 대시보드는 아래 '실행하기'의 `uv sync`, 분석, 페이지 생성 세 명령으로 만든 뒤 `build/report.html`을 브라우저로 여세요. 차트와 글꼴은 인터넷에서 불러오므로 인터넷 연결이 필요합니다.

## 핵심 결과

| 질문 | 답 | 자세히 |
|---|---|---|
| 언제 몰아서 쓰나 | 평일 08–18시는 1년 시간의 30%이지만, 이때 1년 사용량의 **64%**(약 3분의 2)를 씁니다. | 보고서 2장 |
| 미리 알 수 있나 | 15분 뒤 사용량을 평균 **3.94 kWh** 오차(오차율 16%)로 예측합니다. 직전 15분 값을 그대로 쓰는 것보다 오차가 24% 작습니다. | 보고서 4장 |
| 부하 구분의 정체 | 원본의 `Load_Type`(Light=경부하, Medium=중간부하, Maximum=최대부하)은 실제 부하가 아니라 **계절별 요금 시간표**입니다. 맞힌 정도는 평일·주말 구분과 시각·계절만으로 0.88, 과거 사용량까지 쓰면 0.96입니다. | 보고서 3장, 부록 C |
| 평소와 다른 날 | 평일 공휴일 15일 중 **7일**, 공휴일이 아닌 평일 **5일**이 휴무였고, 이상 판정은 **2일**입니다. 날짜는 대부분 달력 일정과 맞지만, 사유는 운영 기록으로 확인해야 합니다. | 보고서 5장 |
| 줄일 여지 | 역률을 0.95까지 보상하면 무효전력량이 **39%** 줄어듭니다. 최대부하 시간대 사용량 10%를 경부하 시간대로 옮기면 연 **481만 원**(가정 요금 기준)을 아낍니다. | 보고서 6장 |

**표의 용어**
- **오차율:** 15분마다의 예측 오차를 모두 더해 실제 사용량 합으로 나눈 값입니다.
- **맞힌 정도:** macro-F1입니다. 경부하·중간부하·최대부하를 각각 얼마나 잘 맞혔는지 평균한 값이며, 1이 만점입니다.
- **역률:** 공급된 전력 중 실제로 일을 한 비율입니다. 1에 가까울수록 좋습니다.
- **무효전력량(kVarh):** 전동기·변압기가 자기장을 만드는 데 오가는 전력의 양입니다. 일은 하지 않지만 설비 용량을 차지합니다.

## 실행하기

**지원 환경:** Windows 10·11(64비트 x86, ARM64), macOS(Apple Silicon, Intel), Linux(x86_64, ARM64). 32비트 Windows는 핵심 분석 패키지가 지원을 중단해 실행할 수 없습니다. 자세한 표와 확인 방법은 [WORKFLOW.md의 2장](WORKFLOW.md#2-준비물)에 있습니다.

준비물은 [uv](https://docs.astral.sh/uv/) 하나입니다. Python 3.12는 uv가 운영체제와 CPU에 맞게 알아서 받습니다.
- **uv 설치 (macOS·Linux):** `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **uv 설치 (Windows PowerShell):** `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

먼저 저장소 폴더로 이동합니다. 폴더 이름의 `&` 때문에 경로를 따옴표로 감싸야 합니다.

```bash
cd "/Users/이름/Desktop/DA&DV"          # macOS · Linux
```

```powershell
cd "C:\Users\이름\Desktop\DA&DV"       # Windows
```

아래 명령은 모든 운영체제에서 같습니다. 한 줄씩 차례로 실행하세요.

```bash
uv sync
uv run pytest
uv run python -m steelenergy.pipeline
uv run python web/build.py
uv run python notebooks/build_notebook.py
uv run jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb
```

차례로 패키지 설치, 테스트(1–3분), 분석(→ `outputs/analysis.json`), 보고서·대시보드 생성(→ `build/*.html`), 노트북 생성과 실행입니다. 단계별 설명, 정상 출력, 결과를 바꾸는 방법, 자주 막히는 곳은 [**WORKFLOW.md**](WORKFLOW.md)에 있습니다.

## 데이터

- **출처:** V E, S., Shin, C., & Cho, Y. (2021). *Steel Industry Energy Consumption* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C52G8C
- **라이선스:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **관련 논문:** Sathishkumar V E, Shin C., Cho Y. (2021). Efficient energy consumption prediction model for a data analytic-enabled industry building in a smart city. *Building Research & Information*, 49(1), 127–143.
- **파일:** `Steel_industry_data.csv`(35,040행)와 원본 압축 파일 `steel+industry+energy+consumption.zip`. 두 파일의 내용은 같습니다.

원본을 읽을 때 주의할 점이 두 가지 있습니다.
- 날짜가 일/월/연 순서입니다.
- 매일 마지막 기록(24:00)이 같은 날짜의 00:00으로 찍혀 있습니다.

분석 코드가 둘 다 보정합니다(`src/steelenergy/io.py`).

## 해석할 때 주의할 점

- **금액은 가정값입니다.** 데이터에 요금 정보가 없어 국내 산업용 계시별 요금(시간대마다 단가가 다른 요금)을 단순화한 예시 단가(`config.TARIFF_ASSUMPTIONS`)를 썼습니다. 금액의 크기보다 방향을 보는 숫자입니다.
- **공장 한 곳, 1년치 자료입니다.** 생산량·공정·설비 정보가 없어 사용량이 왜 바뀌었는지는 추정만 할 수 있습니다.
- **부하 구분 분류 점수 일부는 탐색 결과입니다.** 11–12월 결과를 본 뒤 모델을 고쳤기 때문입니다. 위 표의 0.88과 0.96은 시간 방향을 뒤집은 별도 분할(3–12월 학습, 1–2월 평가)로 낸 값입니다.
- **이상 판정은 사후 점검입니다.** 점수의 척도를 1년 전체 자료로 정했으므로, 그날 바로 울리는 경보로 쓸 수 없습니다.

## 문서 안내

| 문서 | 내용 |
|---|---|
| `README.md` | 이 문서. 무엇을, 왜 분석했고 결과가 무엇인지 |
| [WORKFLOW.md](WORKFLOW.md) | 처음부터 따라 하기: 실행, 분석 단계별 설명, 수정 방법, 검증, 문제 해결 |
| [CLAUDE.md](CLAUDE.md) | Claude Code가 이 저장소에서 작업할 때 따르는 규칙(영어). 코드 구조와 지켜야 할 분석 규칙을 빠르게 파악할 때도 쓸 수 있습니다. |

**유지보수 메모:** 위 '핵심 결과' 표의 숫자와 문구는 테스트(`tests/test_docs.py`)가 분석 결과와 글자 그대로 대조합니다. 분석을 바꿔 숫자가 달라지면 이 표를 고치세요. 표의 문장을 다듬을 때는 테스트의 `expected` 목록도 함께 고쳐야 합니다.

## 저장소 구조

```
src/steelenergy/   분석 코드 (계산 함수는 모두 여기에)
notebooks/         노트북과 노트북 생성기
web/               보고서·대시보드 템플릿과 빌드 스크립트
tests/             테스트
build/             실행하면 생기는 보고서·대시보드 (git에 넣지 않음)
outputs/           analysis.json(실행하면 생김)과 직접 저장해 둔 이전 판 PDF(v1/, v2/)
```

`outputs/v1/`, `outputs/v2/`의 PDF는 어떤 명령으로도 다시 만들 수 없으니 지우지 마세요. 자세한 구조는 [WORKFLOW.md의 9장](WORKFLOW.md#9-폴더-구조)에 있습니다.
