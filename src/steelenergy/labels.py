"""Korean display names shared by the notebook, dashboard and report. Presentation only."""

REGRESSION = {
    "naive_last": "직전값 그대로",
    "naive_day": "하루 전 같은 시각",
    "naive_week": "일주일 전 같은 시각",
    "ridge": "선형 회귀(Ridge)",
    "hgb": "부스팅 트리(HGB)",
}

# One line on what each forecasting method does, for readers who do not know the model names.
REGRESSION_DESC = {
    "naive_last": "비교용: 직전 15분 값을 그대로 쓴다",
    "naive_day": "비교용: 하루 전 같은 시각 값을 쓴다",
    "naive_week": "비교용: 일주일 전 같은 시각 값을 쓴다",
    "ridge": "시각과 과거 사용량을 직선식으로 조합한다",
    "hgb": "과거 사용 패턴을 조건별로 나눠 조합한다(채택)",
}

BAND = {"Light_Load": "경부하", "Medium_Load": "중간부하", "Maximum_Load": "최대부하"}

CLASSIFICATION = {
    "schedule_lookup": ("시간표 조회", "요일 구분·시각"),
    "hgb_no_season": ("부스팅 트리(HGB)", "달력·월·과거 사용량"),
    "hgb_season_month_first": ("부스팅 트리(HGB)", "달력·계절·월·과거 사용량 (월 열 먼저)"),
    "hgb_season_month_last": ("부스팅 트리(HGB)", "달력·계절·과거 사용량·월 (월 열 나중)"),
    "schedule_lookup_season": ("시간표 조회", "요일 구분·시각·계절"),
    "logistic": ("로지스틱 회귀", "달력·계절·과거 사용량"),
    "hgb": ("부스팅 트리(HGB)", "달력·계절·과거 사용량"),
    "hgb_same_interval": ("부스팅 트리(HGB)", "위 입력 + 같은 시각 전력 측정값"),
}

FEATURES = {
    "kwh_lag1": "직전 15분 사용량",
    "kwh_lag2": "30분 전 사용량",
    "kwh_lag4": "1시간 전 사용량",
    "kwh_lag96": "하루 전 같은 시각",
    "kwh_lag672": "일주일 전 같은 시각",
    "kwh_roll4": "최근 1시간 평균",
    "kwh_roll96": "최근 24시간 평균",
    "slot": "하루 중 순번(15분 단위)",
    "hour": "시각",
    "hour_sin": "시각(하루 주기 성분 1)",
    "hour_cos": "시각(하루 주기 성분 2)",
    "dow": "요일",
    "dow_sin": "요일(주간 주기 성분 1)",
    "dow_cos": "요일(주간 주기 성분 2)",
    "is_weekend": "주말 여부",
    "is_winter": "겨울 시간표(11–2월)",
}

CHECKS = {
    "row_count": "행 수",
    "missing_values": "결측값",
    "unique_timestamps": "시각 중복",
    "monotonic_index": "시간 순서",
    "regular_interval": "15분 간격",
    "slots_per_day": "하루 96개 기록",
    "day_of_week_label": "요일 표기",
    "week_status_label": "주중·주말 표기",
    "non_negative": "음수 없음",
    "power_factor_range": "역률 0–100%",
    "nsm_consistent": "자정 이후 초(NSM) 일치",
}

# Analyst notes for specific 2018 dates. The data cannot confirm causes, so every note is
# worded as a calendar fact or a possibility; dashboards, report and notebook all read these.
DATE_NOTES = {
    "2018-02-14": "설 연휴 전날. 연휴에 앞서 일찍 멈춘 것으로 보인다.",
    "2018-07-15": "일요일인데 평일 수준으로 썼다. 특근일 가능성이 있다.",
    "2018-05-01": "근로자의 날",
    "2018-08-01": "8월 초 연속 저사용일(여름휴가 추정)",
    "2018-08-02": "8월 초 연속 저사용일(여름휴가 추정)",
    "2018-08-03": "8월 초 연속 저사용일(여름휴가 추정)",
    "2018-12-31": "연말",
}
