
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "processed" / "reconstructed_deliveries.csv.gz"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading IPL first-innings data...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

df["comp_name"] = df["comp_name"].astype(str)

data = df[
    df["comp_name"].str.contains("IPL", case=False, na=False)
    & (df["innings"] == 1)
    & (~df["is_super_over"])
].copy()

for col in [
    "runs_before_delivery",
    "legal_balls_before",
    "wickets_in_hand_before",
    "season"
]:
    data[col] = pd.to_numeric(data[col], errors="coerce")

data = data.dropna(
    subset=[
        "runs_before_delivery",
        "legal_balls_before",
        "wickets_in_hand_before",
        "season"
    ]
).copy()

data["season"] = data["season"].astype(int)
data["legal_balls_before"] = data["legal_balls_before"].astype(int)
data["wickets_in_hand_before"] = (
    data["wickets_in_hand_before"].astype(int)
)

data["over_segment"] = data["legal_balls_before"] // 6

data["wickets_band"] = pd.cut(
    data["wickets_in_hand_before"],
    bins=[0, 3, 6, 10],
    labels=["1-3", "4-6", "7-10"],
    include_lowest=True
).astype(str)

seasons = sorted(data["season"].unique())

print("\nAVAILABLE SEASONS:", seasons)

MIN_L1_DELIVERIES = 30
MIN_L1_MATCHES = 10

MIN_L2_DELIVERIES = 50
MIN_L2_MATCHES = 15

MIN_L3_DELIVERIES = 100
MIN_L3_MATCHES = 30


def build_benchmark(train, keys, prefix):

    return (
        train.groupby(keys, observed=True, dropna=False)
        .agg(
            expected=("runs_before_delivery", "median"),
            deliveries=("runs_before_delivery", "size"),
            matches=("match_id", "nunique")
        )
        .reset_index()
        .rename(columns={
            "expected": f"{prefix}_expected",
            "deliveries": f"{prefix}_deliveries",
            "matches": f"{prefix}_matches"
        })
    )


def evaluate_season(train, test, season):

    b1 = build_benchmark(
        train,
        ["innings_phase", "over_segment", "wickets_band"],
        "l1"
    )

    b2 = build_benchmark(
        train,
        ["innings_phase", "over_segment"],
        "l2"
    )

    b3 = build_benchmark(
        train,
        ["innings_phase"],
        "l3"
    )

    result = test.merge(
        b1,
        on=["innings_phase", "over_segment", "wickets_band"],
        how="left"
    )

    result = result.merge(
        b2,
        on=["innings_phase", "over_segment"],
        how="left"
    )

    result = result.merge(
        b3,
        on=["innings_phase"],
        how="left"
    )

    valid1 = (
        (result["l1_deliveries"] >= MIN_L1_DELIVERIES)
        & (result["l1_matches"] >= MIN_L1_MATCHES)
    )

    valid2 = (
        (result["l2_deliveries"] >= MIN_L2_DELIVERIES)
        & (result["l2_matches"] >= MIN_L2_MATCHES)
    )

    valid3 = (
        (result["l3_deliveries"] >= MIN_L3_DELIVERIES)
        & (result["l3_matches"] >= MIN_L3_MATCHES)
    )

    result["expected_score"] = np.select(
        [valid1, valid2, valid3],
        [
            result["l1_expected"],
            result["l2_expected"],
            result["l3_expected"]
        ],
        default=np.nan
    )

    result["benchmark_used"] = np.select(
        [valid1, valid2, valid3],
        [
            "Phase + over + wickets band",
            "Phase + over",
            "Phase only"
        ],
        default="Unsupported"
    )

    result["runs_below_par"] = (
        result["expected_score"] - result["runs_before_delivery"]
    )

    result["held_out_season"] = season

    return result


# ---------------------------------------------------------
# CHRONOLOGICAL VALIDATION
# ---------------------------------------------------------

all_results = []
season_summaries = []

for season in seasons:

    train = data[data["season"] < season].copy()
    test = data[data["season"] == season].copy()

    print(f"\nEvaluating season: {season}")
    print("Training seasons:", sorted(train["season"].unique()))
    print("Training matches:", train["match_id"].nunique())
    print("Test matches:", test["match_id"].nunique())

    if train.empty:
        print("No previous season available. Skipping benchmark.")
        continue

    result = evaluate_season(train, test, season)

    all_results.append(result)

    result["supported"] = (
        result["benchmark_used"] != "Unsupported"
    )

    supported = result[result["supported"]].copy()

    coverage = (
        len(supported) / len(result) * 100
        if len(result) else 0
    )

    season_summaries.append({
        "season": season,
        "training_seasons": ", ".join(
            map(str, sorted(train["season"].unique()))
        ),
        "training_matches": train["match_id"].nunique(),
        "test_matches": test["match_id"].nunique(),
        "test_deliveries": len(test),
        "supported_deliveries": len(supported),
        "coverage_percentage": coverage,
        "average_actual_score": (
            supported["runs_before_delivery"].mean()
            if len(supported) else np.nan
        ),
        "average_expected_score": (
            supported["expected_score"].mean()
            if len(supported) else np.nan
        ),
        "average_runs_below_par": (
            supported["runs_below_par"].mean()
            if len(supported) else np.nan
        )
    })

# ---------------------------------------------------------
# COMBINE RESULTS
# ---------------------------------------------------------

if not all_results:
    raise ValueError("No season could be evaluated.")

validation = pd.concat(all_results, ignore_index=True)

summary = pd.DataFrame(season_summaries)

print("\nCHRONOLOGICAL VALIDATION BY SEASON")
print("=" * 75)
print(summary.to_string(index=False))

# ---------------------------------------------------------
# BENCHMARK LEVEL DISTRIBUTION
# ---------------------------------------------------------

support = (
    validation.groupby(
        ["held_out_season", "benchmark_used"],
        dropna=False
    )
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

print("\nBENCHMARK LEVEL DISTRIBUTION")
print("=" * 75)
print(support.to_string(index=False))

# ---------------------------------------------------------
# PHASE-LEVEL RESULTS
# ---------------------------------------------------------

supported = validation[
    validation["benchmark_used"] != "Unsupported"
].copy()

phase_summary = (
    supported.groupby(
        ["held_out_season", "innings_phase"]
    )
    .agg(
        deliveries=("match_id", "size"),
        average_actual_score=("runs_before_delivery", "mean"),
        average_expected_score=("expected_score", "mean"),
        average_runs_below_par=("runs_below_par", "mean"),
        five_below_par=(
            "runs_below_par",
            lambda x: (x >= 5).sum()
        ),
        ten_below_par=(
            "runs_below_par",
            lambda x: (x >= 10).sum()
        )
    )
    .reset_index()
)

print("\nCHRONOLOGICAL VALIDATION BY PHASE")
print("=" * 75)
print(phase_summary.to_string(index=False))

# ---------------------------------------------------------
# SAVE REPORTS
# ---------------------------------------------------------

summary.to_csv(
    REPORT_DIR / "chronological_par_validation_summary.csv",
    index=False
)

support.to_csv(
    REPORT_DIR / "chronological_par_validation_support.csv",
    index=False
)

phase_summary.to_csv(
    REPORT_DIR / "chronological_par_validation_by_phase.csv",
    index=False
)

validation.to_csv(
    REPORT_DIR / "chronological_par_validation_deliveries.csv.gz",
    index=False,
    compression="gzip"
)

print("\nCHRONOLOGICAL PAR VALIDATION COMPLETED")
print("Reports saved in:", REPORT_DIR)
