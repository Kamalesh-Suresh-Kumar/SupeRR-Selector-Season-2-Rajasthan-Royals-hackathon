
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

print("\n" + "=" * 75)
print("STEP 52: T20I PRESSURE CONTEXT VALIDATION")
print("=" * 75)

# ---------------------------------------------------------
# 1. LOAD PRESSURE DATA
# ---------------------------------------------------------

df = pd.read_csv(
    REPORTS / "t20i_pressure_context_deliveries.csv.gz",
    low_memory=False
)

print("Delivery rows:", len(df))

# ---------------------------------------------------------
# 2. BUILD ONE ROW PER INNINGS
# ---------------------------------------------------------

group_columns = [
    "match_id",
    "innings",
    "season",
    "scheduled_legal_balls",
    "scheduled_limit_source",
]

innings_audit = (
    df.groupby(group_columns, dropna=False)
    .agg(
        delivery_records=("match_id", "size"),
        actual_legal_balls=("cumulative_legal_balls", "max"),
        final_score=("cumulative_team_runs", "max"),
        final_wickets=("cumulative_wickets", "max"),
    )
    .reset_index()
)

innings_audit["limit_difference"] = (
    innings_audit["scheduled_legal_balls"] -
    innings_audit["actual_legal_balls"]
)

innings_audit["actual_exceeds_limit"] = (
    innings_audit["limit_difference"] < 0
)

innings_audit["finished_at_limit"] = (
    innings_audit["limit_difference"] == 0
)

innings_audit["finished_before_limit"] = (
    innings_audit["limit_difference"] > 0
)

print("\n" + "-" * 75)
print("INNINGS LIMIT VALIDATION")
print("-" * 75)

print("Total innings:", len(innings_audit))
print(
    "Actual innings legal balls equal scheduled limit:",
    int(innings_audit["finished_at_limit"].sum())
)
print(
    "Actual innings legal balls below scheduled limit:",
    int(innings_audit["finished_before_limit"].sum())
)
print(
    "Actual innings legal balls above scheduled limit:",
    int(innings_audit["actual_exceeds_limit"].sum())
)

print("\nScheduled limit source:")
print(
    innings_audit["scheduled_limit_source"]
    .value_counts(dropna=False)
    .to_string()
)

# ---------------------------------------------------------
# 3. REVISED LIMIT COVERAGE
# ---------------------------------------------------------

revised = innings_audit[
    innings_audit["scheduled_limit_source"] == "source_revised_limit"
].copy()

standard = innings_audit[
    innings_audit["scheduled_limit_source"] == "standard_120_ball_default"
].copy()

print("\n" + "-" * 75)
print("REVISED LIMIT INNINGS")
print("-" * 75)

print("Innings with revised limits:", len(revised))

if len(revised):
    print(
        revised[
            [
                "match_id",
                "innings",
                "season",
                "scheduled_legal_balls",
                "actual_legal_balls",
                "final_score",
                "final_wickets",
                "limit_difference",
            ]
        ].to_string(index=False)
    )

# ---------------------------------------------------------
# 4. CHECK FIXED PHASE BOUNDARIES
# ---------------------------------------------------------

# Current phase boundaries:
# Powerplay: legal balls before 36
# Middle:    legal balls before 90
# Death:     legal balls before 90 or more

shortened = innings_audit[
    innings_audit["scheduled_legal_balls"] < 120
].copy()

shortened_ids = shortened[["match_id", "innings"]]

shortened_deliveries = df.merge(
    shortened_ids,
    on=["match_id", "innings"],
    how="inner"
)

print("\n" + "-" * 75)
print("SHORTENED INNINGS PHASE AUDIT")
print("-" * 75)

print("Shortened innings:", len(shortened))
print("Deliveries in shortened innings:", len(shortened_deliveries))

print("\nCurrent phase distribution in shortened innings:")

if len(shortened_deliveries):
    print(
        shortened_deliveries["innings_phase"]
        .value_counts()
        .to_string()
    )

print("\nShortened innings by scheduled legal-ball limit:")
print(
    shortened["scheduled_legal_balls"]
    .value_counts()
    .sort_index()
    .to_string()
)

# ---------------------------------------------------------
# 5. CHECK PRESSURE LABEL LOGIC
# ---------------------------------------------------------

second = df[df["innings"] == 2].copy()

eligible_chase = (
    second["chase_target"].notna() &
    (second["balls_remaining_before"] > 0) &
    (second["runs_required_before"] > 0)
)

expected_pressure = (
    (second["required_run_rate_before"] >= 10) &
    (
        (second["wickets_in_hand_before"] <= 6) |
        (second["balls_remaining_before"] <= 30)
    )
)

expected_pressure = expected_pressure & eligible_chase

mismatch = (
    second["is_chase_pressure"].astype(bool) != expected_pressure
)

print("\n" + "-" * 75)
print("CHASE PRESSURE RULE RECONCILIATION")
print("-" * 75)

print("Second-innings deliveries:", len(second))
print("Eligible chase deliveries:", int(eligible_chase.sum()))
print("Pressure-label mismatches:", int(mismatch.sum()))
print(
    "Pressure deliveries:",
    int(second["is_chase_pressure"].sum())
)

# ---------------------------------------------------------
# 6. CHECK RRR EXTREMES
# ---------------------------------------------------------

rrr = second["required_run_rate_before"].dropna()

print("\n" + "-" * 75)
print("REQUIRED RUN RATE DISTRIBUTION")
print("-" * 75)

if len(rrr):
    print(rrr.describe(
        percentiles=[0.50, 0.75, 0.90, 0.95, 0.99]
    ).to_string())

    print("Maximum RRR:", float(rrr.max()))

# ---------------------------------------------------------
# 7. SAVE AUDIT OUTPUTS
# ---------------------------------------------------------

innings_audit.to_csv(
    REPORTS / "t20i_pressure_innings_limit_audit.csv",
    index=False
)

shortened_deliveries.to_csv(
    REPORTS / "t20i_shortened_innings_phase_audit.csv",
    index=False
)

summary = {
    "delivery_rows": int(len(df)),
    "innings_rows": int(len(innings_audit)),
    "innings_equal_to_limit": int(
        innings_audit["finished_at_limit"].sum()
    ),
    "innings_below_limit": int(
        innings_audit["finished_before_limit"].sum()
    ),
    "innings_above_limit": int(
        innings_audit["actual_exceeds_limit"].sum()
    ),
    "innings_with_revised_limits": int(len(revised)),
    "innings_using_standard_default": int(len(standard)),
    "shortened_innings": int(len(shortened)),
    "shortened_innings_delivery_rows": int(len(shortened_deliveries)),
    "pressure_rule_mismatches": int(mismatch.sum()),
    "second_innings_pressure_deliveries": int(
        second["is_chase_pressure"].sum()
    ),
    "max_required_run_rate": (
        float(rrr.max()) if len(rrr) else None
    ),
}

with open(
    REPORTS / "t20i_pressure_context_validation_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)

print("\n" + "=" * 75)
print("STEP 52 COMPLETED")
print("=" * 75)

print(json.dumps(summary, indent=4))
print("\nReports saved in:", REPORTS)
