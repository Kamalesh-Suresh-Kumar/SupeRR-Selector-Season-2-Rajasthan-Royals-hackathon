
from pathlib import Path
import json
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

INPUT_FILE = (
    REPORTS / "t20i_first_innings_par_deliveries.csv.gz"
)

print("\n" + "=" * 78)
print("STEP 61: T20I PRESSURE MODEL SENSITIVITY AND ROBUSTNESS")
print("=" * 78)

# ---------------------------------------------------------
# 1. LOAD AND VALIDATE DATA
# ---------------------------------------------------------

df = pd.read_csv(INPUT_FILE, low_memory=False)

required = [
    "match_id",
    "season",
    "legal_balls_before",
    "scheduled_legal_balls",
    "runs_before",
    "expected_runs_before",
    "wickets_before",
    "scaled_innings_phase",
]

missing = [
    column for column in required
    if column not in df.columns
]

if missing:
    raise ValueError(f"Missing columns: {missing}")

df["match_id"] = df["match_id"].astype(str)

numeric_columns = [
    "legal_balls_before",
    "scheduled_legal_balls",
    "runs_before",
    "expected_runs_before",
    "wickets_before",
]

for column in numeric_columns:
    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    )

df = df.dropna(
    subset=numeric_columns
).copy()

if (df["scheduled_legal_balls"] <= 0).any():
    raise ValueError("Invalid scheduled legal-ball limit found.")

if (df["wickets_before"] < 0).any():
    raise ValueError("Negative wickets-before value found.")

if (df["wickets_before"] > 10).any():
    raise ValueError("Wickets-before value exceeds 10.")

df["wickets_in_hand"] = (
    10 - df["wickets_before"]
)

df["runs_below_par"] = (
    df["expected_runs_before"] -
    df["runs_before"]
)

df["innings_progress"] = (
    df["legal_balls_before"] /
    df["scheduled_legal_balls"]
)

print("Valid delivery observations:", len(df))
print("Matches:", df["match_id"].nunique())

# ---------------------------------------------------------
# 2. DEFINE SCENARIOS
# ---------------------------------------------------------

scenarios = {
    "Strict": {
        "below_par": 10,
        "wickets_in_hand": 5,
        "early_progress": 0.25,
        "early_wickets_in_hand": 7,
    },
    "Primary": {
        "below_par": 5,
        "wickets_in_hand": 6,
        "early_progress": 0.30,
        "early_wickets_in_hand": 7,
    },
    "Flexible": {
        "below_par": 3,
        "wickets_in_hand": 7,
        "early_progress": 0.35,
        "early_wickets_in_hand": 7,
    },
}

# ---------------------------------------------------------
# 3. BUILD SIGNALS FOR EACH SCENARIO
# ---------------------------------------------------------

scenario_results = []
rule_results = []

for scenario_name, settings in scenarios.items():

    signal_a = (
        df["runs_below_par"] >= settings["below_par"]
    )

    signal_b = (
        df["wickets_in_hand"] <=
        settings["wickets_in_hand"]
    )

    signal_c = (
        (df["innings_progress"] <=
         settings["early_progress"]) &
        (df["wickets_in_hand"] <=
         settings["early_wickets_in_hand"])
    )

    signal_count = (
        signal_a.astype(int) +
        signal_b.astype(int) +
        signal_c.astype(int)
    )

    # Store the signals for detailed analysis.

    df[f"{scenario_name}_below_par"] = signal_a
    df[f"{scenario_name}_wickets"] = signal_b
    df[f"{scenario_name}_early_collapse"] = signal_c
    df[f"{scenario_name}_signal_count"] = signal_count

    # Compare one-of-three, two-of-three and three-of-three.

    for required_signals in [1, 2, 3]:

        column = (
            f"{scenario_name}_pressure_{required_signals}_of_3"
        )

        df[column] = (
            signal_count >= required_signals
        )

        selected = df[df[column]]

        rule_results.append({
            "scenario": scenario_name,
            "rule": f"{required_signals}_of_3",
            "required_signals": required_signals,
            "pressure_deliveries": len(selected),
            "pressure_percentage": (
                len(selected) / len(df) * 100
            ),
            "matches": selected["match_id"].nunique(),
        })

    # Store the main two-of-three classification.

    primary_column = (
        f"{scenario_name}_pressure_2_of_3"
    )

    scenario_results.append({
        "scenario": scenario_name,
        "below_par_threshold": settings["below_par"],
        "wickets_in_hand_threshold": settings["wickets_in_hand"],
        "early_progress_threshold": settings["early_progress"],
        "early_collapse_wickets_in_hand": (
            settings["early_wickets_in_hand"]
        ),
        "pressure_deliveries": int(
            df[primary_column].sum()
        ),
        "pressure_percentage": (
            df[primary_column].mean() * 100
        ),
        "matches": int(
            df.loc[df[primary_column], "match_id"].nunique()
        ),
    })

scenario_summary = pd.DataFrame(scenario_results)
rule_summary = pd.DataFrame(rule_results)

print("\n" + "-" * 78)
print("THRESHOLD SCENARIO COMPARISON")
print("-" * 78)

print(scenario_summary.to_string(index=False))

print("\n" + "-" * 78)
print("ONE-OF-THREE, TWO-OF-THREE AND THREE-OF-THREE")
print("-" * 78)

print(rule_summary.to_string(index=False))

# ---------------------------------------------------------
# 4. COMPARE ALTERNATIVE LABELS WITH PRIMARY
# ---------------------------------------------------------

comparison_rows = []

primary = df["Primary_pressure_2_of_3"]

for scenario_name in ["Strict", "Flexible"]:

    alternative = df[
        f"{scenario_name}_pressure_2_of_3"
    ]

    both_true = int(
        (primary & alternative).sum()
    )

    either_true = int(
        (primary | alternative).sum()
    )

    same_labels = int(
        (primary == alternative).sum()
    )

    changed_labels = int(
        (primary != alternative).sum()
    )

    comparison_rows.append({
        "comparison": f"{scenario_name}_vs_Primary",
        "primary_pressure_deliveries": int(primary.sum()),
        "alternative_pressure_deliveries": int(
            alternative.sum()
        ),
        "common_pressure_deliveries": both_true,
        "changed_labels": changed_labels,
        "label_agreement_percentage": (
            same_labels / len(df) * 100
        ),
        "jaccard_similarity_percentage": (
            both_true / either_true * 100
            if either_true else 100
        ),
    })

comparison_summary = pd.DataFrame(
    comparison_rows
)

print("\n" + "-" * 78)
print("ALTERNATIVE MODEL AGREEMENT WITH PRIMARY")
print("-" * 78)

print(comparison_summary.to_string(index=False))

# ---------------------------------------------------------
# 5. PHASE-WISE COMPARISON
# ---------------------------------------------------------

phase_rows = []

for phase, group in df.groupby(
    "scaled_innings_phase",
    dropna=False,
):

    for scenario_name in scenarios:

        column = (
            f"{scenario_name}_pressure_2_of_3"
        )

        selected = group[column]

        phase_rows.append({
            "phase": str(phase),
            "scenario": scenario_name,
            "deliveries": len(group),
            "pressure_deliveries": int(selected.sum()),
            "pressure_percentage": (
                selected.mean() * 100
            ),
        })

phase_summary = pd.DataFrame(phase_rows)

print("\n" + "-" * 78)
print("PRESSURE CLASSIFICATION BY PHASE")
print("-" * 78)

print(phase_summary.to_string(index=False))

# ---------------------------------------------------------
# 6. SEASON-WISE COMPARISON
# ---------------------------------------------------------

season_rows = []

for season, group in df.groupby(
    "season",
    dropna=False,
):

    for scenario_name in scenarios:

        column = (
            f"{scenario_name}_pressure_2_of_3"
        )

        selected = group[column]

        season_rows.append({
            "season": str(season),
            "scenario": scenario_name,
            "deliveries": len(group),
            "matches": group["match_id"].nunique(),
            "pressure_deliveries": int(selected.sum()),
            "pressure_percentage": (
                selected.mean() * 100
            ),
        })

season_summary = pd.DataFrame(season_rows)

print("\n" + "-" * 78)
print("PRESSURE CLASSIFICATION BY SEASON")
print("-" * 78)

print(season_summary.to_string(index=False))

# ---------------------------------------------------------
# 7. MATCH COVERAGE AND MATCH-LEVEL PRESSURE RATE
# ---------------------------------------------------------

match_rows = []

for match_id, group in df.groupby(
    "match_id",
    sort=False,
):

    for scenario_name in scenarios:

        column = (
            f"{scenario_name}_pressure_2_of_3"
        )

        pressure_count = int(group[column].sum())

        match_rows.append({
            "match_id": match_id,
            "season": group["season"].iloc[0],
            "scenario": scenario_name,
            "deliveries": len(group),
            "pressure_deliveries": pressure_count,
            "pressure_percentage": (
                pressure_count / len(group) * 100
            ),
            "has_pressure": pressure_count > 0,
        })

match_summary = pd.DataFrame(match_rows)

match_coverage = (
    match_summary.groupby("scenario")
    .agg(
        matches=("match_id", "nunique"),
        matches_with_pressure=("has_pressure", "sum"),
        mean_match_pressure_percentage=(
            "pressure_percentage", "mean"
        ),
        median_match_pressure_percentage=(
            "pressure_percentage", "median"
        ),
    )
    .reset_index()
)

match_coverage["match_coverage_percentage"] = (
    match_coverage["matches_with_pressure"] /
    match_coverage["matches"] * 100
)

print("\n" + "-" * 78)
print("MATCH-LEVEL PRESSURE COVERAGE")
print("-" * 78)

print(match_coverage.to_string(index=False))

# ---------------------------------------------------------
# 8. PLAYER PRESSURE EXPOSURE COMPARISON
# ---------------------------------------------------------

player_rows = []

player_roles = [
    ("Batter", "striker_id", "striker_name"),
    ("Bowler", "bowler_id", "bowler_name"),
]

for role, id_column, name_column in player_roles:

    if id_column not in df.columns:
        print(
            f"\nSkipping {role} exposure: "
            f"{id_column} unavailable."
        )
        continue

    group_columns = [id_column]

    if name_column in df.columns:
        group_columns.append(name_column)

    for scenario_name in scenarios:

        pressure_column = (
            f"{scenario_name}_pressure_2_of_3"
        )

        selected = df[df[pressure_column]].copy()

        exposure = (
            selected.groupby(
                group_columns,
                dropna=False,
            )
            .agg(
                pressure_deliveries=("match_id", "size"),
                pressure_matches=("match_id", "nunique"),
            )
            .reset_index()
        )

        exposure["role"] = role
        exposure["scenario"] = scenario_name

        player_rows.append(exposure)

if player_rows:

    player_exposure = pd.concat(
        player_rows,
        ignore_index=True,
    )

else:
    player_exposure = pd.DataFrame()

# ---------------------------------------------------------
# 9. PLAYER EXPOSURE SUMMARY
# ---------------------------------------------------------

if not player_exposure.empty:

    player_exposure_summary = (
        player_exposure.groupby(
            ["role", "scenario"]
        )
        .agg(
            players=("pressure_matches", "size"),
            total_pressure_deliveries=(
                "pressure_deliveries", "sum"
            ),
            players_with_5_matches=(
                "pressure_matches",
                lambda x: (x >= 5).sum(),
            ),
            players_with_8_matches=(
                "pressure_matches",
                lambda x: (x >= 8).sum(),
            ),
        )
        .reset_index()
    )

    print("\n" + "-" * 78)
    print("PLAYER PRESSURE EXPOSURE")
    print("-" * 78)

    print(
        player_exposure_summary.to_string(index=False)
    )

else:
    player_exposure_summary = pd.DataFrame()

# ---------------------------------------------------------
# 10. SIGNAL THRESHOLD CONTRIBUTION
# ---------------------------------------------------------

signal_rows = []

for scenario_name in scenarios:

    for signal_type, suffix in [
        ("Below par", "below_par"),
        ("Wickets", "wickets"),
        ("Early collapse", "early_collapse"),
    ]:

        column = f"{scenario_name}_{suffix}"

        signal_rows.append({
            "scenario": scenario_name,
            "signal": signal_type,
            "deliveries": int(df[column].sum()),
            "percentage": df[column].mean() * 100,
        })

signal_summary = pd.DataFrame(signal_rows)

print("\n" + "-" * 78)
print("SIGNAL CONTRIBUTION BY SCENARIO")
print("-" * 78)

print(signal_summary.to_string(index=False))

# ---------------------------------------------------------
# 11. PRIMARY MODEL RECONCILIATION
# ---------------------------------------------------------

if "is_first_innings_pressure" in df.columns:

    existing = (
        df["is_first_innings_pressure"]
        .fillna(False)
        .astype(bool)
    )

    mismatch = (
        existing != df["Primary_pressure_2_of_3"]
    )

    primary_mismatch_count = int(mismatch.sum())

    print("\n" + "-" * 78)
    print("PRIMARY MODEL RECONCILIATION")
    print("-" * 78)

    print(
        "Existing label mismatches:",
        primary_mismatch_count,
    )

else:
    primary_mismatch_count = None

# ---------------------------------------------------------
# 12. OVERALL SUMMARY
# ---------------------------------------------------------

overall = {
    "delivery_observations": int(len(df)),
    "matches": int(df["match_id"].nunique()),
    "scenarios": scenarios,
    "strict_pressure_deliveries": int(
        df["Strict_pressure_2_of_3"].sum()
    ),
    "primary_pressure_deliveries": int(
        df["Primary_pressure_2_of_3"].sum()
    ),
    "flexible_pressure_deliveries": int(
        df["Flexible_pressure_2_of_3"].sum()
    ),
    "primary_model_mismatches": primary_mismatch_count,
}

# ---------------------------------------------------------
# 13. SAVE REPORTS
# ---------------------------------------------------------

scenario_summary.to_csv(
    REPORTS / "t20i_pressure_sensitivity_scenarios.csv",
    index=False,
)

rule_summary.to_csv(
    REPORTS / "t20i_pressure_sensitivity_rule_comparison.csv",
    index=False,
)

comparison_summary.to_csv(
    REPORTS / "t20i_pressure_sensitivity_model_agreement.csv",
    index=False,
)

phase_summary.to_csv(
    REPORTS / "t20i_pressure_sensitivity_by_phase.csv",
    index=False,
)

season_summary.to_csv(
    REPORTS / "t20i_pressure_sensitivity_by_season.csv",
    index=False,
)

match_summary.to_csv(
    REPORTS / "t20i_pressure_sensitivity_by_match.csv",
    index=False,
)

match_coverage.to_csv(
    REPORTS / "t20i_pressure_sensitivity_match_coverage.csv",
    index=False,
)

signal_summary.to_csv(
    REPORTS / "t20i_pressure_sensitivity_signal_contribution.csv",
    index=False,
)

if not player_exposure.empty:

    player_exposure.to_csv(
        REPORTS / "t20i_pressure_sensitivity_player_exposure.csv",
        index=False,
    )

    player_exposure_summary.to_csv(
        REPORTS / "t20i_pressure_sensitivity_player_summary.csv",
        index=False,
    )

with open(
    REPORTS / "t20i_pressure_sensitivity_summary.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(overall, f, indent=4)

print("\n" + "=" * 78)
print("STEP 61 COMPLETED")
print("=" * 78)

print(json.dumps(overall, indent=4))

print("\nReports saved in:", REPORTS)
