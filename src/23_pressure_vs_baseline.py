
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "reports" / "unified_pressure_deliveries.csv.gz"
REPORT_DIR = ROOT / "reports"

print("Loading IPL data...")
df = pd.read_csv(INPUT_FILE, low_memory=False)

# --------------------------------------------------
# 1. PRESSURE CLASSIFICATION
# --------------------------------------------------

df["pressure"] = False

first = df["innings"] == 1
second = df["innings"] == 2

df.loc[first, "pressure"] = (
    df.loc[first, "is_pressure_delivery"]
    .fillna(False)
    .astype(bool)
)

df.loc[second, "pressure"] = (
    (df.loc[second, "required_run_rate_before"] >= 10) &
    (
        (df.loc[second, "wickets_in_hand_before"] <= 6) |
        (df.loc[second, "balls_remaining_before"] <= 30)
    )
)

df["extras"] = (
    df["extras_type_clean"].fillna("").str.lower()
)

df["dismissal"] = (
    df["dismissal_type"]
    .fillna("")
    .str.lower()
    .str.replace(" ", "", regex=False)
)

df["innings_key"] = (
    df["match_id"].astype(str) + "_" +
    df["innings"].astype(str)
)

# --------------------------------------------------
# 2. BATTER METRICS
# --------------------------------------------------

df["batter_ball"] = (df["extras"] != "wide").astype(int)

df["batter_out"] = (
    (df["is_wicket"] == 1) &
    (df["dismissed_player_id"] == df["striker_id"])
).astype(int)

df["batter_boundary"] = (
    df["is_four"].astype(bool) |
    df["is_six"].astype(bool)
).astype(int)

# Aggregate pressure and non-pressure separately.
batter = (
    df.groupby(
        ["striker_id", "striker_name", "pressure"],
        dropna=False
    )
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        innings=("innings_key", "nunique"),
        runs=("runs", "sum"),
        balls=("batter_ball", "sum"),
        dismissals=("batter_out", "sum"),
        boundaries=("batter_boundary", "sum")
    )
    .reset_index()
)

batter["strike_rate"] = np.where(
    batter["balls"] > 0,
    batter["runs"] * 100 / batter["balls"],
    np.nan
)

batter["dismissal_rate"] = np.where(
    batter["dismissals"] > 0,
    batter["balls"] / batter["dismissals"],
    np.nan
)

batter["boundary_percentage"] = np.where(
    batter["balls"] > 0,
    batter["boundaries"] * 100 / batter["balls"],
    np.nan
)

# Convert pressure/non-pressure rows into columns.
batter_pivot = batter.pivot(
    index=["striker_id", "striker_name"],
    columns="pressure",
    values=[
        "deliveries", "matches", "innings",
        "runs", "balls", "dismissals",
        "boundaries", "strike_rate",
        "dismissal_rate", "boundary_percentage"
    ]
)

batter_pivot.columns = [
    f"{metric}_{'pressure' if flag else 'normal'}"
    for metric, flag in batter_pivot.columns
]

batter_pivot = batter_pivot.reset_index()

for col in [
    "strike_rate",
    "dismissal_rate",
    "boundary_percentage"
]:
    p = f"{col}_pressure"
    n = f"{col}_normal"

    batter_pivot[f"{col}_difference"] = (
        batter_pivot[p] - batter_pivot[n]
    )

batter_pivot["pressure_balls"] = (
    batter_pivot["balls_pressure"].fillna(0)
)

batter_pivot["pressure_matches"] = (
    batter_pivot["matches_pressure"].fillna(0)
)

batter_pivot.to_csv(
    REPORT_DIR / "batter_pressure_vs_baseline.csv",
    index=False
)

# --------------------------------------------------
# 3. BOWLER METRICS
# --------------------------------------------------

# Byes and leg-byes are not charged to the bowler.
df["bowler_runs"] = df["team_runs_this_delivery"]

not_charged = df["extras"].isin(["byes", "legbyes"])

df.loc[not_charged, "bowler_runs"] -= (
    df.loc[not_charged, "extras1_runs"] +
    df.loc[not_charged, "extras_2_runs"]
)

# Dot balls: legal deliveries on which the batting team
# scores zero total runs.
df["bowler_dot"] = (
    (df["is_legal_ball"] == 1) &
    (df["team_runs_this_delivery"] == 0)
).astype(int)

# Credited bowler wickets only.
credit_types = {
    "caught", "bowled", "lbw",
    "stump", "hitwicket"
}

df["bowler_wicket"] = (
    (df["is_wicket"] == 1) &
    (df["dismissal"] .isin(credit_types))
).astype(int)

df["bowler_boundary"] = (
    df["is_four"].astype(bool) |
    df["is_six"].astype(bool)
).astype(int)

bowler = (
    df.groupby(
        ["bowler_id", "bowler_name", "pressure"],
        dropna=False
    )
    .agg(
        deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        innings=("innings_key", "nunique"),
        runs_conceded=("bowler_runs", "sum"),
        legal_balls=("is_legal_ball", "sum"),
        wickets=("bowler_wicket", "sum"),
        dot_balls=("bowler_dot", "sum"),
        boundaries=("bowler_boundary", "sum")
    )
    .reset_index()
)

bowler["economy"] = np.where(
    bowler["legal_balls"] > 0,
    bowler["runs_conceded"] * 6 / bowler["legal_balls"],
    np.nan
)

bowler["wickets_per_100"] = np.where(
    bowler["legal_balls"] > 0,
    bowler["wickets"] * 100 / bowler["legal_balls"],
    np.nan
)

bowler["dot_percentage"] = np.where(
    bowler["legal_balls"] > 0,
    bowler["dot_balls"] * 100 / bowler["legal_balls"],
    np.nan
)

bowler["boundary_percentage"] = np.where(
    bowler["legal_balls"] > 0,
    bowler["boundaries"] * 100 / bowler["legal_balls"],
    np.nan
)

bowler_pivot = bowler.pivot(
    index=["bowler_id", "bowler_name"],
    columns="pressure",
    values=[
        "deliveries", "matches", "innings",
        "runs_conceded", "legal_balls",
        "wickets", "dot_balls", "boundaries",
        "economy", "wickets_per_100",
        "dot_percentage", "boundary_percentage"
    ]
)

bowler_pivot.columns = [
    f"{metric}_{'pressure' if flag else 'normal'}"
    for metric, flag in bowler_pivot.columns
]

bowler_pivot = bowler_pivot.reset_index()

# Negative economy difference is favourable.
bowler_pivot["economy_difference"] = (
    bowler_pivot["economy_pressure"] -
    bowler_pivot["economy_normal"]
)

# Positive differences are favourable for these metrics.
for metric in ["wickets_per_100", "dot_percentage"]:
    bowler_pivot[f"{metric}_difference"] = (
        bowler_pivot[f"{metric}_pressure"] -
        bowler_pivot[f"{metric}_normal"]
    )

bowler_pivot["pressure_balls"] = (
    bowler_pivot["legal_balls_pressure"].fillna(0)
)

bowler_pivot["pressure_matches"] = (
    bowler_pivot["matches_pressure"].fillna(0)
)

bowler_pivot.to_csv(
    REPORT_DIR / "bowler_pressure_vs_baseline.csv",
    index=False
)

# --------------------------------------------------
# 4. SUMMARY
# --------------------------------------------------

print("\n" + "=" * 90)
print("PRESSURE VS NORMAL PERFORMANCE")
print("=" * 90)

print("\nBATTER COMPARISON — TOP PRESSURE RUN SCORERS")
print("-" * 90)

print(
    batter_pivot.sort_values(
        "runs_pressure",
        ascending=False
    )[
        [
            "striker_name",
            "runs_pressure",
            "balls_pressure",
            "strike_rate_pressure",
            "strike_rate_normal",
            "strike_rate_difference",
            "pressure_matches"
        ]
    ].head(15).to_string(index=False)
)

print("\nBOWLER COMPARISON — TOP PRESSURE WICKET TAKERS")
print("-" * 90)

print(
    bowler_pivot.sort_values(
        "wickets_pressure",
        ascending=False
    )[
        [
            "bowler_name",
            "wickets_pressure",
            "legal_balls_pressure",
            "economy_pressure",
            "economy_normal",
            "economy_difference",
            "pressure_matches"
        ]
    ].head(15).to_string(index=False)
)

print("\nOUTPUT FILES")
print("Batter:", REPORT_DIR / "batter_pressure_vs_baseline.csv")
print("Bowler:", REPORT_DIR / "bowler_pressure_vs_baseline.csv")

print("\nSCRIPT 23 COMPLETED")
