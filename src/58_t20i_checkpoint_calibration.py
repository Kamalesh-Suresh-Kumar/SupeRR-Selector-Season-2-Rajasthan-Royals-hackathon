
from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

INPUT_FILE = REPORTS / "t20i_first_innings_par_deliveries.csv.gz"

print("\n" + "=" * 78)
print("STEP 58: T20I FIRST-INNINGS CHECKPOINT CALIBRATION")
print("=" * 78)

# ---------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------

df = pd.read_csv(INPUT_FILE, low_memory=False)

df["match_id"] = df["match_id"].astype(str)

required = [
    "match_id",
    "season",
    "legal_balls_before",
    "scheduled_legal_balls",
    "runs_before",
    "expected_runs_before",
    "is_first_innings_pressure",
    "scaled_innings_phase",
    "benchmark_level",
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

df = df.sort_values(
    ["match_id", "legal_balls_before"]
).copy()

# ---------------------------------------------------------
# 2. SELECT COMPARABLE INNINGS CHECKPOINTS
# ---------------------------------------------------------

checkpoint_fractions = [0.25, 0.50, 0.75, 0.90]

checkpoint_rows = []

for match_id, group in df.groupby("match_id", sort=False):

    group = group.sort_values("legal_balls_before")

    scheduled = float(
        group["scheduled_legal_balls"].iloc[0]
    )

    for fraction in checkpoint_fractions:

        target_ball = int(round(scheduled * fraction))

        # Select the delivery state closest to the target.
        # This handles illegal deliveries and shortened innings.
        distances = np.abs(
          group["legal_balls_before"].to_numpy(dtype=float) - target_ball
        )

        selected_position = int(np.argmin(distances))

        selected = group.iloc[selected_position]

        checkpoint_rows.append({
            "match_id": match_id,
            "season": selected["season"],
            "checkpoint_fraction": fraction,
            "checkpoint_percentage": int(fraction * 100),
            "target_legal_ball": target_ball,
            "actual_legal_ball": int(
                selected["legal_balls_before"]
            ),
            "scheduled_legal_balls": scheduled,
            "runs_before": float(selected["runs_before"]),
            "expected_runs_before": float(
                selected["expected_runs_before"]
            ),
            "calibration_error": float(
                selected["runs_before"] -
                selected["expected_runs_before"]
            ),
            "absolute_error": abs(
                float(selected["runs_before"]) -
                float(selected["expected_runs_before"])
            ),
            "pressure": bool(
                selected["is_first_innings_pressure"]
            ),
            "phase": selected["scaled_innings_phase"],
            "benchmark_level": selected["benchmark_level"],
            "benchmark_training_matches": int(
                selected["benchmark_training_matches"]
            ),
        })

checkpoints = pd.DataFrame(checkpoint_rows)

if checkpoints.duplicated(
    ["match_id", "checkpoint_percentage"]
).any():
    raise ValueError("Duplicate match/checkpoint rows found.")

print("Matches:", checkpoints["match_id"].nunique())
print("Checkpoint observations:", len(checkpoints))

# ---------------------------------------------------------
# 3. CALIBRATION BY CHECKPOINT
# ---------------------------------------------------------

checkpoint_summary = (
    checkpoints.groupby("checkpoint_percentage")
    .agg(
        matches=("match_id", "nunique"),
        mean_error=("calibration_error", "mean"),
        median_error=("calibration_error", "median"),
        mean_absolute_error=("absolute_error", "mean"),
        median_absolute_error=("absolute_error", "median"),
        pressure_matches=("pressure", "sum"),
    )
    .reset_index()
)

checkpoint_summary["pressure_percentage"] = (
    checkpoint_summary["pressure_matches"] /
    checkpoint_summary["matches"] * 100
)

print("\n" + "-" * 78)
print("CALIBRATION AT INNINGS CHECKPOINTS")
print("-" * 78)

print(checkpoint_summary.to_string(index=False))

# ---------------------------------------------------------
# 4. CHECKPOINT CALIBRATION BY INNINGS LENGTH
# ---------------------------------------------------------

checkpoints["match_length_type"] = np.where(
    checkpoints["scheduled_legal_balls"] == 120,
    "Standard_120_ball",
    "Shortened",
)

length_summary = (
    checkpoints.groupby(
        ["match_length_type", "checkpoint_percentage"]
    )
    .agg(
        matches=("match_id", "nunique"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=("absolute_error", "mean"),
        pressure_matches=("pressure", "sum"),
    )
    .reset_index()
)

length_summary["pressure_percentage"] = (
    length_summary["pressure_matches"] /
    length_summary["matches"] * 100
)

print("\n" + "-" * 78)
print("CALIBRATION BY INNINGS LENGTH AND CHECKPOINT")
print("-" * 78)

print(length_summary.to_string(index=False))

# ---------------------------------------------------------
# 5. CHECKPOINT CALIBRATION BY SEASON
# ---------------------------------------------------------

season_summary = (
    checkpoints.groupby(
        ["season", "checkpoint_percentage"]
    )
    .agg(
        matches=("match_id", "nunique"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=("absolute_error", "mean"),
        pressure_matches=("pressure", "sum"),
    )
    .reset_index()
)

season_summary["pressure_percentage"] = (
    season_summary["pressure_matches"] /
    season_summary["matches"] * 100
)

print("\n" + "-" * 78)
print("CALIBRATION BY SEASON AND CHECKPOINT")
print("-" * 78)

print(season_summary.to_string(index=False))

# ---------------------------------------------------------
# 6. CHECKPOINT CALIBRATION BY BENCHMARK LEVEL
# ---------------------------------------------------------

level_summary = (
    checkpoints.groupby(
        ["benchmark_level", "checkpoint_percentage"]
    )
    .agg(
        observations=("match_id", "size"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=("absolute_error", "mean"),
        minimum_training_matches=(
            "benchmark_training_matches", "min"
        ),
    )
    .reset_index()
)

print("\n" + "-" * 78)
print("CALIBRATION BY BENCHMARK LEVEL AND CHECKPOINT")
print("-" * 78)

print(level_summary.to_string(index=False))

# ---------------------------------------------------------
# 7. MATCH-LEVEL CHECKPOINT ERROR RANGE
# ---------------------------------------------------------

match_checkpoint_summary = (
    checkpoints.groupby("match_id")
    .agg(
        season=("season", "first"),
        checkpoints=("checkpoint_percentage", "count"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=("absolute_error", "mean"),
        maximum_absolute_error=("absolute_error", "max"),
        pressure_checkpoints=("pressure", "sum"),
    )
    .reset_index()
)

print("\n" + "-" * 78)
print("MATCHES WITH LARGEST CHECKPOINT ERRORS")
print("-" * 78)

print(
    match_checkpoint_summary.sort_values(
        "mean_absolute_error", ascending=False
    ).head(15).to_string(index=False)
)

# ---------------------------------------------------------
# 8. OVERALL CHECKPOINT SUMMARY
# ---------------------------------------------------------

overall = {
    "matches": int(checkpoints["match_id"].nunique()),
    "checkpoint_observations": int(len(checkpoints)),
    "mean_error": float(
        checkpoints["calibration_error"].mean()
    ),
    "mean_absolute_error": float(
        checkpoints["absolute_error"].mean()
    ),
    "median_absolute_error": float(
        checkpoints["absolute_error"].median()
    ),
    "observations_within_5_runs_percentage": round(
        float(
            (
                checkpoints["absolute_error"] <= 5
            ).mean() * 100
        ),
        2,
    ),
    "observations_within_10_runs_percentage": round(
        float(
            (
                checkpoints["absolute_error"] <= 10
            ).mean() * 100
        ),
        2,
    ),
}

# ---------------------------------------------------------
# 9. SAVE REPORTS
# ---------------------------------------------------------

checkpoints.to_csv(
    REPORTS / "t20i_first_innings_checkpoint_details.csv",
    index=False,
)

checkpoint_summary.to_csv(
    REPORTS / "t20i_first_innings_checkpoint_summary.csv",
    index=False,
)

length_summary.to_csv(
    REPORTS / "t20i_first_innings_checkpoint_by_length.csv",
    index=False,
)

season_summary.to_csv(
    REPORTS / "t20i_first_innings_checkpoint_by_season.csv",
    index=False,
)

level_summary.to_csv(
    REPORTS / "t20i_first_innings_checkpoint_by_level.csv",
    index=False,
)

match_checkpoint_summary.to_csv(
    REPORTS / "t20i_first_innings_checkpoint_by_match.csv",
    index=False,
)

with open(
    REPORTS / "t20i_first_innings_checkpoint_summary.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(overall, f, indent=4)

print("\n" + "=" * 78)
print("STEP 58 COMPLETED")
print("=" * 78)

print(json.dumps(overall, indent=4))
print("\nReports saved in:", REPORTS)
