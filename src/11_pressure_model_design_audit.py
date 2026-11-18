
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "processed" / "reconstructed_deliveries.csv.gz"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading reconstructed deliveries...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

# ---------------------------------------------------------
# 1. FILTER IPL REGULAR INNINGS
# ---------------------------------------------------------

df["comp_name"] = df["comp_name"].astype(str)

ipl = df[
    df["comp_name"].str.contains("IPL", case=False, na=False)
    & df["innings"].isin([1, 2])
    & (~df["is_super_over"])
].copy()

print("\nIPL DATASET")
print("=" * 65)
print("Total IPL delivery records:", len(ipl))
print("Matches:", ipl["match_id"].nunique())

# Ensure numerical fields are numeric
numeric_columns = [
    "runs",
    "wickets_before_delivery",
    "wickets_in_hand_before",
    "legal_balls_before",
    "balls_remaining_before",
    "current_run_rate_before",
    "required_run_rate_before"
]

for col in numeric_columns:
    ipl[col] = pd.to_numeric(ipl[col], errors="coerce")

# ---------------------------------------------------------
# 2. FIRST INNINGS: HISTORICAL SCORING BENCHMARK
# ---------------------------------------------------------

first = ipl[ipl["innings"] == 1].copy()

# Avoid comparing the first few deliveries, where current
# run rate is not yet a meaningful indicator.
first = first[first["legal_balls_before"] >= 6].copy()

# Group by phase and wickets in hand.
# This compares similar match situations.
benchmark = (
    first.groupby(
        ["innings_phase", "wickets_in_hand_before"],
        dropna=False
    )
    .agg(
        benchmark_deliveries=("current_run_rate_before", "count"),
        expected_run_rate=("current_run_rate_before", "mean"),
        median_run_rate=("current_run_rate_before", "median")
    )
    .reset_index()
)

# Use phase-only benchmark when a detailed group has
# insufficient observations.
phase_benchmark = (
    first.groupby("innings_phase")
    .agg(
        phase_deliveries=("current_run_rate_before", "count"),
        phase_expected_run_rate=("current_run_rate_before", "mean")
    )
    .reset_index()
)

first = first.merge(
    benchmark,
    on=["innings_phase", "wickets_in_hand_before"],
    how="left"
)

first = first.merge(
    phase_benchmark,
    on="innings_phase",
    how="left"
)

MIN_GROUP_SIZE = 100

first["benchmark_used"] = np.where(
    first["benchmark_deliveries"] >= MIN_GROUP_SIZE,
    "Phase + wickets in hand",
    "Phase only"
)

first["expected_run_rate"] = np.where(
    first["benchmark_deliveries"] >= MIN_GROUP_SIZE,
    first["expected_run_rate"],
    first["phase_expected_run_rate"]
)

first["below_expected_rate"] = (
    first["current_run_rate_before"]
    < first["expected_run_rate"] * 0.80
)

# Provisional first-innings pressure indicators
first["low_wickets_signal"] = (
    first["wickets_in_hand_before"] <= 7
)

first["severe_wickets_signal"] = (
    first["wickets_in_hand_before"] <= 5
)

first["below_par_signal"] = first["below_expected_rate"]

first["death_phase_signal"] = (
    first["innings_phase"] == "Death"
)

first["early_collapse_signal"] = (
    (first["legal_balls_before"] <= 36)
    & (first["wickets_in_hand_before"] <= 7)
)

first["first_innings_pressure_signals"] = (
    first["low_wickets_signal"].astype(int)
    + first["below_par_signal"].astype(int)
    + first["death_phase_signal"].astype(int)
    + first["early_collapse_signal"].astype(int)
)

# This is an audit label, not a final player-ranking label.
first["provisional_first_innings_pressure"] = (
    first["first_innings_pressure_signals"] >= 2
)

# ---------------------------------------------------------
# 3. SECOND INNINGS: CHASE PRESSURE INDICATORS
# ---------------------------------------------------------

second = ipl[ipl["innings"] == 2].copy()

second["high_rrr_signal"] = (
    second["required_run_rate_before"] >= 10
)

second["very_high_rrr_signal"] = (
    second["required_run_rate_before"] >= 15
)

second["extreme_rrr_signal"] = (
    second["required_run_rate_before"] >= 24
)

second["low_wickets_signal"] = (
    second["wickets_in_hand_before"] <= 5
)

second["low_balls_signal"] = (
    second["balls_remaining_before"] <= 30
)

second["death_phase_signal"] = (
    second["innings_phase"] == "Death"
)

second["second_innings_pressure_signals"] = (
    second["high_rrr_signal"].astype(int)
    + second["low_wickets_signal"].astype(int)
    + second["low_balls_signal"].astype(int)
    + second["death_phase_signal"].astype(int)
)

second["provisional_second_innings_pressure"] = (
    second["second_innings_pressure_signals"] >= 2
)

# ---------------------------------------------------------
# 4. FIRST INNINGS SUMMARY
# ---------------------------------------------------------

print("\nFIRST INNINGS PRESSURE AUDIT")
print("=" * 65)

first_summary = (
    first.groupby("innings_phase")
    .agg(
        deliveries=("match_id", "size"),
        average_current_run_rate=("current_run_rate_before", "mean"),
        average_expected_run_rate=("expected_run_rate", "mean"),
        below_par_deliveries=("below_par_signal", "sum"),
        low_wicket_deliveries=("low_wickets_signal", "sum"),
        early_collapse_deliveries=("early_collapse_signal", "sum"),
        provisional_pressure_deliveries=(
            "provisional_first_innings_pressure", "sum"
        )
    )
    .reset_index()
)

first_summary["pressure_percentage"] = (
    first_summary["provisional_pressure_deliveries"]
    / first_summary["deliveries"] * 100
)

print(first_summary.to_string(index=False))

# ---------------------------------------------------------
# 5. BENCHMARK QUALITY AUDIT
# ---------------------------------------------------------

print("\nFIRST INNINGS BENCHMARK QUALITY")
print("=" * 65)

benchmark_quality = (
    first.groupby(["innings_phase", "benchmark_used"])
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        average_expected_run_rate=("expected_run_rate", "mean")
    )
    .reset_index()
)

print(benchmark_quality.to_string(index=False))

# ---------------------------------------------------------
# 6. SECOND INNINGS SUMMARY
# ---------------------------------------------------------

print("\nSECOND INNINGS PRESSURE AUDIT")
print("=" * 65)

second_summary = (
    second.groupby("innings_phase")
    .agg(
        deliveries=("match_id", "size"),
        high_rrr=("high_rrr_signal", "sum"),
        very_high_rrr=("very_high_rrr_signal", "sum"),
        low_wickets=("low_wickets_signal", "sum"),
        low_balls=("low_balls_signal", "sum"),
        provisional_pressure=(
            "provisional_second_innings_pressure", "sum"
        )
    )
    .reset_index()
)

second_summary["pressure_percentage"] = (
    second_summary["provisional_pressure"]
    / second_summary["deliveries"] * 100
)

print(second_summary.to_string(index=False))

# ---------------------------------------------------------
# 7. COMPARE OLD AND NEW PRESSURE LABELS
# ---------------------------------------------------------

first_old = int(first["is_high_pressure_delivery"].sum())
first_new = int(first["provisional_first_innings_pressure"].sum())

second_old = int(second["is_high_pressure_delivery"].sum())
second_new = int(second["provisional_second_innings_pressure"].sum())

print("\nOLD VS PROVISIONAL PRESSURE LABELS")
print("=" * 65)

print("First innings:")
print("Old pressure deliveries:", first_old)
print("New provisional deliveries:", first_new)

print("\nSecond innings:")
print("Old pressure deliveries:", second_old)
print("New provisional deliveries:", second_new)

# ---------------------------------------------------------
# 8. SAVE REPORTS
# ---------------------------------------------------------

first_summary.to_csv(
    REPORT_DIR / "first_innings_pressure_model_audit.csv",
    index=False
)

second_summary.to_csv(
    REPORT_DIR / "second_innings_pressure_model_audit.csv",
    index=False
)

benchmark_quality.to_csv(
    REPORT_DIR / "first_innings_benchmark_quality.csv",
    index=False
)

first.to_csv(
    REPORT_DIR / "first_innings_pressure_audit_deliveries.csv.gz",
    index=False,
    compression="gzip"
)

second.to_csv(
    REPORT_DIR / "second_innings_pressure_audit_deliveries.csv.gz",
    index=False,
    compression="gzip"
)

print("\nPRESSURE MODEL DESIGN AUDIT COMPLETED")
print("Reports saved in:", REPORT_DIR)
