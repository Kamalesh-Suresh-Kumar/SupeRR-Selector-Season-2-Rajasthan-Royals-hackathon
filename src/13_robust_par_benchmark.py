
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
# 1. FILTER IPL FIRST INNINGS
# ---------------------------------------------------------

df["comp_name"] = df["comp_name"].astype(str)

ipl = df[
    df["comp_name"].str.contains("IPL", case=False, na=False)
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
).copy()

ipl["legal_balls_before"] = (
    ipl["legal_balls_before"].astype(int)
)

ipl["wickets_in_hand_before"] = (
    ipl["wickets_in_hand_before"].astype(int)
)

# Six-ball windows: 0-5, 6-11, 12-17, etc.
ipl["over_segment"] = (
    ipl["legal_balls_before"] // 6
)

# Group wickets in hand into broader categories.
ipl["wickets_band"] = pd.cut(
    ipl["wickets_in_hand_before"],
    bins=[0, 3, 6, 10],
    labels=["1-3", "4-6", "7-10"],
    include_lowest=True
).astype(str)

print("\nIPL FIRST INNINGS DATA")
print("=" * 65)
print("Deliveries:", len(ipl))
print("Matches:", ipl["match_id"].nunique())

# ---------------------------------------------------------
# 2. BUILD BENCHMARK TABLES
# ---------------------------------------------------------

def build_benchmark(data, keys):
    result = (
        data.groupby(keys, observed=True, dropna=False)
        .agg(
            expected_score=("runs_before_delivery", "median"),
            benchmark_deliveries=("runs_before_delivery", "size"),
            benchmark_matches=("match_id", "nunique")
        )
        .reset_index()
    )
    return result


# Level 1: Same phase, over segment and wickets band
b1 = build_benchmark(
    ipl,
    ["innings_phase", "over_segment", "wickets_band"]
)

# Level 2: Same phase and over segment
b2 = build_benchmark(
    ipl,
    ["innings_phase", "over_segment"]
)

# Level 3: Same phase only
b3 = build_benchmark(
    ipl,
    ["innings_phase"]
)

# ---------------------------------------------------------
# 3. APPLY HIERARCHICAL BENCHMARKS
# ---------------------------------------------------------

data = ipl.copy()

data = data.merge(
    b1.rename(columns={
        "expected_score": "score_l1",
        "benchmark_deliveries": "count_l1",
        "benchmark_matches": "matches_l1"
    }),
    on=["innings_phase", "over_segment", "wickets_band"],
    how="left"
)

data = data.merge(
    b2.rename(columns={
        "expected_score": "score_l2",
        "benchmark_deliveries": "count_l2",
        "benchmark_matches": "matches_l2"
    }),
    on=["innings_phase", "over_segment"],
    how="left"
)

data = data.merge(
    b3.rename(columns={
        "expected_score": "score_l3",
        "benchmark_deliveries": "count_l3",
        "benchmark_matches": "matches_l3"
    }),
    on=["innings_phase"],
    how="left"
)

# Minimum support requirements:
# Level 1: at least 30 deliveries and 10 matches
# Level 2: at least 50 deliveries and 15 matches
# Level 3: at least 100 deliveries and 30 matches

valid_l1 = (
    (data["count_l1"] >= 30)
    & (data["matches_l1"] >= 10)
)

valid_l2 = (
    (data["count_l2"] >= 50)
    & (data["matches_l2"] >= 15)
)

valid_l3 = (
    (data["count_l3"] >= 100)
    & (data["matches_l3"] >= 30)
)

data["expected_score"] = np.select(
    [valid_l1, valid_l2, valid_l3],
    [data["score_l1"], data["score_l2"], data["score_l3"]],
    default=np.nan
)

data["benchmark_used"] = np.select(
    [valid_l1, valid_l2, valid_l3],
    [
        "Phase + over segment + wickets band",
        "Phase + over segment",
        "Phase only"
    ],
    default="Unsupported"
)

data["benchmark_deliveries"] = np.select(
    [valid_l1, valid_l2, valid_l3],
    [data["count_l1"], data["count_l2"], data["count_l3"]],
    default=np.nan
)

data["benchmark_matches"] = np.select(
    [valid_l1, valid_l2, valid_l3],
    [data["matches_l1"], data["matches_l2"], data["matches_l3"]],
    default=np.nan
)

# ---------------------------------------------------------
# 4. CALCULATE PAR DIFFERENCE
# ---------------------------------------------------------

data["runs_below_par"] = (
    data["expected_score"] - data["runs_before_delivery"]
)

data["runs_above_par"] = (
    data["runs_before_delivery"] - data["expected_score"]
)

data["five_or_more_below_par"] = (
    data["runs_below_par"] >= 5
)

data["ten_or_more_below_par"] = (
    data["runs_below_par"] >= 10
)

# ---------------------------------------------------------
# 5. BENCHMARK SUPPORT SUMMARY
# ---------------------------------------------------------

print("\nBENCHMARK SUPPORT")
print("=" * 65)

support = (
    data.groupby("benchmark_used", dropna=False)
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        average_benchmark_deliveries=("benchmark_deliveries", "mean"),
        average_benchmark_matches=("benchmark_matches", "mean")
    )
    .reset_index()
)

support["percentage"] = (
    support["deliveries"] / len(data) * 100
)

print(support.to_string(index=False))

# ---------------------------------------------------------
# 6. PAR SCORE SUMMARY BY PHASE
# ---------------------------------------------------------

supported = data[data["benchmark_used"] != "Unsupported"].copy()

summary = (
    supported.groupby("innings_phase")
    .agg(
        supported_deliveries=("match_id", "size"),
        average_actual_score=("runs_before_delivery", "mean"),
        average_expected_score=("expected_score", "mean"),
        average_runs_below_par=("runs_below_par", "mean"),
        five_below_par=("five_or_more_below_par", "sum"),
        ten_below_par=("ten_or_more_below_par", "sum")
    )
    .reset_index()
)

summary["five_below_par_percentage"] = (
    summary["five_below_par"]
    / summary["supported_deliveries"] * 100
)

summary["ten_below_par_percentage"] = (
    summary["ten_below_par"]
    / summary["supported_deliveries"] * 100
)

print("\nROBUST PAR SCORE SUMMARY")
print("=" * 65)
print(summary.to_string(index=False))

# ---------------------------------------------------------
# 7. CHECK BENCHMARK DISTRIBUTION BY OVER SEGMENT
# ---------------------------------------------------------

segment_summary = (
    data.groupby(
        ["innings_phase", "over_segment", "benchmark_used"],
        dropna=False
    )
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

print("\nUNSUPPORTED DELIVERY COUNT")
print("=" * 65)
print(
    "Unsupported:",
    int((data["benchmark_used"] == "Unsupported").sum())
)

print("\nBENCHMARK LEVEL COUNTS")
print("=" * 65)
print(data["benchmark_used"].value_counts(dropna=False).to_string())

# ---------------------------------------------------------
# 8. SAVE REPORTS
# ---------------------------------------------------------

support.to_csv(
    REPORT_DIR / "robust_par_benchmark_support.csv",
    index=False
)

summary.to_csv(
    REPORT_DIR / "robust_par_score_summary.csv",
    index=False
)

segment_summary.to_csv(
    REPORT_DIR / "robust_par_segment_summary.csv",
    index=False
)

data.to_csv(
    REPORT_DIR / "robust_par_delivery_audit.csv.gz",
    index=False,
    compression="gzip"
)

print("\nROBUST PAR BENCHMARK AUDIT COMPLETED")
print("Reports saved in:", REPORT_DIR)
