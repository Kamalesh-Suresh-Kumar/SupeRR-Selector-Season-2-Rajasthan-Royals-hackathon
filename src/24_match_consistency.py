
from pathlib import Path

import pandas as pd
import numpy as np

# ============================================================
# SCRIPT 24: MATCH-BY-MATCH PRESSURE CONSISTENCY
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "reports" / "unified_pressure_deliveries.csv.gz"
BATTER_OUTPUT = BASE_DIR / "reports" / "batter_match_consistency.csv"
BOWLER_OUTPUT = BASE_DIR / "reports" / "bowler_match_consistency.csv"

print("Loading IPL data...")
df = pd.read_csv(INPUT_FILE, low_memory=False)

# ------------------------------------------------------------
# 1. RECREATE THE SELECTED PRESSURE DEFINITION
# ------------------------------------------------------------

df["is_pressure"] = False

# First innings: use the validated benchmark-based definition.
first = df["innings"] == 1
df.loc[first, "is_pressure"] = (
    df.loc[first, "is_pressure_delivery"].fillna(False).astype(bool)
)

# Second innings: Rule B.
second = df["innings"] == 2
df.loc[second, "is_pressure"] = (
    (df.loc[second, "required_run_rate_before"] >= 10)
    & (
        (df.loc[second, "wickets_in_hand_before"] <= 6)
        | (df.loc[second, "balls_remaining_before"] <= 30)
    )
)

df["is_pressure"] = df["is_pressure"].fillna(False)

# ------------------------------------------------------------
# 2. COMMON CLEANUP
# ------------------------------------------------------------

df["runs"] = pd.to_numeric(df["runs"], errors="coerce").fillna(0)
df["team_runs_this_delivery"] = pd.to_numeric(
    df["team_runs_this_delivery"], errors="coerce"
).fillna(0)

df["is_legal_ball"] = (
    df["is_legal_ball"].fillna(False).astype(bool)
)

df["extras_type_clean"] = (
    df["extras_type_clean"].fillna("").astype(str).str.lower()
)

df["match_id"] = df["match_id"].astype(str)
df["season"] = df["season"].astype(str)

# ------------------------------------------------------------
# 3. BATTER MATCH-LEVEL CONSISTENCY
# ------------------------------------------------------------

print("Calculating batter consistency...")

bat = df.dropna(subset=["striker_id", "striker_name"]).copy()

# A wide is not counted as a ball faced.
bat["balls_faced"] = (
    bat["extras_type_clean"] != "wide"
).astype(int)

# Pressure and normal batting records.
bat_pressure = bat[bat["is_pressure"]].copy()
bat_normal = bat[~bat["is_pressure"]].copy()

# Overall normal baseline for each batter.
batter_baseline = (
    bat_normal.groupby(["striker_id", "striker_name"])
    .agg(
        normal_runs=("runs", "sum"),
        normal_balls=("balls_faced", "sum"),
        normal_deliveries=("match_id", "size"),
        normal_matches=("match_id", "nunique")
    )
    .reset_index()
)

batter_baseline["normal_strike_rate"] = np.where(
    batter_baseline["normal_balls"] > 0,
    batter_baseline["normal_runs"] * 100
    / batter_baseline["normal_balls"],
    np.nan
)

# Pressure performance in each individual match.
batter_match = (
    bat_pressure.groupby(
        ["striker_id", "striker_name", "match_id", "season"]
    )
    .agg(
        pressure_runs=("runs", "sum"),
        pressure_balls=("balls_faced", "sum"),
        pressure_deliveries=("match_id", "size")
    )
    .reset_index()
)

batter_match["pressure_strike_rate"] = np.where(
    batter_match["pressure_balls"] > 0,
    batter_match["pressure_runs"] * 100
    / batter_match["pressure_balls"],
    np.nan
)

# Compare each pressure match against the player's normal baseline.
batter_match = batter_match.merge(
    batter_baseline[
        [
            "striker_id",
            "normal_strike_rate",
            "normal_runs",
            "normal_balls",
            "normal_matches"
        ]
    ],
    on="striker_id",
    how="left",
    validate="many_to_one"
)

batter_match["strike_rate_difference"] = (
    batter_match["pressure_strike_rate"]
    - batter_match["normal_strike_rate"]
)

batter_match["outperformed_baseline"] = (
    batter_match["strike_rate_difference"] > 0
)

# Summarise match-level consistency.
batter_consistency = (
    batter_match.groupby(["striker_id", "striker_name"])
    .agg(
        pressure_matches=("match_id", "nunique"),
        pressure_runs=("pressure_runs", "sum"),
        pressure_balls=("pressure_balls", "sum"),
        average_match_pressure_runs=("pressure_runs", "mean"),
        average_match_pressure_sr=("pressure_strike_rate", "mean"),
        matches_above_baseline=("outperformed_baseline", "sum"),
        average_sr_difference=("strike_rate_difference", "mean"),
        normal_strike_rate=("normal_strike_rate", "first"),
        normal_matches=("normal_matches", "first")
    )
    .reset_index()
)

batter_consistency["consistency_percentage"] = (
    batter_consistency["matches_above_baseline"]
    / batter_consistency["pressure_matches"] * 100
)

batter_consistency["eligible_for_review"] = (
    (batter_consistency["pressure_matches"] >= 8)
    & (batter_consistency["pressure_balls"] >= 60)
)

batter_consistency = batter_consistency.sort_values(
    ["consistency_percentage", "pressure_matches", "pressure_runs"],
    ascending=[False, False, False]
)

# ------------------------------------------------------------
# 4. BOWLER MATCH-LEVEL CONSISTENCY
# ------------------------------------------------------------

print("Calculating bowler consistency...")

bowl = df.dropna(subset=["bowler_id", "bowler_name"]).copy()

# Byes and legbyes are not charged to the bowler.
bowl["bowler_runs_conceded"] = (
    bowl["team_runs_this_delivery"]
    - np.where(
        bowl["extras_type_clean"].isin(["byes", "legbyes"]),
        bowl["team_runs_this_delivery"] - bowl["runs"],
        0
    )
)

# Use explicit extras columns when available for accurate deductions.
if "extras1_runs" in bowl.columns:
    extras1 = pd.to_numeric(
        bowl["extras1_runs"], errors="coerce"
    ).fillna(0)
else:
    extras1 = pd.Series(0, index=bowl.index)

if "extras_2_runs" in bowl.columns:
    extras2 = pd.to_numeric(
        bowl["extras_2_runs"], errors="coerce"
    ).fillna(0)
else:
    extras2 = pd.Series(0, index=bowl.index)

# Deduct only byes and legbyes from the bowler's conceded runs.
bowl["bowler_runs_conceded"] = (
    bowl["team_runs_this_delivery"]
    - np.where(
        bowl["extras_type_clean"].isin(["byes", "legbyes"]),
        extras1 + extras2,
        0
    )
)

bowl["bowler_runs_conceded"] = (
    bowl["bowler_runs_conceded"].clip(lower=0)
)

# Bowler-credit dismissals only.
bowler_wicket_types = [
    "caught",
    "bowled",
    "lbw",
    "stump",
    "hitwicket"
]

bowl["bowler_wicket"] = (
    bowl["is_wicket"].fillna(False).astype(bool)
    & bowl["dismissal_type"].fillna("").str.lower().isin(
        bowler_wicket_types
    )
).astype(int)

bowl["bowler_legal_balls"] = (
    bowl["is_legal_ball"].astype(int)
)

# Overall normal bowling baseline.
bowl_normal = bowl[~bowl["is_pressure"]].copy()
bowl_pressure = bowl[bowl["is_pressure"]].copy()

bowler_baseline = (
    bowl_normal.groupby(["bowler_id", "bowler_name"])
    .agg(
        normal_runs_conceded=("bowler_runs_conceded", "sum"),
        normal_legal_balls=("bowler_legal_balls", "sum"),
        normal_wickets=("bowler_wicket", "sum"),
        normal_matches=("match_id", "nunique")
    )
    .reset_index()
)

bowler_baseline["normal_economy"] = np.where(
    bowler_baseline["normal_legal_balls"] > 0,
    bowler_baseline["normal_runs_conceded"] * 6
    / bowler_baseline["normal_legal_balls"],
    np.nan
)

# Pressure performance in each individual match.
bowler_match = (
    bowl_pressure.groupby(
        ["bowler_id", "bowler_name", "match_id", "season"]
    )
    .agg(
        pressure_runs_conceded=("bowler_runs_conceded", "sum"),
        pressure_legal_balls=("bowler_legal_balls", "sum"),
        pressure_wickets=("bowler_wicket", "sum")
    )
    .reset_index()
)

bowler_match["pressure_economy"] = np.where(
    bowler_match["pressure_legal_balls"] > 0,
    bowler_match["pressure_runs_conceded"] * 6
    / bowler_match["pressure_legal_balls"],
    np.nan
)

bowler_match = bowler_match.merge(
    bowler_baseline[
        [
            "bowler_id",
            "normal_economy",
            "normal_runs_conceded",
            "normal_legal_balls",
            "normal_wickets",
            "normal_matches"
        ]
    ],
    on="bowler_id",
    how="left",
    validate="many_to_one"
)

# Negative difference means the bowler conceded fewer runs per over.
bowler_match["economy_difference"] = (
    bowler_match["pressure_economy"]
    - bowler_match["normal_economy"]
)

bowler_match["outperformed_baseline"] = (
    bowler_match["economy_difference"] < 0
)

# Summarise match-level consistency.
bowler_consistency = (
    bowler_match.groupby(["bowler_id", "bowler_name"])
    .agg(
        pressure_matches=("match_id", "nunique"),
        pressure_runs_conceded=("pressure_runs_conceded", "sum"),
        pressure_legal_balls=("pressure_legal_balls", "sum"),
        pressure_wickets=("pressure_wickets", "sum"),
        average_match_pressure_economy=("pressure_economy", "mean"),
        matches_better_than_baseline=("outperformed_baseline", "sum"),
        average_economy_difference=("economy_difference", "mean"),
        normal_economy=("normal_economy", "first"),
        normal_matches=("normal_matches", "first")
    )
    .reset_index()
)

bowler_consistency["consistency_percentage"] = (
    bowler_consistency["matches_better_than_baseline"]
    / bowler_consistency["pressure_matches"] * 100
)

bowler_consistency["eligible_for_review"] = (
    (bowler_consistency["pressure_matches"] >= 8)
    & (bowler_consistency["pressure_legal_balls"] >= 120)
)

bowler_consistency = bowler_consistency.sort_values(
    [
        "consistency_percentage",
        "pressure_matches",
        "pressure_wickets"
    ],
    ascending=[False, False, False]
)

# ------------------------------------------------------------
# 5. SAVE OUTPUTS
# ------------------------------------------------------------

BATTER_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

batter_match.to_csv(
    BASE_DIR / "reports" / "batter_pressure_match_details.csv",
    index=False
)

bowler_match.to_csv(
    BASE_DIR / "reports" / "bowler_pressure_match_details.csv",
    index=False
)

batter_consistency.to_csv(BATTER_OUTPUT, index=False)
bowler_consistency.to_csv(BOWLER_OUTPUT, index=False)

# ------------------------------------------------------------
# 6. DISPLAY RESULTS
# ------------------------------------------------------------

print("\n" + "=" * 100)
print("MATCH-BY-MATCH PRESSURE CONSISTENCY")
print("=" * 100)

print("\nBATTERS — TOP 15 BY CONSISTENCY")
print("-" * 100)

print(
    batter_consistency[
        [
            "striker_name",
            "pressure_matches",
            "pressure_runs",
            "pressure_balls",
            "normal_strike_rate",
            "consistency_percentage",
            "average_sr_difference",
            "eligible_for_review"
        ]
    ].head(15).to_string(index=False)
)

print("\nBOWLERS — TOP 15 BY CONSISTENCY")
print("-" * 100)

print(
    bowler_consistency[
        [
            "bowler_name",
            "pressure_matches",
            "pressure_wickets",
            "pressure_legal_balls",
            "normal_economy",
            "consistency_percentage",
            "average_economy_difference",
            "eligible_for_review"
        ]
    ].head(15).to_string(index=False)
)

print("\nOUTPUT FILES")
print("Batter:", BATTER_OUTPUT)
print("Bowler:", BOWLER_OUTPUT)

print("\nSCRIPT 24 COMPLETED")
