
from pathlib import Path
import pandas as pd
import numpy as np
import json

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
RAW = ROOT / "data" / "raw"

print("\n" + "=" * 78)
print("STEP 57: T20I FIRST-INNINGS BENCHMARK OUTLIER INVESTIGATION")
print("=" * 78)

# ---------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------

df = pd.read_csv(
    REPORTS / "t20i_first_innings_par_deliveries.csv.gz",
    low_memory=False
)

matches = pd.read_csv(
    RAW / "matches.csv",
    low_memory=False
)

df["match_id"] = df["match_id"].astype(str)
matches["match_id"] = matches["match_id"].astype(str)

df["calibration_error"] = (
    df["runs_before"] - df["expected_runs_before"]
)

# ---------------------------------------------------------
# 2. MATCH-LEVEL ERROR SUMMARY
# ---------------------------------------------------------

match_summary = (
    df.groupby("match_id")
    .agg(
        season=("season", "first"),
        validation_fold=("validation_fold", "first"),
        deliveries=("match_id", "size"),
        scheduled_balls=("scheduled_legal_balls", "first"),
        actual_average=("runs_before", "mean"),
        expected_average=("expected_runs_before", "mean"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=(
            "calibration_error",
            lambda x: x.abs().mean()
        ),
        pressure_deliveries=(
            "is_first_innings_pressure", "sum"
        ),
        pressure_percentage=(
            "is_first_innings_pressure",
            lambda x: x.mean() * 100
        ),
    )
    .reset_index()
)

# Benchmark-level composition within each match.
level_counts = (
    df.groupby(["match_id", "benchmark_level"])
    .size()
    .unstack(fill_value=0)
    .reset_index()
)

match_summary = match_summary.merge(
    level_counts,
    on="match_id",
    how="left",
    validate="one_to_one"
)

# ---------------------------------------------------------
# 3. ADD MATCH METADATA
# ---------------------------------------------------------

metadata_columns = [
    "match_id",
    "match_date",
    "stage",
    "venue_country",
    "home_team",
    "away_team",
    "result",
]

available_metadata = [
    col for col in metadata_columns if col in matches.columns
]

match_summary = match_summary.merge(
    matches[available_metadata].drop_duplicates("match_id"),
    on="match_id",
    how="left",
    validate="one_to_one"
)

# ---------------------------------------------------------
# 4. DISPLAY MOST EXTREME MATCHES
# ---------------------------------------------------------

print("\n" + "-" * 78)
print("10 MOST NEGATIVE MATCH ERRORS")
print("-" * 78)

negative = match_summary.sort_values("mean_error").head(10)

print(
    negative.to_string(index=False)
)

print("\n" + "-" * 78)
print("10 MOST POSITIVE MATCH ERRORS")
print("-" * 78)

positive = match_summary.sort_values(
    "mean_error", ascending=False
).head(10)

print(
    positive.to_string(index=False)
)

# ---------------------------------------------------------
# 5. OUTLIER GROUPS
# ---------------------------------------------------------

match_summary["error_group"] = np.select(
    [
        match_summary["mean_error"] <= -15,
        match_summary["mean_error"] >= 15,
    ],
    [
        "Large negative error",
        "Large positive error",
    ],
    default="Other matches",
)

print("\n" + "-" * 78)
print("OUTLIER GROUP SUMMARY")
print("-" * 78)

outlier_summary = (
    match_summary.groupby("error_group")
    .agg(
        matches=("match_id", "size"),
        average_error=("mean_error", "mean"),
        average_absolute_error=(
            "mean_absolute_error", "mean"
        ),
        average_pressure_percentage=(
            "pressure_percentage", "mean"
        ),
        average_scheduled_balls=(
            "scheduled_balls", "mean"
        ),
    )
    .reset_index()
)

print(outlier_summary.to_string(index=False))

# ---------------------------------------------------------
# 6. BENCHMARK LEVEL COMPOSITION OF OUTLIERS
# ---------------------------------------------------------

level_columns = [
    col for col in [
        "season_segment_wicket",
        "season_phase_wicket",
        "pooled_segment_wicket",
        "pooled_phase_wicket",
        "pooled_phase",
    ]
    if col in match_summary.columns
]

for col in level_columns:
    match_summary[col] = match_summary[col].fillna(0)

print("\n" + "-" * 78)
print("BENCHMARK LEVEL COUNTS BY ERROR GROUP")
print("-" * 78)

if level_columns:
    level_group_summary = (
        match_summary.groupby("error_group")[level_columns]
        .sum()
        .reset_index()
    )

    print(level_group_summary.to_string(index=False))

# ---------------------------------------------------------
# 7. PHASE AND WICKET SITUATION IN EXTREME MATCHES
# ---------------------------------------------------------

extreme_ids = match_summary.loc[
    match_summary["mean_error"].abs() >= 15,
    "match_id"
]

extreme = df[df["match_id"].isin(extreme_ids)].copy()

print("\n" + "-" * 78)
print("EXTREME MATCHES: CALIBRATION BY PHASE")
print("-" * 78)

extreme_phase = (
    extreme.groupby("scaled_innings_phase")
    .agg(
        deliveries=("match_id", "size"),
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

print(extreme_phase.to_string(index=False))

print("\n" + "-" * 78)
print("EXTREME MATCHES: CALIBRATION BY WICKET BAND")
print("-" * 78)

extreme["wicket_band"] = pd.cut(
    extreme["wickets_before"],
    bins=[-1, 1, 3, 5, 7, 10],
    labels=[
        "0-1 wickets",
        "2-3 wickets",
        "4-5 wickets",
        "6-7 wickets",
        "8-10 wickets",
    ],
)

extreme_wickets = (
    extreme.groupby("wicket_band", observed=True)
    .agg(
        deliveries=("match_id", "size"),
        mean_error=("calibration_error", "mean"),
        mean_absolute_error=(
            "calibration_error",
            lambda x: x.abs().mean()
        ),
    )
    .reset_index()
)

print(extreme_wickets.to_string(index=False))

# ---------------------------------------------------------
# 8. CHECK MATCH SCORE PROXIES
# ---------------------------------------------------------

# The last recorded pre-delivery score is not the final innings
# total. This is deliberately labelled as a score proxy.

last_state = (
    df.sort_values(
        ["match_id", "legal_balls_before"]
    )
    .groupby("match_id")
    .tail(1)[
        [
            "match_id",
            "runs_before",
            "legal_balls_before",
            "scheduled_legal_balls",
        ]
    ]
    .rename(
        columns={
            "runs_before": "last_recorded_runs_before",
            "legal_balls_before": "last_recorded_legal_balls",
        }
    )
)

match_summary = match_summary.merge(
    last_state,
    on="match_id",
    how="left",
    validate="one_to_one"
)

match_summary["last_recorded_balls_remaining"] = (
    match_summary["scheduled_balls"] -
    match_summary["last_recorded_legal_balls"]
)

print("\n" + "-" * 78)
print("EXTREME MATCHES: LAST RECORDED SCORE PROXY")
print("-" * 78)

print(
    match_summary[
        match_summary["mean_error"].abs() >= 15
    ][
        [
            "match_id",
            "season",
            "mean_error",
            "deliveries",
            "scheduled_balls",
            "last_recorded_runs_before",
            "last_recorded_legal_balls",
            "last_recorded_balls_remaining",
            "pressure_percentage",
        ]
    ].sort_values("mean_error").to_string(index=False)
)

# ---------------------------------------------------------
# 9. SAVE REPORTS
# ---------------------------------------------------------

match_summary.to_csv(
    REPORTS / "t20i_first_innings_outlier_match_summary.csv",
    index=False,
)

outlier_summary.to_csv(
    REPORTS / "t20i_first_innings_outlier_group_summary.csv",
    index=False,
)

extreme_phase.to_csv(
    REPORTS / "t20i_first_innings_outlier_phase_summary.csv",
    index=False,
)

extreme_wickets.to_csv(
    REPORTS / "t20i_first_innings_outlier_wicket_summary.csv",
    index=False,
)

summary = {
    "total_matches": int(len(match_summary)),
    "large_negative_error_matches": int(
        (match_summary["mean_error"] <= -15).sum()
    ),
    "large_positive_error_matches": int(
        (match_summary["mean_error"] >= 15).sum()
    ),
    "extreme_error_matches": int(
        (match_summary["mean_error"].abs() >= 15).sum()
    ),
    "maximum_positive_error": float(
        match_summary["mean_error"].max()
    ),
    "maximum_negative_error": float(
        match_summary["mean_error"].min()
    ),
    "extreme_match_ids": extreme_ids.astype(str).tolist(),
}

with open(
    REPORTS / "t20i_first_innings_outlier_summary.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(summary, f, indent=4)

print("\n" + "=" * 78)
print("STEP 57 COMPLETED")
print("=" * 78)

print(json.dumps(summary, indent=4))
print("\nReports saved in:", REPORTS)
