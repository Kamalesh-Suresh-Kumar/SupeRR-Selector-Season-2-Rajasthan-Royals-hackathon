
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "data" / "processed" / "reconstructed_deliveries.csv.gz"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

FOLDS = 5

MIN_L1_DELIVERIES = 30
MIN_L1_MATCHES = 10

MIN_L2_DELIVERIES = 50
MIN_L2_MATCHES = 15

MIN_L3_DELIVERIES = 100
MIN_L3_MATCHES = 30

print("Loading IPL first-innings deliveries...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

data = df[
    df["comp_name"].astype(str).str.contains(
        "IPL", case=False, na=False
    )
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
        "season",
        "match_id"
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

print("\nDATASET")
print("=" * 65)
print("Deliveries:", len(data))
print("Matches:", data["match_id"].nunique())
print("Seasons:", sorted(data["season"].unique()))


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


def evaluate_fold(train, test, season, fold):

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

    result["season"] = season
    result["fold"] = fold

    return result


# ---------------------------------------------------------
# FIVE-FOLD VALIDATION WITHIN EACH SEASON
# ---------------------------------------------------------

all_results = []

for season in sorted(data["season"].unique()):

    season_data = data[data["season"] == season].copy()

    match_ids = np.array(sorted(season_data["match_id"].unique()))

    if len(match_ids) < FOLDS:
        print(f"Skipping season {season}: insufficient matches.")
        continue

    match_folds = np.array_split(match_ids, FOLDS)

    print(f"\nSeason: {season}")
    print("Matches:", len(match_ids))

    for fold_number, test_match_ids in enumerate(match_folds, start=1):

        test_ids = set(test_match_ids.tolist())

        train = season_data[
            ~season_data["match_id"].isin(test_ids)
        ].copy()

        test = season_data[
            season_data["match_id"].isin(test_ids)
        ].copy()

        print(
            f"Fold {fold_number}: "
            f"train matches={train['match_id'].nunique()}, "
            f"test matches={test['match_id'].nunique()}"
        )

        if train.empty or test.empty:
            continue

        result = evaluate_fold(
            train,
            test,
            season,
            fold_number
        )

        all_results.append(result)


if not all_results:
    raise ValueError("No validation results were generated.")

validation = pd.concat(all_results, ignore_index=True)

validation["supported"] = (
    validation["benchmark_used"] != "Unsupported"
)

# ---------------------------------------------------------
# SUMMARY BY SEASON
# ---------------------------------------------------------

season_summary = (
    validation.groupby("season")
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        supported_deliveries=("supported", "sum"),
        average_actual_score=("runs_before_delivery", "mean"),
        average_expected_score=("expected_score", "mean"),
        average_runs_below_par=("runs_below_par", "mean")
    )
    .reset_index()
)

season_summary["coverage_percentage"] = (
    season_summary["supported_deliveries"]
    / season_summary["deliveries"] * 100
)

print("\nWITHIN-SEASON VALIDATION")
print("=" * 75)
print(season_summary.to_string(index=False))

# ---------------------------------------------------------
# BENCHMARK LEVEL DISTRIBUTION
# ---------------------------------------------------------

support = (
    validation.groupby(
        ["season", "benchmark_used"],
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
# PHASE-LEVEL VALIDATION
# ---------------------------------------------------------

supported = validation[validation["supported"]].copy()

phase_summary = (
    supported.groupby(["season", "innings_phase"])
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

print("\nPHASE-LEVEL VALIDATION")
print("=" * 75)
print(phase_summary.to_string(index=False))

# ---------------------------------------------------------
# SAVE REPORTS
# ---------------------------------------------------------

season_summary.to_csv(
    REPORT_DIR / "within_season_par_validation_summary.csv",
    index=False
)

support.to_csv(
    REPORT_DIR / "within_season_par_validation_support.csv",
    index=False
)

phase_summary.to_csv(
    REPORT_DIR / "within_season_par_validation_by_phase.csv",
    index=False
)

validation.to_csv(
    REPORT_DIR / "within_season_par_validation_deliveries.csv.gz",
    index=False,
    compression="gzip"
)

print("\nWITHIN-SEASON PAR VALIDATION COMPLETED")
print("Reports saved in:", REPORT_DIR)
