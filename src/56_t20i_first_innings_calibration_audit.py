
from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

INPUT_FILE = REPORTS / "t20i_first_innings_par_deliveries.csv.gz"

print("\n" + "=" * 78)
print("STEP 56: T20I FIRST-INNINGS BENCHMARK CALIBRATION AUDIT")
print("=" * 78)

df = pd.read_csv(INPUT_FILE, low_memory=False)

# ---------------------------------------------------------
# 1. CHECK INPUT AND RESIDUALS
# ---------------------------------------------------------

required = [
    "match_id",
    "season",
    "validation_fold",
    "runs_before",
    "expected_runs_before",
    "runs_below_par",
    "wickets_before",
    "scaled_innings_phase",
    "scheduled_legal_balls",
    "benchmark_level",
    "benchmark_training_matches",
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

df["match_id"] = df["match_id"].astype(str)
df["season"] = df["season"].astype(str)

df["calibration_error"] = (
    df["runs_before"] - df["expected_runs_before"]
)

if df["calibration_error"].isna().any():
    raise ValueError("Missing calibration errors found.")

print("Deliveries:", len(df))
print("Matches:", df["match_id"].nunique())

# ---------------------------------------------------------
# 2. MATCH-LEVEL CALIBRATION
# ---------------------------------------------------------

match_calibration = (
    df.groupby(["match_id", "season", "validation_fold"])
    .agg(
        deliveries=("match_id", "size"),
        actual_average=("runs_before", "mean"),
        expected_average=("expected_runs_before", "mean"),
        average_error=("calibration_error", "mean"),
        average_absolute_error=(
            "calibration_error",
            lambda x: x.abs().mean()
        ),
        pressure_deliveries=(
            "is_first_innings_pressure", "sum"
        ),
    )
    .reset_index()
)

match_calibration["pressure_percentage"] = (
    match_calibration["pressure_deliveries"] /
    match_calibration["deliveries"] * 100
)

print("\n" + "-" * 78)
print("MATCH-LEVEL CALIBRATION")
print("-" * 78)

print(
    match_calibration[
        [
            "match_id",
            "season",
            "deliveries",
            "average_error",
            "average_absolute_error",
            "pressure_percentage",
        ]
    ]
    .sort_values("average_error")
    .head(10)
    .to_string(index=False)
)

print("\nLargest positive calibration errors:")
print(
    match_calibration.sort_values(
        "average_error", ascending=False
    )[
        [
            "match_id",
            "season",
            "deliveries",
            "average_error",
            "average_absolute_error",
            "pressure_percentage",
        ]
    ].head(10).to_string(index=False)
)

# ---------------------------------------------------------
# 3. OVERALL CALIBRATION METRICS
# ---------------------------------------------------------

overall = {
    "mean_error": float(df["calibration_error"].mean()),
    "median_error": float(df["calibration_error"].median()),
    "mean_absolute_error": float(
        df["calibration_error"].abs().mean()
    ),
    "error_standard_deviation": float(
        df["calibration_error"].std()
    ),
    "match_mean_error": float(
        match_calibration["average_error"].mean()
    ),
    "match_mean_absolute_error": float(
        match_calibration["average_error"].abs().mean()
    ),
    "matches_within_2_runs": int(
        (
            match_calibration["average_error"].abs() <= 2
        ).sum()
    ),
    "matches_within_5_runs": int(
        (
            match_calibration["average_error"].abs() <= 5
        ).sum()
    ),
}

print("\n" + "-" * 78)
print("OVERALL CALIBRATION")
print("-" * 78)

for key, value in overall.items():
    print(f"{key}: {value:.4f}" if isinstance(value, float) else f"{key}: {value}")

# ---------------------------------------------------------
# 4. CALIBRATION BY SEASON
# ---------------------------------------------------------

season_calibration = (
    df.groupby("season")
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=(
            "calibration_error",
            lambda x: x.abs().mean()
        ),
        pressure_deliveries=(
            "is_first_innings_pressure", "sum"
        ),
    )
    .reset_index()
)

season_calibration["pressure_percentage"] = (
    season_calibration["pressure_deliveries"] /
    season_calibration["deliveries"] * 100
)

print("\n" + "-" * 78)
print("CALIBRATION BY SEASON")
print("-" * 78)

print(season_calibration.to_string(index=False))

# ---------------------------------------------------------
# 5. CALIBRATION BY PHASE
# ---------------------------------------------------------

phase_calibration = (
    df.groupby("scaled_innings_phase")
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=(
            "calibration_error",
            lambda x: x.abs().mean()
        ),
        pressure_deliveries=(
            "is_first_innings_pressure", "sum"
        ),
    )
    .reset_index()
)

phase_calibration["pressure_percentage"] = (
    phase_calibration["pressure_deliveries"] /
    phase_calibration["deliveries"] * 100
)

print("\n" + "-" * 78)
print("CALIBRATION BY PHASE")
print("-" * 78)

print(phase_calibration.to_string(index=False))

# ---------------------------------------------------------
# 6. CALIBRATION BY WICKET BAND
# ---------------------------------------------------------

df["wicket_band"] = pd.cut(
    df["wickets_before"],
    bins=[-1, 1, 3, 5, 7, 10],
    labels=[
        "0-1 wickets",
        "2-3 wickets",
        "4-5 wickets",
        "6-7 wickets",
        "8-10 wickets",
    ],
)

wicket_calibration = (
    df.groupby("wicket_band", observed=True)
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=(
            "calibration_error",
            lambda x: x.abs().mean()
        ),
    )
    .reset_index()
)

print("\n" + "-" * 78)
print("CALIBRATION BY WICKET BAND")
print("-" * 78)

print(wicket_calibration.to_string(index=False))

# ---------------------------------------------------------
# 7. CALIBRATION BY BENCHMARK LEVEL
# ---------------------------------------------------------

level_calibration = (
    df.groupby("benchmark_level")
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=(
            "calibration_error",
            lambda x: x.abs().mean()
        ),
        minimum_training_matches=(
            "benchmark_training_matches", "min"
        ),
        average_training_matches=(
            "benchmark_training_matches", "mean"
        ),
    )
    .reset_index()
)

print("\n" + "-" * 78)
print("CALIBRATION BY BENCHMARK LEVEL")
print("-" * 78)

print(level_calibration.to_string(index=False))

# ---------------------------------------------------------
# 8. CALIBRATION BY INNINGS LENGTH
# ---------------------------------------------------------

df["match_length_type"] = np.where(
    df["scheduled_legal_balls"] == 120,
    "Standard_120_ball",
    "Shortened",
)

length_calibration = (
    df.groupby("match_length_type")
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=(
            "calibration_error",
            lambda x: x.abs().mean()
        ),
        pressure_deliveries=(
            "is_first_innings_pressure", "sum"
        ),
    )
    .reset_index()
)

length_calibration["pressure_percentage"] = (
    length_calibration["pressure_deliveries"] /
    length_calibration["deliveries"] * 100
)

print("\n" + "-" * 78)
print("CALIBRATION BY INNINGS LENGTH")
print("-" * 78)

print(length_calibration.to_string(index=False))

# ---------------------------------------------------------
# 9. VALIDATION FOLD CALIBRATION
# ---------------------------------------------------------

fold_calibration = (
    match_calibration.groupby("validation_fold")
    .agg(
        matches=("match_id", "nunique"),
        mean_match_error=("average_error", "mean"),
        median_match_error=("average_error", "median"),
        mean_absolute_match_error=(
            "average_error",
            lambda x: x.abs().mean()
        ),
    )
    .reset_index()
)

print("\n" + "-" * 78)
print("FOLD-LEVEL MATCH CALIBRATION")
print("-" * 78)

print(fold_calibration.to_string(index=False))

# ---------------------------------------------------------
# 10. SAVE REPORTS
# ---------------------------------------------------------

match_calibration.to_csv(
    REPORTS / "t20i_first_innings_match_calibration.csv",
    index=False,
)

season_calibration.to_csv(
    REPORTS / "t20i_first_innings_calibration_by_season.csv",
    index=False,
)

phase_calibration.to_csv(
    REPORTS / "t20i_first_innings_calibration_by_phase.csv",
    index=False,
)

wicket_calibration.to_csv(
    REPORTS / "t20i_first_innings_calibration_by_wickets.csv",
    index=False,
)

level_calibration.to_csv(
    REPORTS / "t20i_first_innings_calibration_by_level.csv",
    index=False,
)

length_calibration.to_csv(
    REPORTS / "t20i_first_innings_calibration_by_length.csv",
    index=False,
)

fold_calibration.to_csv(
    REPORTS / "t20i_first_innings_calibration_by_fold.csv",
    index=False,
)

summary = {
    "deliveries": int(len(df)),
    "matches": int(df["match_id"].nunique()),
    "overall": overall,
    "largest_absolute_match_error": float(
        match_calibration["average_error"].abs().max()
    ),
    "matches_within_2_runs_percentage": round(
        float(
            (
                match_calibration["average_error"].abs() <= 2
            ).mean() * 100
        ),
        2,
    ),
    "matches_within_5_runs_percentage": round(
        float(
            (
                match_calibration["average_error"].abs() <= 5
            ).mean() * 100
        ),
        2,
    ),
}

with open(
    REPORTS / "t20i_first_innings_calibration_summary.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(summary, f, indent=4)

print("\n" + "=" * 78)
print("STEP 56 COMPLETED")
print("=" * 78)

print(json.dumps(summary, indent=4))
print("\nReports saved in:", REPORTS)
