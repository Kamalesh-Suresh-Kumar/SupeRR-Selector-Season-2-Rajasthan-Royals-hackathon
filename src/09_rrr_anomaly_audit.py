
import pandas as pd
from pathlib import Path

# =====================================================
# 1. PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "reconstructed_deliveries.csv.gz"
)

REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# 2. LOAD IPL DATA
# =====================================================

print("\nLoading reconstructed data...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

df["comp_name"] = df["comp_name"].fillna("").astype(str)

df = df[
    df["comp_name"].str.contains("IPL", case=False, na=False)
].copy()

# Only regular second innings.

df = df[
    pd.to_numeric(df["innings"], errors="coerce") == 2
].copy()

print("IPL second-innings deliveries:", len(df))

# =====================================================
# 3. CHECK REQUIRED COLUMNS
# =====================================================

columns = [
    "match_id",
    "innings",
    "season",
    "batting_team_name",
    "bowling_team_name",
    "innings_ball_num",
    "overid",
    "over_ball_num",
    "runs_before_delivery",
    "cumulative_runs",
    "target",
    "runs_required_before",
    "scheduled_balls",
    "legal_balls_before",
    "balls_remaining_before",
    "required_run_rate_before",
    "wickets_before_delivery",
    "is_high_pressure_delivery"
]

missing = [c for c in columns if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

# =====================================================
# 4. NUMERIC CONVERSION
# =====================================================

numeric_columns = [
    "runs_before_delivery",
    "cumulative_runs",
    "target",
    "runs_required_before",
    "scheduled_balls",
    "legal_balls_before",
    "balls_remaining_before",
    "required_run_rate_before",
    "wickets_before_delivery"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# =====================================================
# 5. IDENTIFY EXTREME REQUIRED RUN RATES
# =====================================================

print("\n" + "=" * 65)
print("EXTREME REQUIRED RUN RATE AUDIT")
print("=" * 65)

print("\nRRR distribution:")

print(
    df["required_run_rate_before"]
    .describe(
        percentiles=[0.50, 0.75, 0.90, 0.95, 0.99]
    )
)

extreme = df[
    df["required_run_rate_before"] > 36
].copy()

extreme = extreme.sort_values(
    "required_run_rate_before",
    ascending=False
)

print("\nDeliveries with RRR greater than 36:")

print("Count:", len(extreme))

display_columns = [
    "match_id",
    "season",
    "batting_team_name",
    "bowling_team_name",
    "innings_ball_num",
    "overid",
    "over_ball_num",
    "runs_before_delivery",
    "target",
    "runs_required_before",
    "scheduled_balls",
    "legal_balls_before",
    "balls_remaining_before",
    "required_run_rate_before",
    "wickets_before_delivery"
]

print(
    extreme[display_columns]
    .head(30)
    .to_string(index=False)
)

# =====================================================
# 6. CHECK TARGET AND BALLS REMAINING
# =====================================================

print("\n" + "=" * 65)
print("TARGET AND BALLS REMAINING VALIDATION")
print("=" * 65)

df["calculated_runs_required"] = (
    df["target"] - df["runs_before_delivery"]
)

df["calculated_rrr"] = (
    df["calculated_runs_required"]
    / df["balls_remaining_before"]
) * 6

df.loc[
    df["balls_remaining_before"] <= 0,
    "calculated_rrr"
] = float("nan")

df["rrr_difference"] = (
    df["required_run_rate_before"]
    - df["calculated_rrr"]
).abs()

print(
    "Rows with inconsistent runs required:",
    int(
        (
            df["runs_required_before"]
            != df["calculated_runs_required"].clip(lower=0)
        ).sum()
    )
)

print(
    "Rows with RRR calculation difference > 0.01:",
    int((df["rrr_difference"] > 0.01).sum())
)

# =====================================================
# 7. INNINGS WITH EXTREME RRR
# =====================================================

print("\n" + "=" * 65)
print("INNINGS CONTAINING EXTREME RRR")
print("=" * 65)

extreme_matches = extreme["match_id"].dropna().unique()

innings_columns = [
    "match_id",
    "season",
    "batting_team_name",
    "bowling_team_name",
    "target",
    "scheduled_balls",
    "innings_ball_num",
    "runs_before_delivery",
    "runs_required_before",
    "balls_remaining_before",
    "required_run_rate_before"
]

innings_details = df[
    df["match_id"].isin(extreme_matches)
][innings_columns].copy()

print(
    innings_details.sort_values(
        ["match_id", "innings_ball_num"]
    ).to_string(index=False)
)

# =====================================================
# 8. SAVE REPORTS
# =====================================================

extreme.to_csv(
    REPORT_DIR / "extreme_rrr_deliveries.csv",
    index=False
)

innings_details.to_csv(
    REPORT_DIR / "extreme_rrr_innings_details.csv",
    index=False
)

print("\n" + "=" * 65)
print("RRR ANOMALY AUDIT COMPLETED")
print("=" * 65)

print("Extreme deliveries:", len(extreme))

print(
    "Reports saved:",
    REPORT_DIR
)
