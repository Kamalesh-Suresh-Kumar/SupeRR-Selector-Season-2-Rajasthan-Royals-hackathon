
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

print("\n" + "=" * 75)
print("STEP 53: T20I SCALED PRESSURE SENSITIVITY")
print("=" * 75)

# ---------------------------------------------------------
# 1. LOAD EXISTING PRESSURE DATA
# ---------------------------------------------------------

df = pd.read_csv(
    REPORTS / "t20i_pressure_context_deliveries.csv.gz",
    low_memory=False
)

print("Delivery records:", len(df))

# ---------------------------------------------------------
# 2. VALIDATE REQUIRED FIELDS
# ---------------------------------------------------------

required = [
    "match_id",
    "innings",
    "season",
    "scheduled_legal_balls",
    "legal_balls_before",
    "balls_remaining_before",
    "required_run_rate_before",
    "wickets_in_hand_before",
    "is_chase_pressure",
]

missing = [col for col in required if col not in df.columns]

if missing:
    raise ValueError(f"Missing required fields: {missing}")

# ---------------------------------------------------------
# 3. CALCULATE PROPORTIONAL PHASE BOUNDARIES
# ---------------------------------------------------------

# Standard 120-ball innings:
# Powerplay = first 30% = 36 balls
# Middle = up to 75% = 90 balls
# Death = final 25% = 30 balls

df["powerplay_boundary"] = (
    df["scheduled_legal_balls"] * 0.30
)

df["death_start_boundary"] = (
    df["scheduled_legal_balls"] * 0.75
)

def scaled_phase(row):
    balls = row["legal_balls_before"]

    if balls < row["powerplay_boundary"]:
        return "Powerplay"

    elif balls < row["death_start_boundary"]:
        return "Middle"

    return "Death"

df["scaled_innings_phase"] = df.apply(
    scaled_phase,
    axis=1
)

# ---------------------------------------------------------
# 4. CALCULATE PROPORTIONAL LATE-INNINGS TRIGGER
# ---------------------------------------------------------

# Standard 120-ball innings:
# 25% remaining = 30 balls.

df["late_innings_ball_threshold"] = (
    df["scheduled_legal_balls"] * 0.25
)

df["is_late_innings_scaled"] = (
    df["balls_remaining_before"] <=
    df["late_innings_ball_threshold"]
)

# ---------------------------------------------------------
# 5. RECOMPUTE SCALED PRESSURE
# ---------------------------------------------------------

valid_chase = (
    (df["innings"] == 2) &
    df["chase_target"].notna() &
    (df["balls_remaining_before"] > 0) &
    (df["runs_required_before"] > 0) &
    df["required_run_rate_before"].notna()
)

df["is_chase_pressure_scaled"] = False

df.loc[valid_chase, "is_chase_pressure_scaled"] = (
    (
        df.loc[valid_chase, "required_run_rate_before"] >= 10
    ) &
    (
        (df.loc[valid_chase, "wickets_in_hand_before"] <= 6) |
        (
            df.loc[valid_chase, "balls_remaining_before"] <=
            df.loc[valid_chase, "late_innings_ball_threshold"]
        )
    )
)

# ---------------------------------------------------------
# 6. COMPARE OLD AND NEW PRESSURE LABELS
# ---------------------------------------------------------

second = df[df["innings"] == 2].copy()

second["old_pressure"] = (
    second["is_chase_pressure"].astype(bool)
)

second["new_pressure"] = (
    second["is_chase_pressure_scaled"].astype(bool)
)

second["pressure_changed"] = (
    second["old_pressure"] != second["new_pressure"]
)

comparison = (
    second.groupby(
        ["old_pressure", "new_pressure"]
    )
    .size()
    .reset_index(name="deliveries")
)

print("\n" + "-" * 75)
print("OLD VS SCALED PRESSURE LABELS")
print("-" * 75)

print(comparison.to_string(index=False))

print(
    "\nOld pressure deliveries:",
    int(second["old_pressure"].sum())
)

print(
    "Scaled pressure deliveries:",
    int(second["new_pressure"].sum())
)

print(
    "Changed pressure labels:",
    int(second["pressure_changed"].sum())
)

# ---------------------------------------------------------
# 7. COMPARE PRESSURE BY PHASE
# ---------------------------------------------------------

phase_summary = (
    second.groupby("scaled_innings_phase")
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=("new_pressure", "sum"),
    )
    .reset_index()
)

phase_summary["pressure_percentage"] = (
    phase_summary["pressure_deliveries"] /
    phase_summary["deliveries"] * 100
)

print("\n" + "-" * 75)
print("SCALED PHASE PRESSURE DISTRIBUTION")
print("-" * 75)

print(phase_summary.to_string(index=False))

# ---------------------------------------------------------
# 8. COMPARE STANDARD AND SHORTENED MATCHES
# ---------------------------------------------------------

second["match_length_type"] = (
    second["scheduled_legal_balls"].apply(
        lambda x: (
            "Standard_120_ball"
            if x >= 120
            else "Shortened"
        )
    )
)

length_summary = (
    second.groupby("match_length_type")
    .agg(
        deliveries=("match_id", "size"),
        old_pressure=("old_pressure", "sum"),
        scaled_pressure=("new_pressure", "sum"),
        changed_labels=("pressure_changed", "sum"),
    )
    .reset_index()
)

length_summary["old_pressure_percentage"] = (
    length_summary["old_pressure"] /
    length_summary["deliveries"] * 100
)

length_summary["scaled_pressure_percentage"] = (
    length_summary["scaled_pressure"] /
    length_summary["deliveries"] * 100
)

print("\n" + "-" * 75)
print("STANDARD VS SHORTENED MATCHES")
print("-" * 75)

print(length_summary.to_string(index=False))

# ---------------------------------------------------------
# 9. COMPARE BY SEASON
# ---------------------------------------------------------

season_summary = (
    second.groupby("season")
    .agg(
        deliveries=("match_id", "size"),
        old_pressure=("old_pressure", "sum"),
        scaled_pressure=("new_pressure", "sum"),
        changed_labels=("pressure_changed", "sum"),
    )
    .reset_index()
)

season_summary["scaled_pressure_percentage"] = (
    season_summary["scaled_pressure"] /
    season_summary["deliveries"] * 100
)

print("\n" + "-" * 75)
print("SCALED PRESSURE BY SEASON")
print("-" * 75)

print(season_summary.to_string(index=False))

# ---------------------------------------------------------
# 10. CHECK STANDARD MATCHES REMAIN UNCHANGED
# ---------------------------------------------------------

standard = second[
    second["scheduled_legal_balls"] >= 120
]

standard_changes = int(
    standard["pressure_changed"].sum()
)

print("\n" + "-" * 75)
print("STANDARD MATCH CONSISTENCY CHECK")
print("-" * 75)

print("Standard match deliveries:", len(standard))
print("Standard match pressure changes:", standard_changes)

# ---------------------------------------------------------
# 11. SAVE OUTPUTS
# ---------------------------------------------------------

df.to_csv(
    REPORTS / "t20i_pressure_context_scaled_deliveries.csv.gz",
    index=False,
    compression="gzip"
)

comparison.to_csv(
    REPORTS / "t20i_pressure_old_vs_scaled_comparison.csv",
    index=False
)

phase_summary.to_csv(
    REPORTS / "t20i_scaled_pressure_by_phase.csv",
    index=False
)

length_summary.to_csv(
    REPORTS / "t20i_scaled_pressure_by_match_length.csv",
    index=False
)

season_summary.to_csv(
    REPORTS / "t20i_scaled_pressure_by_season.csv",
    index=False
)

summary = {
    "total_deliveries": int(len(df)),
    "second_innings_deliveries": int(len(second)),
    "old_pressure_deliveries": int(second["old_pressure"].sum()),
    "scaled_pressure_deliveries": int(second["new_pressure"].sum()),
    "changed_pressure_labels": int(
        second["pressure_changed"].sum()
    ),
    "standard_match_pressure_changes": standard_changes,
    "shortened_match_deliveries": int(
        (second["match_length_type"] == "Shortened").sum()
    ),
}

with open(
    REPORTS / "t20i_scaled_pressure_sensitivity_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)

print("\n" + "=" * 75)
print("STEP 53 COMPLETED")
print("=" * 75)

print(json.dumps(summary, indent=4))
print("\nReports saved in:", REPORTS)
