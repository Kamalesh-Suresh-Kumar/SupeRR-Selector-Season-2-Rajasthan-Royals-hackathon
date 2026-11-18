
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "reports" / "unified_pressure_deliveries.csv.gz"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading unified pressure data...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

second = df[df["innings"] == 2].copy()

# Normalize signal columns
signal_columns = [
    "high_rrr_signal",
    "low_wickets_signal",
    "low_balls_signal"
]

for col in signal_columns:
    second[col] = second[col].fillna(False).astype(bool)

rrr = pd.to_numeric(
    second["required_run_rate_before"],
    errors="coerce"
)

# ---------------------------------------------------------
# 1. DEFINE ALTERNATIVE CHASE PRESSURE RULES
# ---------------------------------------------------------

high_rrr = second["high_rrr_signal"]
very_high_rrr = rrr >= 15

low_wickets = second["low_wickets_signal"]
low_balls = second["low_balls_signal"]

# Rule A: Current definition
second["rule_A_current"] = (
    second[signal_columns].sum(axis=1) >= 2
)

# Rule B: Require high RRR and at least one supporting signal
second["rule_B_chase_dependent"] = (
    high_rrr & (low_wickets | low_balls)
)

# Rule C: Very high RRR independently qualifies.
# Otherwise require high RRR and one supporting signal.
second["rule_C_flexible"] = (
    very_high_rrr
    | (high_rrr & (low_wickets | low_balls))
)

# Rule D: Stricter RRR threshold, with supporting signal
second["rule_D_strict"] = (
    (rrr >= 12)
    & (low_wickets | low_balls)
)

rules = [
    "rule_A_current",
    "rule_B_chase_dependent",
    "rule_C_flexible",
    "rule_D_strict"
]

# ---------------------------------------------------------
# 2. OVERALL RULE COMPARISON
# ---------------------------------------------------------

print("\nOVERALL CHASE PRESSURE COMPARISON")
print("=" * 80)

overall_rows = []

for rule in rules:

    count = int(second[rule].sum())

    overall_rows.append({
        "rule": rule,
        "pressure_deliveries": count,
        "total_deliveries": len(second),
        "pressure_percentage": count / len(second) * 100
    })

overall = pd.DataFrame(overall_rows)

print(overall.to_string(index=False))

# ---------------------------------------------------------
# 3. COMPARE RULES BY PHASE
# ---------------------------------------------------------

print("\nPRESSURE COMPARISON BY PHASE")
print("=" * 80)

phase_rows = []

for phase, group in second.groupby("innings_phase"):

    for rule in rules:

        count = int(group[rule].sum())

        phase_rows.append({
            "phase": phase,
            "rule": rule,
            "deliveries": len(group),
            "pressure_deliveries": count,
            "pressure_percentage": count / len(group) * 100
        })

phase_comparison = pd.DataFrame(phase_rows)

print(phase_comparison.to_string(index=False))

# ---------------------------------------------------------
# 4. COMPARE RULES BY SEASON
# ---------------------------------------------------------

print("\nPRESSURE COMPARISON BY SEASON")
print("=" * 80)

season_rows = []

for season, group in second.groupby("season"):

    for rule in rules:

        count = int(group[rule].sum())

        season_rows.append({
            "season": season,
            "rule": rule,
            "deliveries": len(group),
            "pressure_deliveries": count,
            "pressure_percentage": count / len(group) * 100
        })

season_comparison = pd.DataFrame(season_rows)

print(season_comparison.to_string(index=False))

# ---------------------------------------------------------
# 5. MATCH-LEVEL DISTRIBUTION
# ---------------------------------------------------------

print("\nMATCH-LEVEL PRESSURE DISTRIBUTION")
print("=" * 80)

match_rows = []

for rule in rules:

    match_summary = (
        second.groupby(["match_id", "season"])
        .agg(
            deliveries=("match_id", "size"),
            pressure_deliveries=(rule, "sum")
        )
        .reset_index()
    )

    match_summary["pressure_percentage"] = (
        match_summary["pressure_deliveries"]
        / match_summary["deliveries"] * 100
    )

    match_rows.append({
        "rule": rule,
        "matches": len(match_summary),
        "average_pressure_percentage": (
            match_summary["pressure_percentage"].mean()
        ),
        "median_pressure_percentage": (
            match_summary["pressure_percentage"].median()
        ),
        "p25": match_summary["pressure_percentage"].quantile(0.25),
        "p75": match_summary["pressure_percentage"].quantile(0.75),
        "maximum": match_summary["pressure_percentage"].max()
    })

match_distribution = pd.DataFrame(match_rows)

print(match_distribution.to_string(index=False))

# ---------------------------------------------------------
# 6. OVERLAP BETWEEN RULES
# ---------------------------------------------------------

print("\nRULE OVERLAP")
print("=" * 80)

overlap = pd.DataFrame({
    "comparison": [
        "A and B",
        "A and C",
        "A and D",
        "B and C",
        "B and D",
        "C and D"
    ],
    "common_pressure_deliveries": [
        int((second["rule_A_current"] & second["rule_B_chase_dependent"]).sum()),
        int((second["rule_A_current"] & second["rule_C_flexible"]).sum()),
        int((second["rule_A_current"] & second["rule_D_strict"]).sum()),
        int((second["rule_B_chase_dependent"] & second["rule_C_flexible"]).sum()),
        int((second["rule_B_chase_dependent"] & second["rule_D_strict"]).sum()),
        int((second["rule_C_flexible"] & second["rule_D_strict"]).sum())
    ]
})

print(overlap.to_string(index=False))

# ---------------------------------------------------------
# 7. FIRST INNINGS REFERENCE
# ---------------------------------------------------------

first = df[df["innings"] == 1].copy()

first_summary = (
    first.groupby("innings_phase")
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=("is_pressure_delivery", "sum")
    )
    .reset_index()
)

first_summary["pressure_percentage"] = (
    first_summary["pressure_deliveries"]
    / first_summary["deliveries"] * 100
)

print("\nFIRST INNINGS REFERENCE")
print("=" * 80)
print(first_summary.to_string(index=False))

# ---------------------------------------------------------
# 8. SAVE REPORTS
# ---------------------------------------------------------

overall.to_csv(
    REPORT_DIR / "pressure_rule_overall_comparison.csv",
    index=False
)

phase_comparison.to_csv(
    REPORT_DIR / "pressure_rule_phase_comparison.csv",
    index=False
)

season_comparison.to_csv(
    REPORT_DIR / "pressure_rule_season_comparison.csv",
    index=False
)

match_distribution.to_csv(
    REPORT_DIR / "pressure_rule_match_distribution.csv",
    index=False
)

overlap.to_csv(
    REPORT_DIR / "pressure_rule_overlap.csv",
    index=False
)

first_summary.to_csv(
    REPORT_DIR / "first_innings_pressure_reference.csv",
    index=False
)

second.to_csv(
    REPORT_DIR / "pressure_rule_delivery_comparison.csv.gz",
    index=False,
    compression="gzip"
)

print("\nPRESSURE DEFINITION SENSITIVITY AUDIT COMPLETED")
print("Reports saved in:", REPORT_DIR)
