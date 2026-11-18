
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "processed" / "reconstructed_deliveries.csv.gz"
PAR_FILE = ROOT / "reports" / "within_season_par_validation_deliveries.csv.gz"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading reconstructed IPL deliveries...")
df = pd.read_csv(INPUT_FILE, low_memory=False)

print("Loading validated first-innings par benchmarks...")
par = pd.read_csv(PAR_FILE, low_memory=False)

# Normalize merge key data types
for frame in [df, par]:
    frame["match_id"] = pd.to_numeric(
        frame["match_id"], errors="coerce"
    ).astype("Int64")

    frame["season"] = pd.to_numeric(
        frame["season"], errors="coerce"
    ).astype("Int64")

    frame["innings"] = pd.to_numeric(
        frame["innings"], errors="coerce"
    ).astype("Int64")

    frame["legal_balls_before"] = pd.to_numeric(
        frame["legal_balls_before"], errors="coerce"
    ).astype("Int64")

    frame["wickets_in_hand_before"] = pd.to_numeric(
        frame["wickets_in_hand_before"], errors="coerce"
    ).astype("Int64")
    
# ---------------------------------------------------------
# 1. FILTER REGULAR IPL INNINGS
# ---------------------------------------------------------

df["comp_name"] = df["comp_name"].astype(str)

ipl = df[
    df["comp_name"].str.contains("IPL", case=False, na=False)
    & df["innings"].isin([1, 2])
    & (~df["is_super_over"])
].copy()

# Numeric conversion
numeric_columns = [
    "runs",
    "wickets_before_delivery",
    "wickets_in_hand_before",
    "legal_balls_before",
    "balls_remaining_before",
    "required_run_rate_before",
    "runs_before_delivery"
]

for col in numeric_columns:
    ipl[col] = pd.to_numeric(ipl[col], errors="coerce")

# ---------------------------------------------------------
# 2. FIRST INNINGS: ATTACH VALIDATED PAR SCORES
# ---------------------------------------------------------

first = ipl[ipl["innings"] == 1].copy()

par_columns = [
    "match_id",
    "season",
    "innings",
    "legal_balls_before",
    "wickets_in_hand_before",
    "fold",
    "expected_score",
    "benchmark_used",
    "benchmark_deliveries",
    "benchmark_matches"
]

par_columns = [
    col for col in par_columns if col in par.columns
]

# ---------------------------------------------------------
# DELIVERY-LEVEL MERGE
# ---------------------------------------------------------

# Preserve original row order before creating sequence keys.
first = first.reset_index(drop=True)
par_first = par[par_columns].copy().reset_index(drop=True)

# Generate a unique delivery sequence within each match innings.
group_keys = ["match_id", "season", "innings"]

first["_delivery_seq"] = (
    first.groupby(group_keys, sort=False).cumcount()
)

par_first["_delivery_seq"] = (
    par_first.groupby(group_keys, sort=False).cumcount()
)

# Remove the old non-unique matching keys from the merge.
merge_columns = [
    "match_id",
    "season",
    "innings",
    "_delivery_seq"
]

# Keep only benchmark columns from the par file.
benchmark_columns = [
    col for col in [
        "expected_score",
        "benchmark_used",
        "benchmark_deliveries",
        "benchmark_matches"
    ]
    if col in par_first.columns
]

par_first = par_first[
    merge_columns + benchmark_columns
]

first = first.merge(
    par_first,
    on=merge_columns,
    how="left",
    validate="one_to_one",
    sort=False
)

# Verify that no delivery records were duplicated or lost.
if len(first) != len(ipl[ipl["innings"] == 1]):
    raise ValueError(
        "Delivery count changed during par benchmark merge."
    )

print("\nDELIVERY-LEVEL MERGE CHECK")
print("First-innings records:", len(first))
print(
    "Matched benchmark records:",
    int(first["expected_score"].notna().sum())
)
print(
    "Unmatched benchmark records:",
    int(first["expected_score"].isna().sum())
)

first = first.drop(columns=["_delivery_seq"])

first["runs_below_par"] = (
    first["expected_score"] - first["runs_before_delivery"]
)

first["below_par_5_signal"] = (
    first["runs_below_par"] >= 5
)

first["below_par_10_signal"] = (
    first["runs_below_par"] >= 10
)

first["low_wickets_signal"] = (
    first["wickets_in_hand_before"] <= 6
)

first["early_collapse_signal"] = (
    (first["legal_balls_before"] <= 36)
    & (first["wickets_in_hand_before"] <= 7)
)

first["first_pressure_signals"] = (
    first["below_par_5_signal"].astype(int)
    + first["low_wickets_signal"].astype(int)
    + first["early_collapse_signal"].astype(int)
)

first["is_pressure_delivery"] = (
    first["first_pressure_signals"] >= 2
)

first["pressure_severity"] = np.select(
    [
        first["is_pressure_delivery"]
        & (
            first["below_par_10_signal"]
            | (first["wickets_in_hand_before"] <= 3)
        ),

        first["is_pressure_delivery"]
    ],
    [
        "Severe",
        "High"
    ],
    default="Not classified"
)

first["pressure_model"] = "First innings: par + wickets"

# ---------------------------------------------------------
# 3. SECOND INNINGS: CHASE PRESSURE
# ---------------------------------------------------------

second = ipl[ipl["innings"] == 2].copy()

second["high_rrr_signal"] = (
    second["required_run_rate_before"] >= 10
)

second["very_high_rrr_signal"] = (
    second["required_run_rate_before"] >= 15
)

second["low_wickets_signal"] = (
    second["wickets_in_hand_before"] <= 6
)

second["critical_wickets_signal"] = (
    second["wickets_in_hand_before"] <= 3
)

second["low_balls_signal"] = (
    second["balls_remaining_before"] <= 30
)

second["critical_balls_signal"] = (
    second["balls_remaining_before"] <= 12
)

second["second_pressure_signals"] = (
    second["high_rrr_signal"].astype(int)
    + second["low_wickets_signal"].astype(int)
    + second["low_balls_signal"].astype(int)
)

second["is_pressure_delivery"] = (
    second["second_pressure_signals"] >= 2
)

second["pressure_severity"] = np.select(
    [
        second["is_pressure_delivery"]
        & (
            second["very_high_rrr_signal"]
            | second["critical_wickets_signal"]
            | second["critical_balls_signal"]
        ),

        second["is_pressure_delivery"]
    ],
    [
        "Severe",
        "High"
    ],
    default="Not classified"
)

second["pressure_model"] = "Second innings: chase context"

# ---------------------------------------------------------
# 4. COMBINE PRESSURE DATA
# ---------------------------------------------------------

combined = pd.concat(
    [first, second],
    ignore_index=True,
    sort=False
)

combined["is_pressure_delivery"] = (
    combined["is_pressure_delivery"].fillna(False).astype(bool)
)

# ---------------------------------------------------------
# 5. OVERALL SUMMARY
# ---------------------------------------------------------

print("\nUNIFIED PRESSURE SUMMARY")
print("=" * 70)

overall = (
    combined.groupby("innings")
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=("is_pressure_delivery", "sum"),
        high_severity=(
            "pressure_severity",
            lambda x: (x == "High").sum()
        ),
        severe_deliveries=(
            "pressure_severity",
            lambda x: (x == "Severe").sum()
        ),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

overall["pressure_percentage"] = (
    overall["pressure_deliveries"]
    / overall["deliveries"] * 100
)

print(overall.to_string(index=False))

# ---------------------------------------------------------
# 6. PRESSURE BY PHASE
# ---------------------------------------------------------

print("\nPRESSURE BY INNINGS AND PHASE")
print("=" * 70)

phase_summary = (
    combined.groupby(
        ["innings", "innings_phase"],
        dropna=False
    )
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=("is_pressure_delivery", "sum"),
        severe_deliveries=(
            "pressure_severity",
            lambda x: (x == "Severe").sum()
        )
    )
    .reset_index()
)

phase_summary["pressure_percentage"] = (
    phase_summary["pressure_deliveries"]
    / phase_summary["deliveries"] * 100
)

print(phase_summary.to_string(index=False))

# ---------------------------------------------------------
# 7. PRESSURE BY SEASON
# ---------------------------------------------------------

print("\nPRESSURE BY SEASON")
print("=" * 70)

season_summary = (
    combined.groupby(["season", "innings"])
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=("is_pressure_delivery", "sum"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

season_summary["pressure_percentage"] = (
    season_summary["pressure_deliveries"]
    / season_summary["deliveries"] * 100
)

print(season_summary.to_string(index=False))

# ---------------------------------------------------------
# 8. BENCHMARK COVERAGE CHECK
# ---------------------------------------------------------

print("\nFIRST INNINGS PAR COVERAGE")
print("=" * 70)

print("First-innings deliveries:", len(first))
print(
    "Deliveries with supported par:",
    int(first["expected_score"].notna().sum())
)

print(
    "Deliveries without supported par:",
    int(first["expected_score"].isna().sum())
)

# ---------------------------------------------------------
# 9. SAVE REPORTS
# ---------------------------------------------------------

overall.to_csv(
    REPORT_DIR / "unified_pressure_overall.csv",
    index=False
)

phase_summary.to_csv(
    REPORT_DIR / "unified_pressure_by_phase.csv",
    index=False
)

season_summary.to_csv(
    REPORT_DIR / "unified_pressure_by_season.csv",
    index=False
)

combined.to_csv(
    REPORT_DIR / "unified_pressure_deliveries.csv.gz",
    index=False,
    compression="gzip"
)

print("\nUNIFIED PRESSURE CONTEXT COMPLETED")
print("Reports saved in:", REPORT_DIR)
