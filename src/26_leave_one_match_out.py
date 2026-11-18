
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT = BASE_DIR / "reports" / "unified_pressure_deliveries.csv.gz"
REPORTS = BASE_DIR / "reports"

print("Loading IPL data...")
df = pd.read_csv(INPUT, low_memory=False)

# ============================================================
# 1. PRESSURE DEFINITION
# ============================================================

df["is_pressure"] = False

first = df["innings"] == 1
second = df["innings"] == 2

df.loc[first, "is_pressure"] = (
    df.loc[first, "is_pressure_delivery"].fillna(False).astype(bool)
)

df.loc[second, "is_pressure"] = (
    (df.loc[second, "required_run_rate_before"] >= 10)
    & (
        (df.loc[second, "wickets_in_hand_before"] <= 6)
        | (df.loc[second, "balls_remaining_before"] <= 30)
    )
)

df["is_pressure"] = df["is_pressure"].fillna(False)

# ============================================================
# 2. COMMON CLEANUP
# ============================================================

df["match_id"] = df["match_id"].astype(str)
df["season"] = df["season"].astype(str)

df["runs"] = pd.to_numeric(
    df["runs"], errors="coerce"
).fillna(0)

df["team_runs_this_delivery"] = pd.to_numeric(
    df["team_runs_this_delivery"], errors="coerce"
).fillna(0)

df["is_legal_ball"] = (
    df["is_legal_ball"].fillna(False).astype(bool)
)

df["extras_type_clean"] = (
    df["extras_type_clean"].fillna("").astype(str).str.lower()
)

# ============================================================
# 3. BATTER MATCH DATA
# ============================================================

print("Calculating leave-one-match-out batter metrics...")

bat = df.dropna(
    subset=["striker_id", "striker_name"]
).copy()

bat["balls_faced"] = (
    bat["extras_type_clean"] != "wide"
).astype(int)

# Aggregate normal deliveries by player and match.
bat_normal = bat[~bat["is_pressure"]].groupby(
    ["striker_id", "striker_name", "match_id"]
).agg(
    normal_runs=("runs", "sum"),
    normal_balls=("balls_faced", "sum")
).reset_index()

# Aggregate pressure deliveries by player and match.
bat_pressure = bat[bat["is_pressure"]].groupby(
    ["striker_id", "striker_name", "match_id", "season"]
).agg(
    pressure_runs=("runs", "sum"),
    pressure_balls=("balls_faced", "sum")
).reset_index()

# All normal performance for each player.
bat_total_normal = (
    bat_normal.groupby(["striker_id", "striker_name"])
    .agg(
        total_normal_runs=("normal_runs", "sum"),
        total_normal_balls=("normal_balls", "sum"),
        normal_matches=("match_id", "nunique")
    )
    .reset_index()
)

bat_match = bat_pressure.merge(
    bat_total_normal,
    on=["striker_id", "striker_name"],
    how="left",
    validate="many_to_one"
)

# Remove normal deliveries from the same match.
bat_match = bat_match.merge(
    bat_normal,
    on=["striker_id", "striker_name", "match_id"],
    how="left",
    validate="one_to_one"
)

bat_match[["normal_runs", "normal_balls"]] = (
    bat_match[["normal_runs", "normal_balls"]].fillna(0)
)

bat_match["other_match_normal_runs"] = (
    bat_match["total_normal_runs"] - bat_match["normal_runs"]
)

bat_match["other_match_normal_balls"] = (
    bat_match["total_normal_balls"] - bat_match["normal_balls"]
)

bat_match["pressure_sr"] = np.where(
    bat_match["pressure_balls"] > 0,
    bat_match["pressure_runs"] * 100 / bat_match["pressure_balls"],
    np.nan
)

bat_match["leave_one_out_normal_sr"] = np.where(
    bat_match["other_match_normal_balls"] > 0,
    bat_match["other_match_normal_runs"] * 100
    / bat_match["other_match_normal_balls"],
    np.nan
)

bat_match["sr_difference"] = (
    bat_match["pressure_sr"] - bat_match["leave_one_out_normal_sr"]
)

bat_match["outperformed_baseline"] = (
    bat_match["sr_difference"] > 0
)

# A comparison is valid only if the player has normal balls
# in other matches.
bat_match["valid_comparison"] = (
    bat_match["other_match_normal_balls"] > 0
)

bat_valid = bat_match[bat_match["valid_comparison"]].copy()

batter_result = (
    bat_valid.groupby(["striker_id", "striker_name"])
    .agg(
        pressure_matches=("match_id", "nunique"),
        pressure_runs=("pressure_runs", "sum"),
        pressure_balls=("pressure_balls", "sum"),
        matches_above_baseline=("outperformed_baseline", "sum"),
        average_sr_difference=("sr_difference", "mean"),
        normal_matches=("normal_matches", "first")
    )
    .reset_index()
)

batter_result["consistency_percentage"] = (
    batter_result["matches_above_baseline"]
    / batter_result["pressure_matches"] * 100
)

batter_result["pressure_strike_rate"] = (
    batter_result["pressure_runs"] * 100
    / batter_result["pressure_balls"]
)

batter_result["eligible"] = (
    (batter_result["pressure_matches"] >= 8)
    & (batter_result["pressure_balls"] >= 100)
    & (batter_result["normal_matches"] >= 8)
)

batter_result = batter_result.sort_values(
    ["eligible", "consistency_percentage", "pressure_runs"],
    ascending=[False, False, False]
)

# ============================================================
# 4. BOWLER MATCH DATA
# ============================================================

print("Calculating leave-one-match-out bowler metrics...")

bowl = df.dropna(
    subset=["bowler_id", "bowler_name"]
).copy()

extras1 = pd.to_numeric(
    bowl["extras1_runs"], errors="coerce"
).fillna(0)

extras2 = pd.to_numeric(
    bowl["extras_2_runs"], errors="coerce"
).fillna(0)

bowl["bowler_runs"] = (
    bowl["team_runs_this_delivery"]
    - np.where(
        bowl["extras_type_clean"].isin(["byes", "legbyes"]),
        extras1 + extras2,
        0
    )
).clip(lower=0)

bowl["legal_balls"] = bowl["is_legal_ball"].astype(int)

bowler_wicket_types = [
    "caught", "bowled", "lbw", "stump", "hitwicket"
]

bowl["bowler_wickets"] = (
    bowl["is_wicket"].fillna(False).astype(bool)
    & bowl["dismissal_type"].fillna("").str.lower().isin(
        bowler_wicket_types
    )
).astype(int)

# Normal performance by player and match.
bowl_normal = bowl[~bowl["is_pressure"]].groupby(
    ["bowler_id", "bowler_name", "match_id"]
).agg(
    normal_runs=("bowler_runs", "sum"),
    normal_balls=("legal_balls", "sum")
).reset_index()

# Pressure performance by player and match.
bowl_pressure = bowl[bowl["is_pressure"]].groupby(
    ["bowler_id", "bowler_name", "match_id", "season"]
).agg(
    pressure_runs=("bowler_runs", "sum"),
    pressure_balls=("legal_balls", "sum"),
    pressure_wickets=("bowler_wickets", "sum")
).reset_index()

bowl_total_normal = (
    bowl_normal.groupby(["bowler_id", "bowler_name"])
    .agg(
        total_normal_runs=("normal_runs", "sum"),
        total_normal_balls=("normal_balls", "sum"),
        normal_matches=("match_id", "nunique")
    )
    .reset_index()
)

bowl_match = bowl_pressure.merge(
    bowl_total_normal,
    on=["bowler_id", "bowler_name"],
    how="left",
    validate="many_to_one"
)

bowl_match = bowl_match.merge(
    bowl_normal,
    on=["bowler_id", "bowler_name", "match_id"],
    how="left",
    validate="one_to_one"
)

bowl_match[["normal_runs", "normal_balls"]] = (
    bowl_match[["normal_runs", "normal_balls"]].fillna(0)
)

bowl_match["other_match_normal_runs"] = (
    bowl_match["total_normal_runs"] - bowl_match["normal_runs"]
)

bowl_match["other_match_normal_balls"] = (
    bowl_match["total_normal_balls"] - bowl_match["normal_balls"]
)

bowl_match["pressure_economy"] = np.where(
    bowl_match["pressure_balls"] > 0,
    bowl_match["pressure_runs"] * 6 / bowl_match["pressure_balls"],
    np.nan
)

bowl_match["leave_one_out_normal_economy"] = np.where(
    bowl_match["other_match_normal_balls"] > 0,
    bowl_match["other_match_normal_runs"] * 6
    / bowl_match["other_match_normal_balls"],
    np.nan
)

bowl_match["economy_difference"] = (
    bowl_match["pressure_economy"]
    - bowl_match["leave_one_out_normal_economy"]
)

bowl_match["outperformed_baseline"] = (
    bowl_match["economy_difference"] < 0
)

bowl_match["valid_comparison"] = (
    bowl_match["other_match_normal_balls"] > 0
)

bowl_valid = bowl_match[bowl_match["valid_comparison"]].copy()

bowler_result = (
    bowl_valid.groupby(["bowler_id", "bowler_name"])
    .agg(
        pressure_matches=("match_id", "nunique"),
        pressure_runs_conceded=("pressure_runs", "sum"),
        pressure_legal_balls=("pressure_balls", "sum"),
        pressure_wickets=("pressure_wickets", "sum"),
        matches_better_than_baseline=("outperformed_baseline", "sum"),
        average_economy_difference=("economy_difference", "mean"),
        normal_matches=("normal_matches", "first")
    )
    .reset_index()
)

bowler_result["consistency_percentage"] = (
    bowler_result["matches_better_than_baseline"]
    / bowler_result["pressure_matches"] * 100
)

bowler_result["pressure_economy"] = (
    bowler_result["pressure_runs_conceded"] * 6
    / bowler_result["pressure_legal_balls"]
)

bowler_result["eligible"] = (
    (bowler_result["pressure_matches"] >= 8)
    & (bowler_result["pressure_legal_balls"] >= 120)
    & (bowler_result["normal_matches"] >= 8)
)

bowler_result = bowler_result.sort_values(
    ["eligible", "consistency_percentage", "pressure_wickets"],
    ascending=[False, False, False]
)

# ============================================================
# 5. SAVE RESULTS
# ============================================================

batter_result.to_csv(
    REPORTS / "batter_leave_one_out_consistency.csv",
    index=False
)

bowler_result.to_csv(
    REPORTS / "bowler_leave_one_out_consistency.csv",
    index=False
)

bat_match.to_csv(
    REPORTS / "batter_leave_one_out_match_details.csv",
    index=False
)

bowl_match.to_csv(
    REPORTS / "bowler_leave_one_out_match_details.csv",
    index=False
)

# ============================================================
# 6. DISPLAY
# ============================================================

print("\n" + "=" * 100)
print("LEAVE-ONE-MATCH-OUT BATTER RESULTS")
print("=" * 100)

print(
    batter_result[
        [
            "striker_name",
            "pressure_matches",
            "pressure_runs",
            "pressure_balls",
            "consistency_percentage",
            "average_sr_difference",
            "eligible"
        ]
    ].head(20).to_string(index=False)
)

print("\n" + "=" * 100)
print("LEAVE-ONE-MATCH-OUT BOWLER RESULTS")
print("=" * 100)

print(
    bowler_result[
        [
            "bowler_name",
            "pressure_matches",
            "pressure_wickets",
            "pressure_legal_balls",
            "consistency_percentage",
            "average_economy_difference",
            "eligible"
        ]
    ].head(20).to_string(index=False)
)

print("\nELIGIBILITY COUNTS")
print("Batters:", int(batter_result["eligible"].sum()))
print("Bowlers:", int(bowler_result["eligible"].sum()))

print("\nSCRIPT 26 COMPLETED")
