"""Write notebooks/analysis.ipynb. Numbers in the prose are read from outputs/analysis.json,
the same file the dashboard and report are built from, so the text cannot drift from them.

    uv run python -m steelenergy.pipeline          # writes outputs/analysis.json
    uv run python notebooks/build_notebook.py
    uv run jupyter nbconvert --to notebook --execute --inplace notebooks/analysis.ipynb
"""
import inspect
import json
import re
from pathlib import Path

import nbformat as nbf
import pandas as pd

from steelenergy import config

OUT = Path(__file__).resolve().with_name("analysis.ipynb")


def pct(x, d=0):
    return f"{x * 100:.{d}f}%"


def num(x, d=0):
    return f"{x:,.{d}f}"


def man(x):
    """KRW in 만 원."""
    return f"{x / 1e4:,.0f}만 원"


def signed_man(x):
    """KRW in 만 원 with an explicit sign."""
    return ("+" if x > 0 else "−" if x < 0 else "±") + f"{abs(x) / 1e4:,.0f}만 원"


DOW_KO = "월화수목금토일"

# Korean particles after a number depend on how its last digit is read:
# 영 일 삼 육 칠 팔 end in a consonant (일, 칠, 팔 in ㄹ); 이 사 오 구 end in a vowel.
_FINAL = {"0": "ng", "1": "l", "2": "", "3": "m", "4": "", "5": "", "6": "k", "7": "l", "8": "l", "9": ""}
_PAIRS = {("이다", "다"): ("이다", "다"), ("으로", "로"): ("으로", "로"), ("이", "가"): ("이", "가"),
          ("과", "와"): ("과", "와"), ("은", "는"): ("은", "는"), ("을", "를"): ("을", "를")}
_JOSA = re.compile(r"(\d)(이다|다|으로|로|이|가|과|와|은|는|을|를)(?=[\s.,)·]|$)")


def fix_josa(text: str) -> str:
    """Pick the particle that matches the reading of the preceding digit (e.g. 0.73이다, 0.97로)."""
    def choose(m):
        digit, particle = m.group(1), m.group(2)
        final = _FINAL[digit]
        for (cons, vow) in _PAIRS:
            if particle in (cons, vow):
                if (cons, vow) == ("으로", "로"):
                    return digit + ("로" if final in ("", "l") else "으로")
                return digit + (cons if final else vow)
        return m.group(0)
    return _JOSA.sub(choose, text)


def md_date(ts):
    return f"{ts.month}/{ts.day}"


def frame(records, index=None):
    out = pd.DataFrame(records)
    if index == "date":
        out = out.assign(date=pd.to_datetime(out["date"])).set_index("date")
    elif index:
        out = out.set_index(index)
    return out


def _context(data_path: Path) -> dict:
    """Every value the chapters quote, read from outputs/analysis.json."""
    d = json.loads(data_path.read_text(encoding="utf-8"))
    kpi, meta, A, S = d["kpi"], d["meta"], d["anomaly"], d["scenarios"]
    conc, idle = kpi["weekday_daytime"], kpi["idle"]
    monthly = frame(d["monthly"], "month")
    night = frame(d["night_load"], "month")["night_mean_kwh"]
    pf_bins, lt = frame(d["pf_by_load"], "kwh_bin"), frame(d["load_types"], "load_type")
    corr = d["correlations"]
    tests = frame(d["stats"]["tests"], "test")
    emission = d["stats"]["emission"]
    reg, clf = frame(d["regression"]["scores"], "model"), frame(d["classification"]["scores"], "model")
    best_naive = reg.loc[d["regression"]["best_naive"], "label"]
    rev = frame(d["classification"]["reverse"], "model")
    hol = frame(A["holidays"], "date")
    weekday_hol = hol[~hol["is_weekend"]]
    running = weekday_hol[~weekday_hol["shutdown"]].sort_values("ratio_to_weekday", ascending=False)
    closed = hol[hol["shutdown"]]
    flagged, near = frame(A["days"], "date"), frame(A["near_threshold"], "date")
    shutdowns = frame(A["weekday_shutdowns"], "date")
    notes = d["date_notes"]
    sens = frame(A["sensitivity"])
    pf95 = pd.Series(S["pf_default"])
    shift = frame(S["shift"], "fraction")
    s10 = shift.loc[0.1]
    sur = S["surcharge"]
    sp = meta["split"]
    labels_ = d["classification"]["confusion"]["labels"]
    cm = pd.DataFrame(d["classification"]["confusion"]["matrix"], index=labels_, columns=labels_)
    first_judged = pd.Timestamp(A["first_judged_day"])
    z_day = meta["anomaly_z_day"]
    return {
        "d": d,
        "kpi": kpi,
        "meta": meta,
        "A": A,
        "S": S,
        "conc": conc,
        "idle": idle,
        "monthly": monthly,
        "night": night,
        "pf_bins": pf_bins,
        "lt": lt,
        "corr": corr,
        "tests": tests,
        "emission": emission,
        "reg": reg,
        "clf": clf,
        "best_naive": best_naive,
        "rev": rev,
        "hol": hol,
        "weekday_hol": weekday_hol,
        "running": running,
        "closed": closed,
        "flagged": flagged,
        "near": near,
        "shutdowns": shutdowns,
        "notes": notes,
        "sens": sens,
        "pf95": pf95,
        "shift": shift,
        "s10": s10,
        "sur": sur,
        "sp": sp,
        "labels_": labels_,
        "cm": cm,
        "first_judged": first_judged,
        "z_day": z_day,
    }


def _title(md, code, best_naive, meta, weekday_hol, closed, shutdowns, flagged, conc, idle, reg, rev, s10, pf95):
    """표지: 질문과 답 요약"""
    md(f"""
# 철강 공장 전력 사용 분석 ({meta['year']})

UCI *Steel Industry Energy Consumption* 데이터로 한 공장의 1년치 15분 단위 전력 기록을 분석한다. UCI 설명에 따르면 데이터는 전남 광양의 대우제철(DAEWOO Steel Co. Ltd)에서 수집되었다(Sathishkumar, Shin & Cho, 2021, *Building Research & Information* 49(1)).

이 노트북은 분석가를 위한 작업 기록이다. 결론만 필요하면 `build/report.html`(보고서)이나 `build/dashboard.html`(대시보드)을 먼저 보면 된다.

분석 로직은 모두 `src/steelenergy/`에 있다. 이 노트북은 그 함수를 순서대로 호출하고 결과를 해석한다. 본문의 수치는 `notebooks/build_notebook.py`가 같은 파이프라인 결과로 채운 것이다.

**질문과 답**

| 질문 | 답 |
|---|---|
| 1. 전력은 언제, 얼마나 몰려서 쓰이는가? | 평일 {conc['hours'][0]:02d}–{conc['hours'][1]}시는 1년 시간의 {pct(conc['slot_share'])}지만 사용량의 {pct(conc['kwh_share'])}가 이때 쓰인다. 15분 기록의 {pct(idle['slot_share'])}는 거의 멈춘 상태(전력 중앙값 약 {num(idle['base_kw'])} kW)다. |
| 2. 소비량과 부하 구분(`Load_Type`)은 얼마나 예측 가능한가? | 15분 뒤 사용량을 평균 오차 {num(reg.loc['hgb', 'test_mae'], 2)} kWh(WAPE {pct(reg.loc['hgb', 'test_wape'])})로 예측한다. '{best_naive}' 대비 {pct(reg.loc['hgb', 'test_mae_vs_best_naive'])} 개선이다. `Load_Type`은 계절별 요금 시간표다(역방향 분할 macro-F1 {num(rev.loc['hgb', 'macro_f1'], 2)}, 요일·시각·계절 시간표만으로 {num(rev.loc['schedule_lookup_season', 'macro_f1'], 2)}). |
| 3. 평소와 다르게 쓴 날은 언제인가? | 평일 공휴일 {len(weekday_hol)}일 중 {len(closed)}일, 공휴일이 아닌 평일 {len(shutdowns)}일이 휴무였다. 그 밖의 이상 일자는 {len(flagged)}일이다. |
| 4. 비용과 무효전력을 줄일 여지는? | 역률을 {config.PF_TARGET:.2f}로 보상하면 무효전력량이 {pct(1 - pf95['kvarh_after'] / pf95['kvarh_before'])} 줄어든다. 최대부하 시간대 사용량 10%를 옮기면 가정 요금 기준 연 {man(s10['total_cost_before'] - s10['total_cost_after'])}이 절감된다. |
""")
    code("""
import matplotlib.pyplot as plt
import pandas as pd

from steelenergy import anomaly, config, eda, features, io, labels, plots, scenarios, stats, validate
from steelenergy.models import classify, regress, split

plots.setup()
pd.set_option("display.precision", 3)
pd.set_option("display.max_columns", 20)
""")


def _data(md, code):
    """1. 데이터 이해"""
    md("""
## 1. 데이터 이해

원본 컬럼과 코드에서 쓰는 이름은 아래와 같다. 역률은 원본 그대로 % 단위다. 본문에서는 0–1 비율로 바꿔 쓴다(예: 90.3% → 0.903).

| 원본 | 코드 | 뜻 | 단위 |
|---|---|---|---|
| `date` | `timestamp` | 15분 구간이 끝나는 시각 | 일/월/연 시:분 |
| `Usage_kWh` | `kwh` | 유효전력량: 실제로 일을 한 전력 | kWh / 15분 |
| `Lagging_Current_Reactive.Power_kVarh` | `lag_kvarh` | 지상 무효전력량: 전동기·변압기처럼 코일이 있는 설비에서 오가는 전력 | kVarh / 15분 |
| `Leading_Current_Reactive_Power_kVarh` | `lead_kvarh` | 진상 무효전력량: 콘덴서 쪽 무효전력 | kVarh / 15분 |
| `CO2(tCO2)` | `co2_t` | 배출량 | tCO₂ / 15분 |
| `Lagging_Current_Power_Factor` | `lag_pf` | 지상 역률 | % |
| `Leading_Current_Power_Factor` | `lead_pf` | 진상 역률 | % |
| `NSM` | `nsm` | 자정 이후 초 | 초 |
| `WeekStatus`, `Day_of_week` | `week_status`, `day_of_week` | 주중·주말, 요일 | |
| `Load_Type` | `load_type` | 부하 구분(Light/Medium/Maximum) | |

15분 사용량(kWh)에 4를 곱하면 그 15분 동안의 평균 전력(kW)이 된다.
""")
    code("""
raw = io.read_csv()
raw.head()
""")
    md("""
날짜는 일-월-연 순서다. 그런데 파일을 그대로 파싱하면 시간 순서가 맞지 않는다.
""")
    code("""
naive = pd.to_datetime(raw["timestamp_raw"], format="%d/%m/%Y %H:%M")
print("단조 증가:", naive.is_monotonic_increasing)
raw.iloc[93:98]
""")
    md("""
각 날의 마지막 행이 **같은 날짜의 00:00**으로 찍혀 있다(`NSM == 0`). 순서상 23:45 다음이므로 실제로는 그날 24:00, 즉 다음 날 00:00의 측정값이다.

`io.fix_timestamps`는 두 가지를 한다.
- 이 행을 하루 뒤로 옮긴다.
- 구간 시작 시각을 기준으로 **운영일**(`operating_day`)을 만든다. 그래서 24:00 측정값은 원래 날짜의 집계에 들어간다.
""")
    code("""
df = io.load()
df.iloc[[0, 1, 94, 95, 96, -1]][["kwh", "nsm", "day_of_week", "operating_day"]]
""")


def _validation(md, code, d):
    """2. 정제와 검증"""
    md("""
## 2. 정제와 검증

구현: `src/steelenergy/validate.py::run_checks`
""")
    code("""
checks = validate.checks_frame(validate.run_checks(df))
checks.assign(label=checks["name"].map(labels.CHECKS))[["label", "passed", "detail"]]
""")
    md(f"""
결측, 중복, 간격 누락이 없다. 요일과 주말 라벨은 `operating_day` 기준으로 모두 맞는다. 캘린더 날짜 기준으로 보면 자정 행 365개가 어긋나는데, `test_day_label_check_catches_calendar_midnight`가 이 경우를 확인한다.

남은 주의점은 `CO2(tCO2)` 컬럼이다. 소수 둘째 자리(0.01 t)로 반올림되어 있어 15분 기록의 {pct(d['stats']['co2_zero_share'])}가 0이다. 그래서 배출계수는 일·연간 합계로만 추정한다(4장).
""")
    code("""
(df["co2_t"] == 0).mean(), df["co2_t"].value_counts().head()
""")


def _eda(md, code, conc, idle, kpi, monthly, night, lt, pf_bins, corr):
    """3. 탐색적 분석"""
    md("""
## 3. 탐색적 분석

구현: `src/steelenergy/eda.py`(집계), `features.py`(피처). 평일 주간 기준 시각은 `eda.concentration`, 기저 부하 기준 5 kWh는 `eda.idle_share`의 인자다.
""")
    code("""
df = features.build(df)
daily = eda.daily_totals(df)
fig, ax = plt.subplots(figsize=(10, 3.4))
plots.daily_timeline(daily, ax=ax)
ax.set_title("일 사용량: 주말마다 깊게 떨어지고 1–2월 수준이 높다")
plots.caption(ax, f"단위 kWh/일 · {daily.index.min():%Y-%m-%d} – {daily.index.max():%Y-%m-%d} · 운영일 기준")
""")
    code("""
fig, ax = plt.subplots(figsize=(6, 5))
plots.heatmap_hour_dow(eda.hour_dow_profile(df), ax=ax)
ax.set_title("시간대 × 요일 평균 사용량")
""")
    code("""
eda.concentration(df), eda.idle_share(df)
""")
    md(f"""
- 평일 {conc['hours'][0]:02d}–{conc['hours'][1]}시는 1년 15분 기록의 {pct(conc['slot_share'])}지만 사용량의 **{pct(conc['kwh_share'])}**를 차지한다.
- 15분 기록의 {pct(idle['slot_share'])}는 15분 사용량 {num(idle['threshold_kwh'])} kWh 미만이다. 이때 전력은 중앙값 약 {num(idle['base_kw'])} kW로, 기저 부하 상태다. 일요일 대부분과 평일 야간이 여기에 해당한다.
- 토요일은 평일과 일요일 중간이다. 오전에 가동하는 주와 쉬는 주가 섞여 있어 분산이 크다(4장 참고).
""")
    code("""
monthly = eda.monthly_summary(df)
top, bottom = plots.monthly(monthly)
top.set_title("월별 일평균 사용량(위)과 역률(아래)")
plots.caption(bottom, "역률은 월 유효전력량과 지상 무효전력량 합으로 계산 · 기준선 0.90")
monthly[["kwh", "kwh_per_day", "peak_kw", "pf"]]
""")
    md(f"""
1월의 일평균 사용량({num(monthly.loc[1, 'kwh_per_day'])} kWh)은 연평균({num(kpi['mean_daily_kwh'])} kWh)의 {monthly.loc[1, 'kwh_per_day'] / kpi['mean_daily_kwh']:.1f}배다. 차이는 주로 야간에서 난다.
""")
    code("""
eda.night_load(df)
""")
    md(f"""
1–2월에는 야간(21–08시) 15분 평균 사용량이 {num(night.loc[1], 1)}, {num(night.loc[2], 1)} kWh다. 3월 이후에는 {num(night.loc[3:].min(), 1)}–{num(night.loc[3:].max(), 1)} kWh다. 겨울 두 달은 야간에도 가동했고, 3월부터 주간 위주로 바뀐 것으로 보인다.

역률은 {monthly['pf'].idxmin()}월에 {monthly['pf'].min():.3f}로 가장 낮다.
""")
    code("""
lt = eda.load_type_summary(df)
fig, ax = plt.subplots(figsize=(8, 2.6))
plots.load_type_distribution(df, ax=ax)
ax.set_title("부하 구분별 15분 사용량 분포")
lt
""")
    md(f"""
Light 시간대는 1년의 {pct(lt.loc['Light_Load', 'slot_share'])}를 차지하지만 중앙값이 {num(lt.loc['Light_Load', 'median_kwh'], 1)} kWh로 대부분 정지 상태다. Maximum 시간대는 시간 비중 {pct(lt.loc['Maximum_Load', 'slot_share'])}에 사용량의 {pct(lt.loc['Maximum_Load', 'kwh_share'])}를 쓴다.
""")
    code("""
pf_bins = eda.pf_by_load_bin(df)
ax = plots.pf_by_load(pf_bins)
ax.set_title("거의 정지한 구간(5 kWh 미만)만 역률이 크게 낮다")
plots.caption(ax, "주황 = 역률 0.90 미만 · 가로선 = 0.90")
pf_bins
""")
    md(f"""
역률이 낮은 주원인은 **거의 정지한 구간**이다. 15분 5 kWh 미만에서는 역률이 {pf_bins['pf'].iloc[0]:.2f}다. 설비가 멈춰 있어도 변압기와 모터의 여자 전류(자화 전류) 때문에 무효전력이 계속 흐르기 때문이다. 그 밖의 구간은 {pf_bins['pf'].iloc[1:].min():.2f}–{pf_bins['pf'].iloc[1:].max():.2f}로 단조 관계는 아니다.
""")
    code("""
corr = eda.correlations(df)  # Spearman 순위 상관(eda.correlations 참고)
corr
""")
    md(f"""
Spearman 상관으로 보면 `kwh`와 `co2_t`는 {corr['co2_t']:.2f}다. CO₂는 사용량에서 계산된 값에 가깝다(4장). `lag_kvarh`도 사용량과 {corr['lag_kvarh']:.2f}로 함께 움직인다.
""")


def _stats(md, code, tests, emission):
    """4. 통계 검정"""
    md("""
## 4. 통계 검정

구현: `src/steelenergy/stats.py`

15분 기록은 자기상관이 강하다. 3만 5천 행으로 검정하면 독립성 가정이 깨지고 p값이 무의미하게 작아진다. 그래서 다음과 같이 했다.
- **일 단위 집계**를 관측 단위로 쓴다.
- 효과크기의 신뢰구간은 **주 단위 블록 부트스트랩**으로 구한다. 월–일 한 주를 통째로 복원추출하므로 같은 주 안의 의존성이 유지된다.
- p값은 Holm 방법으로 보정했다. 여러 검정을 동시에 할 때 우연히 유의해지는 것을 막는 보정이다.

하루 합계도 전날과 연관이 있다(아래 1일 시차 자기상관). 그래서 순위 검정의 p값은 독립을 가정한 만큼 실제보다 작게 나온다. 결론은 효과크기와 블록 부트스트랩 신뢰구간으로 내리고, p값은 참고용으로만 둔다.
""")
    code("""
daily["kwh"].autocorr(lag=1)
""")
    code("""
tests = stats.run_tests(df, daily)
tests[["question", "n", "test", "effect_name", "effect", "ci_low", "ci_high", "p_holm"]]
""")
    mw, sw = tests.loc["Mann–Whitney U"], tests.loc["Wilcoxon signed-rank"]
    fr, kw = tests.loc["Friedman χ²"], tests.loc["Kruskal–Wallis H"]
    md(f"""
- **평일과 주말:** Cliff's δ = {mw['effect']:.2f} [{mw['ci_low']:.2f}, {mw['ci_high']:.2f}]. δ는 한쪽 값이 다른 쪽보다 클 확률에서 반대 확률을 뺀 값이다. 무작위로 고른 평일이 주말보다 사용량이 많을 확률은 P = (1 + δ) / 2 ≈ {pct((mw['effect'] + 1) / 2)}다.
- **토요일과 일요일:** δ = {sw['effect']:.2f}. 토요일 가동 여부가 주마다 다르다.
- **부하 구분 간 수준 차이:** Kendall's W = {fr['effect']:.2f}로 매우 일관적이다. W는 0–1이며 1이면 모든 날의 순위가 같다는 뜻이다. 세 부하 구분이 모두 있는 {int(fr['n'])}일만 썼다.
- **평일만 본 월별 차이:** ε² = {kw['effect']:.2f}로, 월이 일 사용량 분산의 약 {pct(kw['effect'])}를 설명한다. 다만 신뢰구간이 {kw['ci_low']:.2f}–{kw['ci_high']:.2f}로 넓다.
""")
    code("""
stats.emission_factor(daily)
""")
    md(f"""
연간 합계로 계산한 배출계수는 **{emission['ratio_of_sums']:.3f} tCO₂/MWh**다. 일 단위로 원점을 지나는 회귀를 하면 {emission['t_per_mwh']:.3f}이고 R²는 {emission['r2_daily']:.2f}다. 보고서와 대시보드는 연간 합계 기준을 쓴다.

CO₂는 사용량에 계수를 곱한 값에 가깝다. 그래서 CO₂를 사용량 예측의 입력으로 쓰면 정답을 거의 그대로 넣는 셈이 된다(누수).
""")


def _forecast(md, code, meta, sp, best_naive, reg, d):
    """5. 사용량 예측"""
    md(f"""
## 5. 사용량 예측 (15분 앞)

구현: `src/steelenergy/models/split.py`, `models/regress.py`

**설정**
- t 시점의 kWh를 t−1까지의 정보만으로 예측한다.
- 입력은 달력 피처와 과거 사용량(lag·rolling)뿐이다. 같은 구간의 무효전력·역률·CO₂는 쓰지 않는다.
- 학습 {sp['train']['start']}–{sp['train']['end']}, 검증 10월, 테스트 11–12월로 나눴다. 1주 전 값(`kwh_lag672`)이 필요해서 첫 {meta['history_days_dropped']}일({sp['train']['start']} 이전)은 빠진다.
- 모델 선택은 검증으로만 했다. 테스트는 학습+검증(1–10월)으로 다시 학습한 뒤 한 번만 평가했다.

**모델**
- 기준선 세 가지: 직전값 그대로, 하루 전 같은 시각, 일주일 전 같은 시각
- 선형 회귀: Ridge(L2 정규화 선형회귀)
- 부스팅 트리: HGB(scikit-learn `HistGradientBoostingRegressor`, 결정트리를 순차적으로 쌓는 모델)

**지표**
- MAE: 평균 절대 오차(kWh)
- RMSE: 큰 오차에 더 민감한 오차
- WAPE: 총 사용량 대비 절대 오차 합(%)

구간의 절반이 3 kWh 근처라 MAPE는 쓰지 않는다. 값이 작은 구간에서 비율 오차가 폭주하기 때문이다.
""")
    code("""
sp = split.by_date(df)
sp.periods()
""")
    code("""
reg = regress.evaluate(sp)
reg.scores.rename(index=labels.REGRESSION)
""")
    md(f"""
- 직전값이 생각보다 강하다(MAE {reg.loc['naive_last', 'test_mae']:.2f}). 하루 전·일주일 전 값은 가동 여부가 바뀌는 날이 많아 훨씬 나쁘다.
- Ridge({reg.loc['ridge', 'test_mae']:.2f})는 직전값보다 못하다. 가동 시작과 정지 같은 급격한 전환은 선형 모델로 잡지 못한다.
- HGB는 테스트 MAE {reg.loc['hgb', 'test_mae']:.2f} kWh로 검증에서 가장 나았던 기준선('{best_naive}') 대비 **{pct(reg.loc['hgb', 'test_mae_vs_best_naive'])}** 개선했다. 같은 기간(11–12월)의 15분 평균 사용량 {d['regression']['test_mean_kwh']:.1f} kWh와 견주어 보면 된다.
""")
    code("""
week = reg.test_predictions["operating_day"].between(*config.FORECAST_WEEK)
ax = plots.forecast_week(reg.test_predictions[week])  # 직전값 선은 실측과 겹쳐 생략(show_naive=True로 표시)
ax.set_title(f"테스트 기간 한 주({config.FORECAST_WEEK[0]} – {config.FORECAST_WEEK[1]}) 예측")
""")
    code("""
ax = plots.error_by_hour(reg.error_by_hour)
ax.set_title("HGB의 이점은 점심 정지(12시)·재가동(13시)·가동 시작(08시)에 크다")
reg.importance.rename(index=labels.FEATURES).head(8)
""")
    md("""
순열 중요도는 피처 하나를 무작위로 섞었을 때 MAE가 얼마나 늘어나는지를 잰다. 직전 15분 사용량의 영향이 압도적이다.

시각별로 보면 HGB의 이점은 사용량이 급변하는 시각에 몰린다. 밤(22–07시)에는 두 방법 모두 오차가 1 kWh 미만이고, 직전값이 근소하게 낫다.
""")


def _classification(md, code, clf, rev, cm, d):
    """6. 부하 구분 분류"""
    md(f"""
## 6. 부하 구분 분류: 처음 시도와 수정

구현: `src/steelenergy/models/classify.py`

처음에는 달력 피처(요일, 시각, 월)와 과거 사용량으로 `Load_Type`을 분류했다. 검증(10월)에서 macro-F1 {clf.loc['hgb_no_season', 'valid_macro_f1']:.2f}이 나왔다. 테스트(11–12월)에서는 **{clf.loc['hgb_no_season', 'test_macro_f1']:.2f}**로 떨어졌다. macro-F1은 세 등급을 각각 얼마나 잘 맞혔는지를 평균한 값으로, 1이 만점이다.
""")
    code("""
clf = classify.evaluate(sp)
clf.scores.assign(label=clf.scores.index.map(lambda m: labels.CLASSIFICATION[m][0]))
""")
    md("""
초기 모델(계절 미반영)의 테스트 혼동행렬을 보면 오차가 거의 전부 Medium과 Maximum 사이에서 난다.
""")
    code("""
clf.confusions["hgb_no_season"]
""")
    md("""
월·시간별로 가장 흔한 라벨을 펼쳐 보면 원인이 드러난다.
""")
    code("""
schedule = eda.tou_schedule(df)
ax = plots.tou_schedule(schedule)
ax.set_title("평일 부하 구분은 계절별 고정 시간표다")
plots.caption(ax, "밝음 Light · 중간 Medium · 어두움 Maximum")
""")
    md(f"""
`Load_Type`은 측정된 부하 상태가 아니다. **계절에 따라 바뀌는 시간대별 요금 구간(TOU, 계시별 요금) 라벨**에 가깝다.
- 3–10월: Maximum이 10–12시, 13–17시다.
- 11–2월: Maximum이 10–12시, 17–20시, 22–23시로 바뀐다.
- 검증 기간인 10월은 여름 시간표라서 이 변화를 보지 못했다.

수정한 내용은 두 가지다.
1. `is_winter`(11–2월) 피처를 추가했다.
2. `month`를 모델 입력에서 뺐다.

두 번째 수정의 이유는 위 표의 `hgb_season_month_first`와 `hgb_season_month_last`에 있다. 두 행은 같은 피처를 쓰고 열 순서만 다르다. 그런데 테스트 F1이 {clf.loc['hgb_season_month_first', 'test_macro_f1']:.2f}과 {clf.loc['hgb_season_month_last', 'test_macro_f1']:.2f}로 갈린다.
- 학습 기간(1–10월)에는 `is_winter == 1`과 `month <= 2`가 정확히 같은 행을 가리킨다.
- 트리는 둘 중 하나로 분기하고, 동률이면 열 순서로 고른다.
- `month`로 분기한 모델은 처음 보는 11·12월을 여름(3–10월) 쪽으로 보낸다.

아래 셀에서 시드(0, 42)를 바꿔도 결과가 같고 열 순서에만 달려 있음을 확인한다. 우연에 기대는 모델이므로 `month`를 뺐다.
""")
    code("""
classify.column_order_check(sp)
""")
    md(f"""
열 순서가 같으면 시드와 무관하게 같은 점수가 나온다.

수정 후 HGB의 테스트 macro-F1은 **{clf.loc['hgb', 'test_macro_f1']:.3f}**다. 같은 구간의 전기 측정값을 더해도 {clf.loc['hgb_same_interval', 'test_macro_f1']:.3f}로 거의 같다. 라벨이 시간표로 정해진다는 해석과 맞는 결과다.

**이 점수는 독립적인 확인이 아니다.** 11–12월 결과를 보고 모델을 고쳤으므로, 같은 기간의 점수는 탐색 결과다. 그래서 시간 방향을 뒤집은 별도 분할로 다시 확인한다. 3–12월로 학습하고 또 다른 겨울 기간인 1–2월로 평가한다. 1–2월도 처음 학습과 시간표 분석에 쓰였으므로 완전히 새로운 자료는 아니다. 새 연도 자료가 생기면 그것으로 확인하는 것이 맞다.
""")
    code("""
classify.reverse_check(df)
""")
    md(f"""
1–2월에서 최종 모델은 {rev.loc['hgb', 'macro_f1']:.3f}, 요일·시각·계절 시간표는 {rev.loc['schedule_lookup_season', 'macro_f1']:.3f}다. 계절을 빼면 {rev.loc['schedule_lookup', 'macro_f1']:.3f}에 그친다. 계절별 시간표라는 결론이 뒤집은 분할에서도 유지된다.
""")
    code("""
fig, ax = plt.subplots(figsize=(4.2, 3.6))
plots.confusion(clf.confusion, ax=ax)
ax.set_title("HGB(계절 반영) 테스트 혼동행렬")
""")
    md(f"""
최종 모델의 남은 오분류는 실제 Maximum을 Light로 본 {int(cm.loc['Maximum_Load', 'Light_Load'])}건과 실제 Medium을 Light로 본 {int(cm.loc['Medium_Load', 'Light_Load'])}건이 대부분이다. 평일·주말로 나누면 다음과 같다.
""")
    code("""
clf.errors_by_daytype
""")
    eb = frame(d["classification"]["errors_by_daytype"], "daytype")
    md(f"""
오분류의 {pct(eb.loc['주말', 'share_of_errors'])}가 주말에서 나온다. 주말은 테스트 기간 기록의 {pct(eb.loc['주말', 'slots'] / eb['slots'].sum())}다. 학습 기간에 겨울 주말은 1–2월분밖에 없었다.
""")


def _anomaly(md, code, closed, running, z_day, meta, hol, weekday_hol, notes, flagged, near, first_judged, shutdowns, A, sens):
    """7. 휴무와 이상 탐지"""
    hol_closed = ", ".join(f"{md_date(day)} {h}" for day, h in closed["holiday"].items())
    hol_running = ", ".join(f"{h.holiday}({pct(h.ratio_to_weekday)})" for h in running.itertuples())
    md(f"""
## 7. 휴무와 이상 탐지

구현: `src/steelenergy/anomaly.py`, `eda.holiday_operation`, `eda.weekday_shutdowns`. 기준값은 `config.py`의 `SHUTDOWN_RATIO`, `ANOMALY_Z_DAY`, `ANOMALY_Z_INTERVAL`, `ANOMALY_MIN_RUN`이다.

**처음 시도**(작업 기록이며 현재 코드에는 남겨 두지 않았다)는 달력 피처만으로 기대 사용량을 예측하고(이전 달까지로 학습), 그 잔차가 큰 구간을 이상으로 보는 방식이었다. 결과는 15분 기록의 약 15%가 이상으로 잡혔다. 1–2월의 야간 가동이 3월부터 줄어든 것처럼, 운영 방식이 바뀌면 그 이후가 전부 이상으로 표시되었다. 이 방식은 폐기했다.

최종 방식은 세 가지다.
- **공휴일**: 미리 알 수 있는 정보이므로 {meta['year']}년 한국 공휴일 달력(`config.KR_HOLIDAYS_2018`)으로 따로 정리한다. 주말과 겹친 공휴일은 원래 쉬는 날이라 휴무 판정에서 뺀다.
- **일 단위 이상**: 각 날을 직전 4주 같은 요일(공휴일 제외)의 중앙값과 비교한다. 평일·토·일별로 robust z를 계산하고 |z| ≥ {z_day:.0f}이면 이상으로 본다.
  - robust z는 평균·표준편차 대신 중앙값과 MAD(중앙값 절대편차)로 표준화한 편차 점수다. 이상치 몇 개에 기준이 흔들리지 않는다.
  - 기대값은 과거만 참조하므로 운영 방식이 바뀌면 한 번 표시된 뒤 기준에 흡수된다.
  - 다만 점수의 척도(잔차의 중앙값·MAD)는 1년 전체로 계산한다. 그날 바로 울리는 경보가 아니라 사후 점검이다.
- **15분 단위 점검 구간**: 월별 확장 창(매달 그 이전 모든 달로 다시 학습)으로 만든 15분 앞 예측의 잔차를 본다. 잔차를 (평일·토·일, 시각) 칸마다 중앙값과 MAD로 표준화해 z를 만든다. 칸마다 평소 흔들림이 다르기 때문이다(`anomaly.robust_z`, `anomaly.flag`).
""")
    code("""
holidays = eda.holiday_operation(daily)
holidays[["holiday", "is_weekend", "kwh", "ratio_to_weekday", "shutdown"]]
""")
    md(f"""
공휴일 {len(hol)}일 가운데 {int(hol['is_weekend'].sum())}일은 주말과 겹친다. 평일 공휴일 {len(weekday_hol)}일 중 {len(closed)}일은 휴무였다(평일 중앙값의 {pct(config.SHUTDOWN_RATIO)} 미만): {hol_closed}.

나머지 공휴일에는 가동했고, 가동 수준은 날마다 달랐다: {hol_running}.

이 공장은 명절과 신정·성탄절에 쉬고 나머지 공휴일에는 대체로 가동한다.
""")
    code("""
days = anomaly.daily_deviation(daily)
days[days["flag"]][["weekday", "kwh", "expected_kwh", "z"]]
""")
    def note(day):
        return notes.get(day.strftime("%Y-%m-%d"), "사유는 운영 기록으로 확인해야 한다.")
    flagged_text = "\n".join(
        f"- {md_date(day)}({DOW_KO[day.dayofweek]}): 실측 {num(row.kwh)} kWh, 평소 {num(row.expected_kwh)} kWh, z {row.z:.1f}. {note(day)}"
        for day, row in flagged.iterrows())
    near_text = ", ".join(f"{md_date(day)}({DOW_KO[day.dayofweek]}, z {row.z:.1f})" for day, row in near.iterrows())
    md(f"""
공휴일을 제외하면 일 단위 이상은 {len(flagged)}일이다.
{flagged_text}

비교할 이전 같은 요일 4번이 쌓이기 전인 {md_date(first_judged)} 이전은 판정하지 않았다. 사유는 전력 기록만으로 확정할 수 없으므로 위 설명은 달력에 비춘 추정이다.

임계값 바로 아래(3 ≤ |z| < {z_day:.0f})에는 {near_text or "해당하는 날이 없다"}가 있다. 이 가운데 연속 휴무의 일부인 날이 있는지 앞뒤 날짜를 확인해 본다.
""")
    code("""
runs = eda.shutdown_runs(eda.weekday_shutdowns(daily))
longest = runs.loc[runs["days"].idxmax()]  # 가장 긴 연속 휴무와 앞뒤 날짜
daily.loc[longest["start"] - pd.Timedelta(days=2):longest["end"] + pd.Timedelta(days=4), ["kwh"]].T.round(0)
""")
    md(f"""
휴무가 여러 날 이어지면 z 기준으로는 잘 잡히지 않는다. 평일 잔차의 MAD가 커서 휴무일의 z가 −3 언저리에 머물기 때문이다.

그래서 휴무는 z 대신 단순한 규칙으로 따로 판정한다. 공휴일이 아닌 평일 중 사용량이 평일 중앙값의 {pct(config.SHUTDOWN_RATIO)} 미만인 날을 휴무로 본다.
""")
    code("""
eda.weekday_shutdowns(daily)
""")
    md(f"""
공휴일이 아닌 평일 휴무는 {len(shutdowns)}일이다.
{chr(10).join(f"- {md_date(day)}: {note(day)}" for day in shutdowns.index)}

이상 탐지에 잡힌 날과 휴무일은 모두 달력 일정과 맞아떨어진다. 다만 실제 사유(휴가, 특근, 설비 문제)는 전력 기록만으로 확정할 수 없고 운영 기록으로 확인해야 한다.
""")
    code("""
fig, ax = plt.subplots(figsize=(10, 3.4))
plots.daily_timeline(daily, days[days["flag"]], ax=ax)
ax.set_title(f"공휴일을 제외한 일 단위 이상은 {int(days['flag'].sum())}일")
""")
    code("""
intervals = anomaly.flag(df, regress.out_of_fold_forecast(split.monthly_folds(df)))
anomaly.sensitivity(intervals)
""")
    md(f"""
15분 단위 잔차는 꼬리가 매우 두껍다. 임계값을 {sens['z'].iloc[0]}에서 {sens['z'].iloc[-1]}로 올려도 플래그 비율이 {pct(sens['flag_rate'].iloc[0], 1)}에서 {pct(sens['flag_rate'].iloc[-1], 1)}로 천천히 줄 뿐 뚜렷한 끊김이 없다. 설비가 켜지고 꺼지는 순간이 매번 큰 잔차를 만들기 때문이다.

그래서 15분 단위 결과는 현장에서 확인할 **점검 목록**으로만 쓴다. |z| ≥ {meta['anomaly_z_interval']:.0f}인 15분 기록이 {config.ANOMALY_MIN_RUN}개 이상({A['min_run_minutes']}분 이상) 이어진 연속 이벤트만 남겼다.
""")
    code("""
episodes = anomaly.episodes(intervals)
episodes.head(10)
""")
    code("""
anomaly.isolation_forest_agreement(df, intervals)
""")
    md(f"""
Isolation Forest는 전기 측정값만 보고 이상을 고르는 다른 방식의 알고리즘이다. 잔차 기반 플래그 중 {pct(A['iforest']['share_of_residual_flags_also_iforest'])}는 Isolation Forest도 이상으로 잡았다. 같은 비율로 무작위로 플래그를 찍었을 때 기대되는 겹침은 {pct(A['iforest']['chance_overlap'], 1)}다. 두 방법은 서로 다른 것을 본다. 이 정도 일치를 근거로 '확정 이상'이라고 할 수는 없다.
""")


def _scenarios(md, code, sur, pf95, s10, shift, S):
    """8. 절감 시나리오"""
    md("""
## 8. 절감 시나리오

구현: `src/steelenergy/scenarios.py`

이 데이터에는 요금 정보가 없다. 요금 단가와 역률 할증 규칙은 `config.TARIFF_ASSUMPTIONS`에 둔 **가정값**이다. 금액은 구조를 비교하는 용도로만 해석해야 한다.
""")
    code("""
config.TARIFF_ASSUMPTIONS
""")
    md("""
**(a) 역률 보상**: 역률이 목표값보다 낮은 15분 기록의 지상 무효전력량을 목표 수준까지 줄인다. 콘덴서 설치를 가정한 계산이다. 유효전력량(kWh)과 CO₂는 변하지 않는다. 바뀌는 것은 다음 세 가지다.
- 연간 무효전력량(kVarh). 콘덴서 용량(kVar)과는 다른 값이다.
- 피상전력 최대치: 변압기가 감당하는 전체 전력(kVA)
- 역률 할증
""")
    code("""
pf = scenarios.pf_grid(df)
pf.assign(**{c: pf[c] / 1e4 for c in ["surcharge_before", "surcharge_after"]}).round(3)
""")
    md(f"""
목표 역률을 {config.PF_TARGET:.2f}로 잡으면 다음과 같이 바뀐다.
- 지상 무효전력량: {num(pf95['kvarh_before'] / 1000)} → {num(pf95['kvarh_after'] / 1000)} MVarh({pct(1 - pf95['kvarh_after'] / pf95['kvarh_before'])} 감소)
- 피상전력 최대치: {num(pf95['peak_kva_before'])} → {num(pf95['peak_kva_after'])} kVA

가정한 요금 체계에서 역률 할증은 연 {man(pf95['surcharge_before'])} 수준이다. 할증은 {sur['months_with_surcharge']}개월에 붙지만 {pct(sur['focus_share'])}가 8–10월에 몰려 있다. 금액보다는 변압기 여유와 손실 감소 쪽 효과가 크다.
""")
    md("""
**(b) 피크 부하 이동**: 최대부하(Maximum) 시간대 사용량의 일부를 같은 날 경부하(Light) 시간대로 고르게 옮긴다. 옮기는 사용량에 딸린 무효전력량도 원래 비율대로 함께 옮긴다. 총 kWh와 CO₂는 보존되고, 바뀌는 것은 시간대별 요금과 최대 수요다.

*작업 중 수정:* 처음 구현에서는 무효전력량을 받는 쪽(경부하 시간대)의 비율로 다시 계산했다. 그러자 정지 구간의 나쁜 역률이 옮긴 부하에 붙어 할증이 늘어나는 것처럼 나왔다. 지금은 원래 비율을 유지하고, 하루 단위로 kWh와 kVarh가 모두 보존되는지 테스트(`test_shift_conserves_daily_*`)로 확인한다.
""")
    code("""
cost_cols = ["energy_cost_after", "demand_cost_after", "surcharge_after", "total_cost_after"]
grid = scenarios.shift_grid(df).set_index("fraction")
(grid[cost_cols] - grid[[c.replace("after", "before") for c in cost_cols]].values).div(1e4).round(0).join(
    grid["mean_monthly_peak_kw_after"].round(0))
""")
    md(f"""
위 표는 만 원 단위의 변화량이다. 최대부하 시간대 사용량의 10%를 옮기면 가정 요금 기준 연 {man(s10['total_cost_before'] - s10['total_cost_after'])}({pct(1 - s10['total_cost_after'] / s10['total_cost_before'], 1)})이 줄어든다.
- 전력량요금: {signed_man(s10['energy_cost_after'] - s10['energy_cost_before'])}
- 기본요금: {signed_man(s10['demand_cost_after'] - s10['demand_cost_before'])}

월 최대 수요의 평균(현재 {num(shift.loc[0.0, 'mean_monthly_peak_kw_before'])} kW)은 이동 비율에 따라 {", ".join(f"{pct(f)}에서 {num(row.mean_monthly_peak_kw_after)} kW" for f, row in shift.iloc[1:].iterrows())}가 된다. {"이동 비율 " + pct(S["first_demand_increase"]) + "부터는 기본요금이 오히려 늘어난다." if S["first_demand_increase"] is not None else "기본요금은 줄어든다."} 경부하 시간대는 주로 야간이라, 이미 가동 중인 야간에 부하가 더해지면 새 피크가 생긴다. 실제로 옮길 수 있는 공정이 있는지는 이 데이터로 알 수 없다.
""")


def _conclusion(md):
    """9. 정리와 한계"""
    md("""
## 9. 정리와 한계

맨 위의 질문과 답 표가 이 노트북의 결론이다.

**한계**
- 공장 한 곳의 1년치 데이터다. 겨울 시간표 기간은 1–2월과 11–12월뿐이라 계절 패턴을 학습할 표본이 적다.
- 생산량, 공정, 설비 정보가 없어 사용량이 왜 바뀌었는지는 추정만 할 수 있다.
- 요금은 가정값이다. CO₂는 0.01 t 단위로 반올림되어 있다.
- 공휴일 달력은 휴무·이상 분석에만 썼다. 예측·분류 모델에 공휴일과 겨울 주말 정보를 넣는 것은 다음 단계로 남긴다.
""")


CHAPTERS = [
    _title,
    _data,
    _validation,
    _eda,
    _stats,
    _forecast,
    _classification,
    _anomaly,
    _scenarios,
    _conclusion,
]


def build(data_path: Path = config.OUTPUT_DIR / "analysis.json") -> nbf.NotebookNode:
    """Assemble the notebook chapter by chapter; each chapter takes only the values it quotes."""
    ctx = _context(data_path)
    cells = []

    def md(text):
        cells.append(nbf.v4.new_markdown_cell(fix_josa(text.strip())))

    def code(text):
        cells.append(nbf.v4.new_code_cell(text.strip()))

    ctx.update(md=md, code=code)
    for chapter in CHAPTERS:
        wanted = inspect.signature(chapter).parameters
        chapter(**{name: ctx[name] for name in wanted})

    nb = nbf.v4.new_notebook()
    nb["cells"] = cells
    nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    return nb


if __name__ == "__main__":
    nbf.write(build(), OUT)
    print(f"wrote {OUT.relative_to(config.ROOT)}")
