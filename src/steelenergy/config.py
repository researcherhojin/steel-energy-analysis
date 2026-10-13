from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DATASET = {
    "source": "UCI Machine Learning Repository, Steel Industry Energy Consumption (id 851)",
    "plant": "DAEWOO Steel Co. Ltd, Gwangyang, South Korea",
    "citation": "Sathishkumar V E, Shin C., Cho Y. (2021). Building Research & Information 49(1), 127–143.",
}
RAW_CSV = ROOT / "Steel_industry_data.csv"
OUTPUT_DIR = ROOT / "outputs"
BUILD_DIR = ROOT / "build"

SEED = 42
INTERVAL_MIN = 15
SLOTS_PER_DAY = 24 * 60 // INTERVAL_MIN
EXPECTED_ROWS = 365 * SLOTS_PER_DAY

COLUMNS = {
    "date": "timestamp_raw",
    "Usage_kWh": "kwh",
    "Lagging_Current_Reactive.Power_kVarh": "lag_kvarh",
    "Leading_Current_Reactive_Power_kVarh": "lead_kvarh",
    "CO2(tCO2)": "co2_t",
    "Lagging_Current_Power_Factor": "lag_pf",
    "Leading_Current_Power_Factor": "lead_pf",
    "NSM": "nsm",
    "WeekStatus": "week_status",
    "Day_of_week": "day_of_week",
    "Load_Type": "load_type",
}

LOAD_TYPES = ["Light_Load", "Medium_Load", "Maximum_Load"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# Months on the winter time-of-use schedule (found in the data, see notebook §6).
WINTER_MONTHS = (11, 12, 1, 2)

# Korean public holidays in 2018 (관공서의 공휴일에 관한 규정, including substitute days
# and the local election). The dataset itself has no holiday flag.
KR_HOLIDAYS_2018 = {
    "2018-01-01": "신정",
    "2018-02-15": "설날 연휴",
    "2018-02-16": "설날",
    "2018-02-17": "설날 연휴",
    "2018-03-01": "삼일절",
    "2018-05-05": "어린이날",
    "2018-05-07": "대체공휴일",
    "2018-05-22": "부처님오신날",
    "2018-06-06": "현충일",
    "2018-06-13": "지방선거",
    "2018-08-15": "광복절",
    "2018-09-23": "추석 연휴",
    "2018-09-24": "추석",
    "2018-09-25": "추석 연휴",
    "2018-09-26": "대체공휴일",
    "2018-10-03": "개천절",
    "2018-10-09": "한글날",
    "2018-12-25": "성탄절",
}
# A day below this share of the median weekday is treated as a shutdown.
SHUTDOWN_RATIO = 0.2

# Time-ordered split on operating day. Test is touched once, at the end.
TRAIN_END = "2018-09-30"
VALID_END = "2018-10-31"
# One test-period week shown as a forecast example (operating days, inclusive).
FORECAST_WEEK = ("2018-12-03", "2018-12-09")

# The dataset carries no tariff. These are illustrative assumptions, labelled as such
# wherever they surface; change them here and every downstream number follows.
TARIFF_ASSUMPTIONS = {
    "currency": "KRW",
    "energy_rate_per_kwh": {"Light_Load": 95.0, "Medium_Load": 140.0, "Maximum_Load": 210.0},
    "demand_rate_per_kw_month": 8_300.0,
    "pf_threshold": 0.90,
    "pf_penalty_rate_per_pct": 0.002,  # surcharge on energy charge per pct-point below threshold
    "source": "가정값 (국내 산업용 TOU 요금 구조를 단순화한 예시 단가)",
}
PF_TARGET = 0.95
SHIFT_EXAMPLE = 0.10  # the load-shift fraction the report and README quote

# Day-level deviations are near-normal; 15-min forecast residuals are heavy-tailed
# (machines switching on/off), so the interval threshold sits higher.
ANOMALY_Z_DAY = 4.0
ANOMALY_Z_INTERVAL = 6.0
ANOMALY_MIN_RUN = 2  # consecutive 15-min slots
NEAR_THRESHOLD_Z = 3.0  # days with NEAR_THRESHOLD_Z <= |z| < ANOMALY_Z_DAY are listed for a second look

# Model and resampling settings. Kept here so every caller fits the same model.
HGB_CLASSIFIER = {"max_iter": 300, "learning_rate": 0.08}
HGB_REGRESSOR = {"max_iter": 400, "learning_rate": 0.06, "max_leaf_nodes": 31}
LOGISTIC = {"max_iter": 2000, "C": 1.0}
RIDGE_ALPHA = 1.0
BOOTSTRAP_DRAWS = 2000
PERMUTATION_REPEATS = 5

# How many rows of long lists go into the JSON for the pages.
TOP_EPISODES = 25
TOP_FEATURES = 10
