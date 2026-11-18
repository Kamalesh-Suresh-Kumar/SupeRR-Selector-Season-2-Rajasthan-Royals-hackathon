from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

CHECKPOINT_FILE = (
    REPORTS / "t20i_first_innings_checkpoint_details.csv"
)

DELIVERY_FILE = (
    REPORTS / "t20i_first_innings_par_deliveries.csv.gz"
)

print("\n" + "=" * 78)
print("STEP 59: T20I CHECKPOINT ERROR DIAGNOSTIC AUDIT")
print("=" * 78)

# ---------------------------------------------------------
# 1. LOAD STEP 58 CHECKPOINT RESULTS
# ---------------------------------------------------------

checkpoints = pd.read_csv(CHECKPOINT_FILE, low_memory=False)

checkpoints["match_id"] = checkpoints["match_id"].astype(str)

required = [
    "match_id",
    "season",
    "checkpoint_percentage",
    "calibration_error",
    "absolute_error",
    "pressure",
    "phase",
    "benchmark_level",
    "match_length_type",
]

# match_length_type was created in Step 58 before saving.
# If an older checkpoint file does not contain it, recreate it.

missing = [
    column for column in required
    if column not in checkpoints.columns
    and column != "match_length_type"
]

if missing:
    raise ValueError(
        f"Missing required checkpoint columns: {missing}"
    )

if "match_length_type" not in checkpoints.columns:
    checkpoints["match_length_type"] = np.where(
        checkpoints["scheduled_legal_balls"] == 120,
        "Standard_120_ball",
        "Shortened",
    )

checkpoints["error_direction"] = np.where(
    checkpoints["calibration_error"] > 0,
    "Underestimated",
    np.where(
        checkpoints["calibration_error"] < 0,
        "Overestimated",
        "Exact",
    ),
)

print("Checkpoint observations:", len(checkpoints))
print("Unique matches:", checkpoints["match_id"].nunique())

# ---------------------------------------------------------
# 2. ENRICH CHECKPOINTS WITH WICKET INFORMATION
# ---------------------------------------------------------

deliveries = pd.read_csv(DELIVERY_FILE, low_memory=False)

deliveries["match_id"] = deliveries["match_id"].astype(str)

# Find the actual delivery-state column.
# Step 58's actual_legal_ball represents legal_balls_before.

if "legal_balls_before" not in deliveries.columns:
    raise ValueError(
        "legal_balls_before is missing from the delivery file."
    )

wicket_candidates = [
    "wickets_in_hand",
    "wickets_lost_before",
    "wickets_before",
    "cumulative_wickets_before",
]

wicket_column = None

for column in wicket_candidates:
    if column in deliveries.columns:
        wicket_column = column
        break

# Select only the fields needed for enrichment.

extra_columns = []

for column in [
    "match_id",
    "legal_balls_before",
    "cumulative_wickets",
    "wickets_in_hand",
    "wickets_lost_before",
    "wickets_before",
    "cumulative_wickets_before",
]:
    if column in deliveries.columns:
        extra_columns.append(column)

delivery_states = deliveries[extra_columns].copy()

delivery_states = delivery_states.drop_duplicates(
    ["match_id", "legal_balls_before"]
)

checkpoints = checkpoints.merge(
    delivery_states,
    left_on=["match_id", "actual_legal_ball"],
    right_on=["match_id", "legal_balls_before"],
    how="left",
    validate="many_to_one",
)

# Convert available wicket information into wickets lost.
# Do not use cumulative_wickets unless no pre-delivery
# wicket field is available; it includes the current state.

if "wickets_in_hand" in checkpoints.columns:
    checkpoints["wickets_lost"] = (
        10 - checkpoints["wickets_in_hand"]
    )
    wicket_source = "wickets_in_hand"

elif "wickets_lost_before" in checkpoints.columns:
    checkpoints["wickets_lost"] = (
        checkpoints["wickets_lost_before"]
    )
    wicket_source = "wickets_lost_before"

elif "wickets_before" in checkpoints.columns:
    checkpoints["wickets_lost"] = (
        checkpoints["wickets_before"]
    )
    wicket_source = "wickets_before"

elif "cumulative_wickets_before" in checkpoints.columns:
    checkpoints["wickets_lost"] = (
        checkpoints["cumulative_wickets_before"]
    )
    wicket_source = "cumulative_wickets_before"

else:
    checkpoints["wickets_lost"] = np.nan
    wicket_source = "Unavailable"

if wicket_source != "Unavailable":
    checkpoints["wickets_lost"] = (
        checkpoints["wickets_lost"]
        .clip(lower=0, upper=10)
    )

    checkpoints["wicket_band"] = pd.cut(
        checkpoints["wickets_lost"],
        bins=[-1, 1, 3, 5, 7, 10],
        labels=[
            "0-1 wickets lost",
            "2-3 wickets lost",
            "4-5 wickets lost",
            "6-7 wickets lost",
            "8-10 wickets lost",
        ],
    )

else:
    checkpoints["wicket_band"] = "Unavailable"

print("Wicket information source:", wicket_source)
print(
    "Checkpoints with wicket information:",
    int(checkpoints["wickets_lost"].notna().sum()),
)

# ---------------------------------------------------------
# 3. COMMON GROUP SUMMARY FUNCTION
# ---------------------------------------------------------

def create_summary(data, group_columns):

    result = (
        data.groupby(
            group_columns,
            observed=True,
            dropna=False,
        )
        .agg(
            observations=("calibration_error", "size"),
            matches=("match_id", "nunique"),
            mean_error=("calibration_error", "mean"),
            median_error=("calibration_error", "median"),
            mean_absolute_error=("absolute_error", "mean"),
            median_absolute_error=("absolute_error", "median"),
            within_5_runs=(
                "absolute_error",
                lambda x: (x <= 5).mean() * 100,
            ),
            within_10_runs=(
                "absolute_error",
                lambda x: (x <= 10).mean() * 100,
            ),
            pressure_observations=("pressure", "sum"),
        )
        .reset_index()
    )

    result["pressure_percentage"] = (
        result["pressure_observations"] /
        result["observations"] * 100
    )

    return result

# ---------------------------------------------------------
# 4. PRESSURE VS NON-PRESSURE AUDIT
# ---------------------------------------------------------

pressure_summary = create_summary(
    checkpoints,
    ["pressure"],
)

print("\n" + "-" * 78)
print("PRESSURE VS NON-PRESSURE CALIBRATION")
print("-" * 78)

print(pressure_summary.to_string(index=False))

# ---------------------------------------------------------
# 5. INNINGS PHASE AUDIT
# ---------------------------------------------------------

phase_summary = create_summary(
    checkpoints,
    ["phase"],
)

print("\n" + "-" * 78)
print("CALIBRATION BY INNINGS PHASE")
print("-" * 78)

print(phase_summary.to_string(index=False))

# ---------------------------------------------------------
# 6. WICKET-LOSS AUDIT
# ---------------------------------------------------------

wicket_summary = create_summary(
    checkpoints,
    ["wicket_band"],
)

print("\n" + "-" * 78)
print("CALIBRATION BY WICKETS LOST")
print("-" * 78)

print(wicket_summary.to_string(index=False))

# ---------------------------------------------------------
# 7. INNINGS LENGTH AUDIT
# ---------------------------------------------------------

length_summary = create_summary(
    checkpoints,
    ["match_length_type"],
)

print("\n" + "-" * 78)
print("CALIBRATION BY INNINGS LENGTH")
print("-" * 78)

print(length_summary.to_string(index=False))

# ---------------------------------------------------------
# 8. BENCHMARK LEVEL AUDIT
# ---------------------------------------------------------

level_summary = create_summary(
    checkpoints,
    ["benchmark_level"],
)

print("\n" + "-" * 78)
print("CALIBRATION BY BENCHMARK LEVEL")
print("-" * 78)

print(level_summary.to_string(index=False))

# ---------------------------------------------------------
# 9. CHECKPOINT AND PRESSURE COMBINATION
# ---------------------------------------------------------

checkpoint_pressure_summary = create_summary(
    checkpoints,
    ["checkpoint_percentage", "pressure"],
)

print("\n" + "-" * 78)
print("CHECKPOINT CALIBRATION BY PRESSURE STATUS")
print("-" * 78)

print(
    checkpoint_pressure_summary.to_string(index=False)
)

# ---------------------------------------------------------
# 10. PHASE AND PRESSURE COMBINATION
# ---------------------------------------------------------

phase_pressure_summary = create_summary(
    checkpoints,
    ["phase", "pressure"],
)

print("\n" + "-" * 78)
print("PHASE AND PRESSURE CALIBRATION")
print("-" * 78)

print(
    phase_pressure_summary.to_string(index=False)
)

# ---------------------------------------------------------
# 11. LARGEST POSITIVE AND NEGATIVE ERRORS
# ---------------------------------------------------------

largest_positive = (
    checkpoints.sort_values(
        "calibration_error",
        ascending=False,
    )
    .head(15)
)

largest_negative = (
    checkpoints.sort_values(
        "calibration_error",
        ascending=True,
    )
    .head(15)
)

outlier_columns = [
    "match_id",
    "season",
    "checkpoint_percentage",
    "calibration_error",
    "absolute_error",
    "pressure",
    "phase",
    "benchmark_level",
    "wickets_lost",
    "match_length_type",
]

outlier_columns = [
    column for column in outlier_columns
    if column in checkpoints.columns
]

print("\n" + "-" * 78)
print("15 LARGEST POSITIVE ERRORS")
print("-" * 78)

print(
    largest_positive[outlier_columns].to_string(index=False)
)

print("\n" + "-" * 78)
print("15 LARGEST NEGATIVE ERRORS")
print("-" * 78)

print(
    largest_negative[outlier_columns].to_string(index=False)
)

# ---------------------------------------------------------
# 12. ERROR DIRECTION SUMMARY
# ---------------------------------------------------------

direction_summary = (
    checkpoints.groupby("error_direction")
    .agg(
        observations=("match_id", "size"),
        matches=("match_id", "nunique"),
        mean_absolute_error=("absolute_error", "mean"),
    )
    .reset_index()
)

direction_summary["percentage"] = (
    direction_summary["observations"] /
    len(checkpoints) * 100
)

print("\n" + "-" * 78)
print("ERROR DIRECTION DISTRIBUTION")
print("-" * 78)

print(direction_summary.to_string(index=False))

# ---------------------------------------------------------
# 13. OVERALL DIAGNOSTIC SUMMARY
# ---------------------------------------------------------

overall = {
    "checkpoint_observations": int(len(checkpoints)),
    "matches": int(checkpoints["match_id"].nunique()),
    "wicket_information_source": wicket_source,
    "checkpoints_with_wicket_information": int(
        checkpoints["wickets_lost"].notna().sum()
    ),
    "mean_error": round(
        float(checkpoints["calibration_error"].mean()), 4
    ),
    "mean_absolute_error": round(
        float(checkpoints["absolute_error"].mean()), 4
    ),
    "median_absolute_error": round(
        float(checkpoints["absolute_error"].median()), 4
    ),
    "positive_error_observations": int(
        (checkpoints["calibration_error"] > 0).sum()
    ),
    "negative_error_observations": int(
        (checkpoints["calibration_error"] < 0).sum()
    ),
    "exact_error_observations": int(
        (checkpoints["calibration_error"] == 0).sum()
    ),
}

# ---------------------------------------------------------
# 14. SAVE REPORTS
# ---------------------------------------------------------

checkpoints.to_csv(
    REPORTS / "t20i_checkpoint_diagnostic_details.csv",
    index=False,
)

pressure_summary.to_csv(
    REPORTS / "t20i_checkpoint_by_pressure.csv",
    index=False,
)

phase_summary.to_csv(
    REPORTS / "t20i_checkpoint_by_phase.csv",
    index=False,
)

wicket_summary.to_csv(
    REPORTS / "t20i_checkpoint_by_wickets.csv",
    index=False,
)

length_summary.to_csv(
    REPORTS / "t20i_checkpoint_by_length.csv",
    index=False,
)

level_summary.to_csv(
    REPORTS / "t20i_checkpoint_by_benchmark_level.csv",
    index=False,
)

checkpoint_pressure_summary.to_csv(
    REPORTS / "t20i_checkpoint_by_checkpoint_pressure.csv",
    index=False,
)

phase_pressure_summary.to_csv(
    REPORTS / "t20i_checkpoint_by_phase_pressure.csv",
    index=False,
)

largest_positive[outlier_columns].to_csv(
    REPORTS / "t20i_checkpoint_largest_positive_errors.csv",
    index=False,
)

largest_negative[outlier_columns].to_csv(
    REPORTS / "t20i_checkpoint_largest_negative_errors.csv",
    index=False,
)

direction_summary.to_csv(
    REPORTS / "t20i_checkpoint_error_direction.csv",
    index=False,
)

with open(
    REPORTS / "t20i_checkpoint_diagnostic_summary.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(overall, f, indent=4)

print("\n" + "=" * 78)
print("STEP 59 COMPLETED")
print("=" * 78)

print(json.dumps(overall, indent=4))

print("\nReports saved in:", REPORTS)