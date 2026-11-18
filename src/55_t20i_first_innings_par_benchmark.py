
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

INPUT_FILE = REPORTS / "t20i_pressure_context_scaled_deliveries.csv.gz"

print("\n" + "=" * 78)
print("STEP 55: T20I FIRST-INNINGS MATCH-HELD-OUT PAR BENCHMARK")
print("=" * 78)

# ---------------------------------------------------------
# 1. LOAD AND PREPARE FIRST-INNINGS DATA
# ---------------------------------------------------------

df = pd.read_csv(INPUT_FILE, low_memory=False)
df = df[df["innings"] == 1].copy()

required_columns = [
    "match_id",
    "season",
    "runs_before",
    "legal_balls_before",
    "wickets_before",
    "scheduled_legal_balls",
    "scaled_innings_phase",
]

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")

df["season"] = df["season"].astype(str)
df["scaled_innings_phase"] = df["scaled_innings_phase"].astype(str)

df["over_segment"] = (
    df["legal_balls_before"] // 6
).astype(int)

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
).astype(str)

df["runs_before"] = pd.to_numeric(
    df["runs_before"], errors="coerce"
)

df["match_id"] = df["match_id"].astype(str)

if df["runs_before"].isna().any():
    raise ValueError("Missing runs_before values found.")

if df["wicket_band"].isin(["nan"]).any():
    raise ValueError("Missing wicket-band values found.")

print("First-innings deliveries:", len(df))
print("First-innings matches:", df["match_id"].nunique())
print("Seasons:", df["season"].nunique())

# ---------------------------------------------------------
# 2. ASSIGN FIVE MATCH-HELD-OUT FOLDS
# ---------------------------------------------------------

# Assign folds separately within each season.
# Small seasons will still be covered, but use pooled
# fallback benchmarks whenever their own support is low.

fold_map = {}

for season, group in df.groupby("season"):
    match_ids = sorted(group["match_id"].unique())

    for i, match_id in enumerate(match_ids):
        fold_map[match_id] = i % 5

df["validation_fold"] = df["match_id"].map(fold_map).astype(int)

print("\nFold distribution:")

fold_summary = (
    df[["match_id", "season", "validation_fold"]]
    .drop_duplicates()
    .groupby(["season", "validation_fold"])
    .size()
    .unstack(fill_value=0)
)

print(fold_summary.to_string())

# ---------------------------------------------------------
# 3. BENCHMARK HELPER
# ---------------------------------------------------------

def build_benchmark(training_data, group_columns):
    """
    First calculate one average per match and group.
    Then average those match-level values.

    This prevents matches with more deliveries in a group
    from receiving disproportionate weight.
    """

    match_level = (
        training_data.groupby(
            group_columns + ["match_id"],
            observed=True
        )["runs_before"]
        .mean()
        .reset_index(name="match_average_runs")
    )

    benchmark = (
        match_level.groupby(
            group_columns,
            observed=True
        )
        .agg(
            expected_runs=("match_average_runs", "mean"),
            training_matches=("match_id", "nunique"),
        )
        .reset_index()
    )

    return benchmark


# ---------------------------------------------------------
# 4. CREATE MATCH-HELD-OUT BENCHMARKS
# ---------------------------------------------------------

df["expected_runs_before"] = np.nan
df["benchmark_level"] = ""
df["benchmark_training_matches"] = 0

benchmark_levels = [
    (
        "season_segment_wicket",
        ["season", "over_segment", "wicket_band"],
    ),
    (
        "season_phase_wicket",
        ["season", "scaled_innings_phase", "wicket_band"],
    ),
    (
        "pooled_segment_wicket",
        ["over_segment", "wicket_band"],
    ),
    (
        "pooled_phase_wicket",
        ["scaled_innings_phase", "wicket_band"],
    ),
    (
        "pooled_phase",
        ["scaled_innings_phase"],
    ),
]

for fold in range(5):

    print(f"\nBuilding benchmark for validation fold {fold + 1}/5")

    train = df[df["validation_fold"] != fold].copy()
    test_index = df.index[df["validation_fold"] == fold]

    unresolved = pd.Series(True, index=test_index)

    for level_name, group_columns in benchmark_levels:

        benchmark = build_benchmark(
            train,
            group_columns
        )

        # Only use groups supported by at least 5 training matches.
        benchmark = benchmark[
            benchmark["training_matches"] >= 5
        ].copy()

        if benchmark.empty:
            continue

        test_part = df.loc[test_index].copy()

        lookup_columns = group_columns + [
            "expected_runs",
            "training_matches",
        ]

        matched = test_part.merge(
            benchmark[lookup_columns],
            on=group_columns,
            how="left",
            validate="many_to_one",
            sort=False,
        )

        matched = matched.set_index(test_part.index)

        available = (
            unresolved &
            matched["expected_runs"].notna()
        )

        selected_index = available[available].index

        if len(selected_index) > 0:
            df.loc[
                selected_index,
                "expected_runs_before"
            ] = matched.loc[
                selected_index,
                "expected_runs"
            ].values

            df.loc[
                selected_index,
                "benchmark_level"
            ] = level_name

            df.loc[
                selected_index,
                "benchmark_training_matches"
            ] = matched.loc[
                selected_index,
                "training_matches"
            ].values

            unresolved.loc[selected_index] = False

        print(
            f"  {level_name}: "
            f"{len(selected_index):,} deliveries assigned"
        )

# ---------------------------------------------------------
# 5. CHECK BENCHMARK COVERAGE
# ---------------------------------------------------------

uncovered = df["expected_runs_before"].isna()

print("\n" + "-" * 78)
print("BENCHMARK COVERAGE")
print("-" * 78)

print("Total first-innings deliveries:", len(df))
print("Benchmark-covered deliveries:", int((~uncovered).sum()))
print("Uncovered deliveries:", int(uncovered.sum()))

if uncovered.any():
    print("\nUncovered delivery examples:")
    print(
        df.loc[
            uncovered,
            [
                "match_id",
                "season",
                "over_segment",
                "wicket_band",
                "scaled_innings_phase",
            ],
        ].head(20).to_string(index=False)
    )

    raise ValueError(
        "Some deliveries have no supported benchmark. "
        "Do not proceed until coverage is resolved."
    )

# ---------------------------------------------------------
# 6. CALCULATE PAR DIFFERENCE
# ---------------------------------------------------------

df["runs_below_par"] = (
    df["expected_runs_before"] - df["runs_before"]
)

# Positive value means the batting team is below par.
# Negative value means the batting team is above par.

df["wickets_in_hand_before"] = (
    10 - df["wickets_before"]
)

# Scale early-innings collapse boundary for shortened matches.
df["early_innings_boundary"] = (
    df["scheduled_legal_balls"] * 0.30
)

df["signal_below_par"] = (
    df["runs_below_par"] >= 5
)

df["signal_low_wickets"] = (
    df["wickets_in_hand_before"] <= 6
)

df["signal_early_collapse"] = (
    (df["legal_balls_before"] <= df["early_innings_boundary"]) &
    (df["wickets_in_hand_before"] <= 7)
)

df["first_innings_pressure_signal_count"] = (
    df["signal_below_par"].astype(int) +
    df["signal_low_wickets"].astype(int) +
    df["signal_early_collapse"].astype(int)
)

df["is_first_innings_pressure"] = (
    df["first_innings_pressure_signal_count"] >= 2
)

df["first_innings_pressure_severity"] = np.where(
    df["is_first_innings_pressure"] &
    (
        (df["runs_below_par"] >= 10) |
        (df["wickets_in_hand_before"] <= 3)
    ),
    "Severe",
    np.where(
        df["is_first_innings_pressure"],
        "High",
        "Normal",
    ),
)

# ---------------------------------------------------------
# 7. VALIDATE FOLD AND BENCHMARK SUPPORT
# ---------------------------------------------------------

coverage_by_level = (
    df.groupby("benchmark_level")
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        average_training_matches=(
            "benchmark_training_matches", "mean"
        ),
        minimum_training_matches=(
            "benchmark_training_matches", "min"
        ),
    )
    .reset_index()
)

print("\n" + "-" * 78)
print("BENCHMARK LEVEL DISTRIBUTION")
print("-" * 78)

print(coverage_by_level.to_string(index=False))

# ---------------------------------------------------------
# 8. ACTUAL VS EXPECTED SCORE BY SEASON
# ---------------------------------------------------------

season_validation = (
    df.groupby("season")
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        actual_average_runs_before=("runs_before", "mean"),
        expected_average_runs_before=(
            "expected_runs_before", "mean"
        ),
        average_runs_below_par=("runs_below_par", "mean"),
        pressure_deliveries=(
            "is_first_innings_pressure", "sum"
        ),
    )
    .reset_index()
)

season_validation["pressure_percentage"] = (
    season_validation["pressure_deliveries"] /
    season_validation["deliveries"] * 100
)

season_validation["actual_expected_difference"] = (
    season_validation["actual_average_runs_before"] -
    season_validation["expected_average_runs_before"]
)

print("\n" + "-" * 78)
print("SEASON VALIDATION")
print("-" * 78)

print(season_validation.to_string(index=False))

# ---------------------------------------------------------
# 9. PRESSURE BY PHASE
# ---------------------------------------------------------

phase_summary = (
    df.groupby("scaled_innings_phase")
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=(
            "is_first_innings_pressure", "sum"
        ),
        average_runs_below_par=("runs_below_par", "mean"),
        average_wickets_before=("wickets_before", "mean"),
    )
    .reset_index()
)

phase_summary["pressure_percentage"] = (
    phase_summary["pressure_deliveries"] /
    phase_summary["deliveries"] * 100
)

print("\n" + "-" * 78)
print("FIRST-INNINGS PRESSURE BY PHASE")
print("-" * 78)

print(phase_summary.to_string(index=False))

# ---------------------------------------------------------
# 10. FOLD VALIDATION
# ---------------------------------------------------------

fold_validation = (
    df.groupby("validation_fold")
    .agg(
        matches=("match_id", "nunique"),
        deliveries=("match_id", "size"),
        actual_average_runs_before=("runs_before", "mean"),
        expected_average_runs_before=(
            "expected_runs_before", "mean"
        ),
        average_runs_below_par=("runs_below_par", "mean"),
        pressure_deliveries=(
            "is_first_innings_pressure", "sum"
        ),
    )
    .reset_index()
)

fold_validation["actual_expected_difference"] = (
    fold_validation["actual_average_runs_before"] -
    fold_validation["expected_average_runs_before"]
)

print("\n" + "-" * 78)
print("FIVE-FOLD VALIDATION")
print("-" * 78)

print(fold_validation.to_string(index=False))

# ---------------------------------------------------------
# 11. SAVE OUTPUTS
# ---------------------------------------------------------

output_columns = [
    "match_id",
    "innings",
    "season",
    "striker_id",
    "striker_name",
    "bowler_id",
    "bowler_name",
    "legal_balls_before",
    "over_segment",
    "scaled_innings_phase",
    "runs_before",
    "expected_runs_before",
    "runs_below_par",
    "wickets_before",
    "wickets_in_hand_before",
    "scheduled_legal_balls",
    "benchmark_level",
    "benchmark_training_matches",
    "validation_fold",
    "signal_below_par",
    "signal_low_wickets",
    "signal_early_collapse",
    "first_innings_pressure_signal_count",
    "is_first_innings_pressure",
    "first_innings_pressure_severity",
]

df[output_columns].to_csv(
    REPORTS / "t20i_first_innings_par_deliveries.csv.gz",
    index=False,
    compression="gzip",
)

coverage_by_level.to_csv(
    REPORTS / "t20i_first_innings_benchmark_levels.csv",
    index=False,
)

season_validation.to_csv(
    REPORTS / "t20i_first_innings_par_season_validation.csv",
    index=False,
)

phase_summary.to_csv(
    REPORTS / "t20i_first_innings_pressure_by_phase.csv",
    index=False,
)

fold_validation.to_csv(
    REPORTS / "t20i_first_innings_par_fold_validation.csv",
    index=False,
)

summary = {
    "first_innings_deliveries": int(len(df)),
    "first_innings_matches": int(df["match_id"].nunique()),
    "validation_folds": 5,
    "benchmark_covered_deliveries": int((~uncovered).sum()),
    "uncovered_deliveries": int(uncovered.sum()),
    "pressure_deliveries": int(
        df["is_first_innings_pressure"].sum()
    ),
    "pressure_percentage": round(
        float(df["is_first_innings_pressure"].mean() * 100),
        3,
    ),
    "severe_pressure_deliveries": int(
        (df["first_innings_pressure_severity"] == "Severe").sum()
    ),
    "high_pressure_deliveries": int(
        (df["first_innings_pressure_severity"] == "High").sum()
    ),
    "benchmark_levels_used": {
        str(row["benchmark_level"]): int(row["deliveries"])
        for _, row in coverage_by_level.iterrows()
    },
    "minimum_training_matches": int(
        df["benchmark_training_matches"].min()
    ),
}

with open(
    REPORTS / "t20i_first_innings_par_benchmark_summary.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(summary, f, indent=4)

print("\n" + "=" * 78)
print("STEP 55 COMPLETED")
print("=" * 78)

print(json.dumps(summary, indent=4))
print("\nReports saved in:", REPORTS)
