
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
# 1. FILTER REGULAR IPL FIRST INNINGS
# ---------------------------------------------------------

ipl = df[
    df["comp_name"].astype(str).str.contains(
        "IPL", case=False, na=False
    )
    & (df["innings"] == 1)
    & (~df["is_super_over"])
].copy()

for col in [
    "runs_before_delivery",
    "legal_balls_before",
    "wickets_in_hand_before"
]:
    ipl[col] = pd.to_numeric(ipl[col], errors="coerce")

ipl = ipl.dropna(
    subset=[
        "runs_before_delivery",
        "legal_balls_before",
        "wickets_in_hand_before"
    ]
)

ipl["legal_balls_before"] = (
    ipl["legal_balls_before"].astype(int)
)

ipl["wickets_in_hand_before"] = (
    ipl["wickets_in_hand_before"].astype(int)
)

print("\nDATASET")
print("=" * 65)
print("First innings deliveries:", len(ipl))
print("Matches:", ipl["match_id"].nunique())

# ---------------------------------------------------------
# 2. BUILD HISTORICAL PAR SCORE
# ---------------------------------------------------------

# Compare deliveries at the same legal-ball number
# and similar wickets in hand.

benchmark = (
    ipl.groupby(
        ["legal_balls_before", "wickets_in_hand_before"]
    )
    .agg(
        sample_deliveries=("runs_before_delivery", "size"),
        sample_matches=("match_id", "nunique"),
        expected_score=("runs_before_delivery", "median"),
        average_score=("runs_before_delivery", "mean")
    )
    .reset_index()
)

# Fallback benchmark: same legal-ball number,
# irrespective of wickets in hand.

ball_benchmark = (
    ipl.groupby("legal_balls_before")
    .agg(
        ball_sample_deliveries=("runs_before_delivery", "size"),
        ball_sample_matches=("match_id", "nunique"),
        ball_expected_score=("runs_before_delivery", "median")
    )
    .reset_index()
)

benchmark = benchmark.merge(
    ball_benchmark,
    on="legal_balls_before",
    how="left"
)

MIN_GROUP_SIZE = 30

benchmark["benchmark_used"] = np.where(
    benchmark["sample_deliveries"] >= MIN_GROUP_SIZE,
    "Ball + wickets in hand",
    "Ball only"
)

benchmark["final_expected_score"] = np.where(
    benchmark["sample_deliveries"] >= MIN_GROUP_SIZE,
    benchmark["expected_score"],
    benchmark["ball_expected_score"]
)

# ---------------------------------------------------------
# 3. APPLY HISTORICAL PAR TO EACH DELIVERY
# ---------------------------------------------------------

ipl = ipl.merge(
    benchmark[
        [
            "legal_balls_before",
            "wickets_in_hand_before",
            "sample_deliveries",
            "sample_matches",
            "final_expected_score",
            "benchmark_used"
        ]
    ],
    on=[
        "legal_balls_before",
        "wickets_in_hand_before"
    ],
    how="left"
)

ipl["runs_below_par"] = (
    ipl["final_expected_score"]
    - ipl["runs_before_delivery"]
)

ipl["runs_above_par"] = (
    ipl["runs_before_delivery"]
    - ipl["final_expected_score"]
)

# Provisional diagnostic bands.
ipl["par_difference_band"] = pd.cut(
    ipl["runs_below_par"],
    bins=[-np.inf, -5, 0, 5, 10, np.inf],
    labels=[
        "Above par by more than 5",
        "Near or above par",
        "0-5 below par",
        "5-10 below par",
        "More than 10 below par"
    ]
)

# ---------------------------------------------------------
# 4. SUMMARY BY PHASE
# ---------------------------------------------------------

summary = (
    ipl.groupby("innings_phase", observed=False)
    .agg(
        deliveries=("match_id", "size"),
        average_actual_score=("runs_before_delivery", "mean"),
        average_expected_score=("final_expected_score", "mean"),
        average_runs_below_par=("runs_below_par", "mean"),
        deliveries_5_below_par=(
            "runs_below_par",
            lambda x: (x >= 5).sum()
        ),
        deliveries_10_below_par=(
            "runs_below_par",
            lambda x: (x >= 10).sum()
        )
    )
    .reset_index()
)

summary["five_below_par_percentage"] = (
    summary["deliveries_5_below_par"]
    / summary["deliveries"] * 100
)

summary["ten_below_par_percentage"] = (
    summary["deliveries_10_below_par"]
    / summary["deliveries"] * 100
)

print("\nHISTORICAL PAR SCORE BY PHASE")
print("=" * 65)
print(summary.to_string(index=False))

# ---------------------------------------------------------
# 5. BENCHMARK SAMPLE QUALITY
# ---------------------------------------------------------

quality = (
    benchmark.groupby("benchmark_used")
    .agg(
        benchmark_groups=("legal_balls_before", "size"),
        minimum_group_deliveries=("sample_deliveries", "min"),
        median_group_deliveries=("sample_deliveries", "median"),
        maximum_group_deliveries=("sample_deliveries", "max")
    )
    .reset_index()
)

print("\nBENCHMARK SAMPLE QUALITY")
print("=" * 65)
print(quality.to_string(index=False))

print("\nSMALL-SAMPLE BENCHMARK GROUPS")
print("=" * 65)

small_groups = benchmark[
    benchmark["sample_deliveries"] < MIN_GROUP_SIZE
]

print("Small groups:", len(small_groups))
print("Fallback groups:", len(small_groups))

# ---------------------------------------------------------
# 6. SAVE REPORTS
# ---------------------------------------------------------

summary.to_csv(
    REPORT_DIR / "first_innings_par_score_summary.csv",
    index=False
)

benchmark.to_csv(
    REPORT_DIR / "first_innings_par_score_benchmarks.csv",
    index=False
)

ipl.to_csv(
    REPORT_DIR / "first_innings_par_score_audit.csv.gz",
    index=False,
    compression="gzip"
)

print("\nFIRST INNINGS PAR SCORE AUDIT COMPLETED")
print("Reports saved in:", REPORT_DIR)
