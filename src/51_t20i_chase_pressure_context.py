
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

print("\n" + "=" * 75)
print("STEP 51: T20I CHASE PRESSURE CONTEXT")
print("=" * 75)

# ---------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------

df = pd.read_csv(
    REPORTS / "t20i_reconstructed_deliveries.csv.gz",
    low_memory=False
)

innings = pd.read_csv(
    REPORTS / "t20i_reconstructed_innings_summary.csv"
)

matches = pd.read_csv(
    REPORTS / "t20i_match_target_reconciliation.csv"
)

print("Delivery records:", len(df))
print("Innings records:", len(innings))
print("Match records:", len(matches))



# ---------------------------------------------------------
# 2. BUILD MATCH TARGET AND INNINGS METADATA
# ---------------------------------------------------------

# Add match-level target information.
target_columns = [
    "match_id",
    "first_innings_runs",
    "second_innings_runs",
    "ordinary_target",
    "effective_target",
    "target_source",
]

target_lookup = matches[target_columns].drop_duplicates("match_id")

df = df.merge(
    target_lookup,
    on="match_id",
    how="left",
    validate="many_to_one"
)

# Revised limits must come from the innings summary.
innings_metadata_columns = [
    "match_id",
    "innings",
    "first_inn_revised_overs",
    "second_inn_revised_overs",
]

innings_metadata = innings[innings_metadata_columns].copy()

df = df.merge(
    innings_metadata,
    on=["match_id", "innings"],
    how="left",
    validate="many_to_one"
)

# Add season from the original competition metadata.
raw_matches = pd.read_csv(
    ROOT / "data" / "raw" / "matches.csv"
)

competitions = pd.read_csv(
    ROOT / "data" / "raw" / "competitions.csv"
)

competitions["match_format"] = (
    competitions["match_format"].astype(str).str.strip().str.upper()
)

t20i_competitions = competitions[
    competitions["match_format"] == "T20I"
][["comp_id", "season"]]

season_lookup = raw_matches[
    ["match_id", "comp_id"]
].merge(
    t20i_competitions,
    on="comp_id",
    how="inner",
    validate="many_to_one"
)[["match_id", "season"]].drop_duplicates("match_id")

if "season" not in df.columns:
    df = df.merge(
        season_lookup,
        on="match_id",
        how="left",
        validate="many_to_one"
    )

print("\nMetadata merge validation:")
print("Missing effective targets:", int(df["effective_target"].isna().sum()))
print("Missing first revised limits:", int(df["first_inn_revised_overs"].isna().sum()))
print("Missing second revised limits:", int(df["second_inn_revised_overs"].isna().sum()))
print("Missing seasons:", int(df["season"].isna().sum()))


# ---------------------------------------------------------
# 3. DETERMINE SCHEDULED LEGAL BALLS
# ---------------------------------------------------------

df["scheduled_legal_balls"] = np.where(
    df["innings"] == 1,
    df["first_inn_revised_overs"],
    df["second_inn_revised_overs"]
)

df["scheduled_legal_balls"] = pd.to_numeric(
    df["scheduled_legal_balls"],
    errors="coerce"
)

# Source revised values are provisionally interpreted as
# legal-ball limits. Standard T20I default is 120 balls.
df["scheduled_limit_source"] = np.where(
    df["scheduled_legal_balls"].notna(),
    "source_revised_limit",
    "standard_120_ball_default"
)

df["scheduled_legal_balls"] = (
    df["scheduled_legal_balls"].fillna(120)
)

# ---------------------------------------------------------
# 4. SORT DELIVERY RECORDS
# ---------------------------------------------------------

sort_columns = [
    "match_id",
    "innings",
    "overid",
    "over_ball_num",
    "innings_ball_num",
]

df = df.sort_values(sort_columns).reset_index(drop=True)

# ---------------------------------------------------------
# 5. CALCULATE PRE-DELIVERY SCORE AND WICKETS
# ---------------------------------------------------------

df["team_runs"] = pd.to_numeric(
    df["team_runs"], errors="coerce"
).fillna(0)

df["is_wicket_clean"] = (
    df["is_wicket_clean"].fillna(False).astype(bool)
)

df["cumulative_wickets"] = pd.to_numeric(
    df["cumulative_wickets"], errors="coerce"
).fillna(0)

df["legal_balls_before"] = pd.to_numeric(
    df["legal_balls_before"], errors="coerce"
).fillna(0)

# The reconstructed cumulative fields include the current
# delivery. Subtract the current delivery to obtain the
# state immediately before it.
df["runs_before"] = (
    df["cumulative_team_runs"] - df["team_runs"]
)

df["wickets_before"] = (
    df["cumulative_wickets"] -
    df["is_wicket_clean"].astype(int)
)

df["wickets_before"] = (
    df["wickets_before"].clip(lower=0, upper=10)
)

# ---------------------------------------------------------
# 6. CALCULATE BALLS REMAINING
# ---------------------------------------------------------

df["balls_remaining_before"] = (
    df["scheduled_legal_balls"] -
    df["legal_balls_before"]
)

df["balls_remaining_before"] = (
    df["balls_remaining_before"].clip(lower=0)
)

df["wickets_in_hand_before"] = (
    10 - df["wickets_before"]
)

# ---------------------------------------------------------
# 7. CALCULATE SECOND-INNINGS TARGET AND RRR
# ---------------------------------------------------------

df["chase_target"] = np.where(
    df["innings"] == 2,
    df["effective_target"],
    np.nan
)

df["runs_required_before"] = (
    df["chase_target"] - df["runs_before"]
)

valid_chase = (
    (df["innings"] == 2) &
    df["chase_target"].notna() &
    (df["balls_remaining_before"] > 0) &
    (df["runs_required_before"] > 0)
)

df["required_run_rate_before"] = np.nan

df.loc[valid_chase, "required_run_rate_before"] = (
    df.loc[valid_chase, "runs_required_before"] * 6 /
    df.loc[valid_chase, "balls_remaining_before"]
)

# ---------------------------------------------------------
# 8. APPLY PROVISIONAL CHASE PRESSURE RULE
# ---------------------------------------------------------

# Rule B:
# RRR >= 10 AND
# (wickets in hand <= 6 OR balls remaining <= 30)

df["is_chase_pressure"] = False

df.loc[valid_chase, "is_chase_pressure"] = (
    (
        df.loc[valid_chase, "required_run_rate_before"] >= 10
    ) &
    (
        (df.loc[valid_chase, "wickets_in_hand_before"] <= 6) |
        (df.loc[valid_chase, "balls_remaining_before"] <= 30)
    )
)

# Completed chases are not under active chase pressure.
df.loc[
    (df["innings"] == 2) &
    (df["runs_required_before"] <= 0),
    "is_chase_pressure"
] = False

# ---------------------------------------------------------
# 9. ASSIGN INNINGS PHASE
# ---------------------------------------------------------

def get_phase(row):
    ball = row["legal_balls_before"]

    if ball < 36:
        return "Powerplay"
    elif ball < 90:
        return "Middle"
    return "Death"

df["innings_phase"] = df.apply(get_phase, axis=1)

# ---------------------------------------------------------
# 10. VALIDATION
# ---------------------------------------------------------

print("\n" + "-" * 75)
print("PRE-DELIVERY STATE VALIDATION")
print("-" * 75)

print(
    "Missing runs before:",
    int(df["runs_before"].isna().sum())
)

print(
    "Missing wickets before:",
    int(df["wickets_before"].isna().sum())
)

print(
    "Missing legal balls before:",
    int(df["legal_balls_before"].isna().sum())
)

print(
    "Negative runs before:",
    int((df["runs_before"] < 0).sum())
)

print(
    "Wickets outside 0-10:",
    int(
        (
            (df["wickets_before"] < 0) |
            (df["wickets_before"] > 10)
        ).sum()
    )
)

print(
    "Negative balls remaining:",
    int((df["balls_remaining_before"] < 0).sum())
)

# ---------------------------------------------------------
# 11. PRESSURE DISTRIBUTION
# ---------------------------------------------------------

second = df[df["innings"] == 2].copy()

pressure_summary = (
    second.groupby("innings_phase")
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=("is_chase_pressure", "sum"),
        avg_required_rate=("required_run_rate_before", "mean"),
    )
    .reset_index()
)

pressure_summary["pressure_percentage"] = (
    pressure_summary["pressure_deliveries"] /
    pressure_summary["deliveries"] * 100
)

print("\n" + "-" * 75)
print("SECOND-INNINGS PRESSURE BY PHASE")
print("-" * 75)

print(pressure_summary.to_string(index=False))

print(
    "\nTotal second-innings deliveries:",
    len(second)
)

print(
    "Second-innings pressure deliveries:",
    int(second["is_chase_pressure"].sum())
)

# ---------------------------------------------------------
# 12. PRESSURE BY SEASON
# ---------------------------------------------------------

season_summary = (
    second.groupby("season")
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=("is_chase_pressure", "sum"),
    )
    .reset_index()
)

season_summary["pressure_percentage"] = (
    season_summary["pressure_deliveries"] /
    season_summary["deliveries"] * 100
)

print("\n" + "-" * 75)
print("PRESSURE BY SEASON")
print("-" * 75)

print(season_summary.to_string(index=False))

# ---------------------------------------------------------
# 13. SAVE OUTPUTS
# ---------------------------------------------------------

df.to_csv(
    REPORTS / "t20i_pressure_context_deliveries.csv.gz",
    index=False,
    compression="gzip"
)

pressure_summary.to_csv(
    REPORTS / "t20i_chase_pressure_by_phase.csv",
    index=False
)

season_summary.to_csv(
    REPORTS / "t20i_chase_pressure_by_season.csv",
    index=False
)

summary = {
    "delivery_rows": int(len(df)),
    "second_innings_deliveries": int(len(second)),
    "second_innings_pressure_deliveries": int(
        second["is_chase_pressure"].sum()
    ),
    "second_innings_pressure_percentage": round(
        float(second["is_chase_pressure"].mean() * 100), 2
    ),
    "missing_runs_before": int(df["runs_before"].isna().sum()),
    "missing_wickets_before": int(df["wickets_before"].isna().sum()),
    "negative_balls_remaining": int(
        (df["balls_remaining_before"] < 0).sum()
    ),
    "revised_limit_rows": int(
        (df["scheduled_limit_source"] == "source_revised_limit").sum()
    ),
    "default_limit_rows": int(
        (df["scheduled_limit_source"] == "standard_120_ball_default").sum()
    ),
}

with open(
    REPORTS / "t20i_chase_pressure_context_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)

print("\n" + "=" * 75)
print("STEP 51 COMPLETED")
print("=" * 75)

print(json.dumps(summary, indent=4))
print("\nReports saved in:", REPORTS)
