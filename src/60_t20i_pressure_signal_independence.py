
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
print("STEP 60: T20I FIRST-INNINGS PRESSURE SIGNAL INDEPENDENCE AUDIT")
print("=" * 78)

# ---------------------------------------------------------
# 1. LOAD DATA
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
]

missing = [
    column for column in required
    if column not in df.columns
]

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )

print("Delivery observations:", len(df))
print("Matches:", df["match_id"].nunique())

# ---------------------------------------------------------
# 2. PREPARE THE THREE PRESSURE SIGNALS
# ---------------------------------------------------------

df["match_id"] = df["match_id"].astype(str)

df["wickets_before"] = pd.to_numeric(
    df["wickets_before"],
    errors="coerce",
)

df["wickets_in_hand"] = (
    10 - df["wickets_before"]
)

df["runs_below_par"] = (
    df["expected_runs_before"] - df["runs_before"]
)

# Signal A:
# Actual score is at least 5 runs below expected score.

df["signal_below_par"] = (
    df["runs_below_par"] >= 5
)

# Signal B:
# Six or fewer wickets remain.

df["signal_wickets"] = (
    df["wickets_in_hand"] <= 6
)

# Signal C:
# Early collapse:
# No more than 30% of scheduled legal balls used
# and seven or fewer wickets remain.

df["innings_progress"] = (
    df["legal_balls_before"] /
    df["scheduled_legal_balls"]
)

df["signal_early_collapse"] = (
    (df["innings_progress"] <= 0.30) &
    (df["wickets_in_hand"] <= 7)
)

signal_columns = [
    "signal_below_par",
    "signal_wickets",
    "signal_early_collapse",
]

for column in signal_columns:
    df[column] = df[column].fillna(False).astype(bool)

# Count active signals.

df["signal_count"] = (
    df[signal_columns].sum(axis=1)
)

# Existing rule: at least two of three signals.

df["pressure_rule_2_of_3"] = (
    df["signal_count"] >= 2
)

# Independent contextual rule:
# Ignore the benchmark-dependent below-par signal.
# Require both wicket-related signals.

df["pressure_context_only"] = (
    df["signal_wickets"] &
    df["signal_early_collapse"]
)

# ---------------------------------------------------------
# 3. VERIFY EXISTING PRESSURE CLASSIFICATION
# ---------------------------------------------------------

if "is_first_innings_pressure" in df.columns:

    df["existing_pressure"] = (
        df["is_first_innings_pressure"]
        .fillna(False)
        .astype(bool)
    )

    df["pressure_label_mismatch"] = (
        df["existing_pressure"] !=
        df["pressure_rule_2_of_3"]
    )

    mismatch_count = int(
        df["pressure_label_mismatch"].sum()
    )

else:
    df["existing_pressure"] = np.nan
    df["pressure_label_mismatch"] = np.nan
    mismatch_count = None

# ---------------------------------------------------------
# 4. SIGNAL FREQUENCY AUDIT
# ---------------------------------------------------------

signal_names = {
    "signal_below_par": "Below par",
    "signal_wickets": "Six or fewer wickets in hand",
    "signal_early_collapse": "Early collapse",
}

signal_rows = []

for column, name in signal_names.items():

    selected = df[df[column]]

    signal_rows.append({
        "signal": name,
        "deliveries": len(selected),
        "percentage": (
            len(selected) / len(df) * 100
        ),
        "matches": selected["match_id"].nunique(),
        "mean_runs_below_par": (
            selected["runs_below_par"].mean()
        ),
        "mean_wickets_in_hand": (
            selected["wickets_in_hand"].mean()
        ),
    })

signal_summary = pd.DataFrame(signal_rows)

print("\n" + "-" * 78)
print("INDIVIDUAL PRESSURE SIGNAL FREQUENCY")
print("-" * 78)

print(signal_summary.to_string(index=False))

# ---------------------------------------------------------
# 5. SIGNAL COMBINATION AUDIT
# ---------------------------------------------------------

combination_names = {
    (False, False, False): "No signals",
    (True, False, False): "Below par only",
    (False, True, False): "Wickets only",
    (False, False, True): "Early collapse only",
    (True, True, False): "Below par + wickets",
    (True, False, True): "Below par + early collapse",
    (False, True, True): "Wickets + early collapse",
    (True, True, True): "All three signals",
}

df["signal_combination"] = list(
    zip(
        df["signal_below_par"],
        df["signal_wickets"],
        df["signal_early_collapse"],
    )
)

combination_rows = []

for combination, name in combination_names.items():

    selected = df[
        df["signal_combination"] == combination
    ]

    combination_rows.append({
        "combination": name,
        "deliveries": len(selected),
        "percentage": (
            len(selected) / len(df) * 100
        ),
        "matches": selected["match_id"].nunique(),
        "mean_runs_below_par": (
            selected["runs_below_par"].mean()
        ),
        "mean_wickets_in_hand": (
            selected["wickets_in_hand"].mean()
        ),
        "pressure_under_2_of_3": (
            bool(sum(combination) >= 2)
        ),
    })

combination_summary = pd.DataFrame(
    combination_rows
)

print("\n" + "-" * 78)
print("ALL EIGHT SIGNAL COMBINATIONS")
print("-" * 78)

print(
    combination_summary.to_string(index=False)
)

# ---------------------------------------------------------
# 6. PRESSURE RULE COMPARISON
# ---------------------------------------------------------

rule_rows = []

rules = {
    "Below par only": df["signal_below_par"],
    "Wickets only": df["signal_wickets"],
    "Early collapse only": df["signal_early_collapse"],
    "Wickets + early collapse": df["pressure_context_only"],
    "At least two of three": df["pressure_rule_2_of_3"],
}

for name, rule in rules.items():

    selected = df[rule]

    rule_rows.append({
        "rule": name,
        "deliveries": len(selected),
        "percentage": (
            len(selected) / len(df) * 100
        ),
        "matches": selected["match_id"].nunique(),
        "mean_runs_below_par": (
            selected["runs_below_par"].mean()
        ),
        "mean_wickets_in_hand": (
            selected["wickets_in_hand"].mean()
        ),
    })

rule_summary = pd.DataFrame(rule_rows)

print("\n" + "-" * 78)
print("PRESSURE RULE COMPARISON")
print("-" * 78)

print(rule_summary.to_string(index=False))

# ---------------------------------------------------------
# 7. PHASE-WISE SIGNAL ANALYSIS
# ---------------------------------------------------------

phase_column = None

for column in [
    "scaled_innings_phase",
    "innings_phase",
    "phase",
]:
    if column in df.columns:
        phase_column = column
        break

if phase_column is not None:

    phase_rows = []

    for phase, group in df.groupby(
        phase_column,
        dropna=False,
    ):

        phase_rows.append({
            "phase": str(phase),
            "deliveries": len(group),
            "below_par_percentage": (
                group["signal_below_par"].mean() * 100
            ),
            "wickets_signal_percentage": (
                group["signal_wickets"].mean() * 100
            ),
            "early_collapse_percentage": (
                group["signal_early_collapse"].mean() * 100
            ),
            "context_only_pressure_percentage": (
                group["pressure_context_only"].mean() * 100
            ),
            "two_of_three_pressure_percentage": (
                group["pressure_rule_2_of_3"].mean() * 100
            ),
        })

    phase_summary = pd.DataFrame(phase_rows)

    print("\n" + "-" * 78)
    print("SIGNAL ANALYSIS BY INNINGS PHASE")
    print("-" * 78)

    print(phase_summary.to_string(index=False))

else:
    phase_summary = pd.DataFrame()
    print("\nPhase column unavailable. Phase audit skipped.")

# ---------------------------------------------------------
# 8. SEASON-WISE SIGNAL ANALYSIS
# ---------------------------------------------------------

season_summary = (
    df.groupby("season")
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        below_par_percentage=(
            "signal_below_par",
            lambda x: x.mean() * 100,
        ),
        wickets_signal_percentage=(
            "signal_wickets",
            lambda x: x.mean() * 100,
        ),
        early_collapse_percentage=(
            "signal_early_collapse",
            lambda x: x.mean() * 100,
        ),
        context_only_pressure_percentage=(
            "pressure_context_only",
            lambda x: x.mean() * 100,
        ),
        two_of_three_pressure_percentage=(
            "pressure_rule_2_of_3",
            lambda x: x.mean() * 100,
        ),
    )
    .reset_index()
)

print("\n" + "-" * 78)
print("SIGNAL ANALYSIS BY SEASON")
print("-" * 78)

print(season_summary.to_string(index=False))

# ---------------------------------------------------------
# 9. EXISTING RULE RECONCILIATION
# ---------------------------------------------------------

if mismatch_count is not None:

    print("\n" + "-" * 78)
    print("EXISTING PRESSURE RULE RECONCILIATION")
    print("-" * 78)

    print("Mismatched delivery labels:", mismatch_count)

    print(
        "Mismatch percentage:",
        round(mismatch_count / len(df) * 100, 4),
    )

    reconciliation = pd.crosstab(
        df["existing_pressure"],
        df["pressure_rule_2_of_3"],
        rownames=["Existing pressure"],
        colnames=["Reconstructed pressure"],
    )

    print(reconciliation.to_string())

else:
    reconciliation = pd.DataFrame()
    print("\nExisting pressure label unavailable.")

# ---------------------------------------------------------
# 10. INDEPENDENT CONTEXT PRESSURE BY WICKET BAND
# ---------------------------------------------------------

df["wicket_band"] = pd.cut(
    10 - df["wickets_in_hand"],
    bins=[-1, 1, 3, 5, 7, 10],
    labels=[
        "0-1 wickets lost",
        "2-3 wickets lost",
        "4-5 wickets lost",
        "6-7 wickets lost",
        "8-10 wickets lost",
    ],
)

wicket_context_summary = (
    df.groupby(
        "wicket_band",
        observed=True,
    )
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        context_only_pressure_percentage=(
            "pressure_context_only",
            lambda x: x.mean() * 100,
        ),
        two_of_three_pressure_percentage=(
            "pressure_rule_2_of_3",
            lambda x: x.mean() * 100,
        ),
    )
    .reset_index()
)

print("\n" + "-" * 78)
print("PRESSURE BY WICKET-LOSS BAND")
print("-" * 78)

print(wicket_context_summary.to_string(index=False))

# ---------------------------------------------------------
# 11. OVERALL SUMMARY
# ---------------------------------------------------------

overall = {
    "delivery_observations": int(len(df)),
    "matches": int(df["match_id"].nunique()),
    "below_par_deliveries": int(
        df["signal_below_par"].sum()
    ),
    "wickets_signal_deliveries": int(
        df["signal_wickets"].sum()
    ),
    "early_collapse_deliveries": int(
        df["signal_early_collapse"].sum()
    ),
    "two_of_three_pressure_deliveries": int(
        df["pressure_rule_2_of_3"].sum()
    ),
    "context_only_pressure_deliveries": int(
        df["pressure_context_only"].sum()
    ),
    "existing_rule_mismatches": mismatch_count,
    "phase_column_used": phase_column,
}

# ---------------------------------------------------------
# 12. SAVE REPORTS
# ---------------------------------------------------------

df.to_csv(
    REPORTS / "t20i_pressure_signal_delivery_audit.csv.gz",
    index=False,
    compression="gzip",
)

signal_summary.to_csv(
    REPORTS / "t20i_pressure_signal_frequency.csv",
    index=False,
)

combination_summary.to_csv(
    REPORTS / "t20i_pressure_signal_combinations.csv",
    index=False,
)

rule_summary.to_csv(
    REPORTS / "t20i_pressure_rule_comparison.csv",
    index=False,
)

phase_summary.to_csv(
    REPORTS / "t20i_pressure_signals_by_phase.csv",
    index=False,
)

season_summary.to_csv(
    REPORTS / "t20i_pressure_signals_by_season.csv",
    index=False,
)

wicket_context_summary.to_csv(
    REPORTS / "t20i_pressure_signals_by_wickets.csv",
    index=False,
)

if not reconciliation.empty:
    reconciliation.to_csv(
        REPORTS / "t20i_pressure_rule_reconciliation.csv"
    )

with open(
    REPORTS / "t20i_pressure_signal_audit_summary.json",
    "w",
    encoding="utf-8",
) as f:
    json.dump(overall, f, indent=4)

print("\n" + "=" * 78)
print("STEP 60 COMPLETED")
print("=" * 78)

print(json.dumps(overall, indent=4))

print("\nReports saved in:", REPORTS)
