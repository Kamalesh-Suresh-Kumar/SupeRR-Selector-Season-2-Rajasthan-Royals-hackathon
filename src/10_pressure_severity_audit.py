
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR / "data" / "processed"
    / "reconstructed_deliveries.csv.gz"
)

REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(exist_ok=True)

print("Loading reconstructed deliveries...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

# IPL only
df = df[
    df["comp_name"].astype(str).str.contains(
        "IPL", case=False, na=False
    )
].copy()

# Exclude Super Overs
df = df[
    pd.to_numeric(df["innings"], errors="coerce") <= 2
].copy()

# Numeric conversions
cols = [
    "innings",
    "required_run_rate_before",
    "wickets_before_delivery",
    "balls_remaining_before",
    "is_high_pressure_delivery"
]

for col in cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# =====================================================
# 1. CLASSIFY RRR SEVERITY
# =====================================================

conditions = [
    df["required_run_rate_before"] < 8,
    df["required_run_rate_before"].between(8, 10, inclusive="left"),
    df["required_run_rate_before"].between(10, 15, inclusive="left"),
    df["required_run_rate_before"].between(15, 24, inclusive="left"),
    df["required_run_rate_before"] >= 24
]

labels = [
    "Manageable",
    "Elevated",
    "High",
    "Very High",
    "Extreme"
]

df["rrr_severity"] = pd.NA

chase = df["innings"] == 2

df.loc[chase, "rrr_severity"] = pd.cut(
    df.loc[chase, "required_run_rate_before"],
    bins=[-float("inf"), 8, 10, 15, 24, float("inf")],
    labels=labels,
    right=False
).astype(str)

# =====================================================
# 2. RRR SEVERITY DISTRIBUTION
# =====================================================

print("\nRRR SEVERITY DISTRIBUTION")
print("=" * 65)

severity = (
    df.loc[chase]
    .groupby("rrr_severity", observed=False)
    .agg(
        deliveries=("match_id", "size"),
        average_wickets_lost=("wickets_before_delivery", "mean"),
        average_balls_remaining=("balls_remaining_before", "mean")
    )
    .reset_index()
)

severity["percentage"] = (
    severity["deliveries"] / chase.sum() * 100
)

print(severity.to_string(index=False))

# =====================================================
# 3. EXTREME RRR WITH WICKETS
# =====================================================

print("\nEXTREME RRR AND WICKETS")
print("=" * 65)

extreme = df[
    chase
    & (df["required_run_rate_before"] >= 24)
]

print("Extreme pressure deliveries:", len(extreme))

print(
    "Average wickets lost:",
    round(extreme["wickets_before_delivery"].mean(), 2)
)

print(
    "Average balls remaining:",
    round(extreme["balls_remaining_before"].mean(), 2)
)

# =====================================================
# 4. FIRST INNINGS PRESSURE
# =====================================================

first = df[df["innings"] == 1]

print("\nFIRST INNINGS PRESSURE")
print("=" * 65)

print("First innings deliveries:", len(first))

print(
    first.groupby("innings_phase", dropna=False)
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=("is_high_pressure_delivery", "sum")
    )
    .to_string()
)

# =====================================================
# 5. SAVE REPORT
# =====================================================

severity.to_csv(
    REPORT_DIR / "rrr_severity_distribution.csv",
    index=False
)

extreme.to_csv(
    REPORT_DIR / "extreme_pressure_deliveries.csv",
    index=False
)

print("\nPRESSURE SEVERITY AUDIT COMPLETED")
print("Reports saved in:", REPORT_DIR)
