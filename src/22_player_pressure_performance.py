
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = ROOT / "reports" / "unified_pressure_deliveries.csv.gz"
REPORT_DIR = ROOT / "reports"

REPORT_DIR.mkdir(exist_ok=True)

print("Loading IPL delivery data...")
df = pd.read_csv(INPUT_FILE, low_memory=False)

# --------------------------------------------------
# 1. PREPARE PRESSURE FLAGS
# --------------------------------------------------

print("\nPreparing pressure definitions...")

df["analysis_pressure_delivery"] = False

first = df["innings"] == 1
second = df["innings"] == 2

# First innings: existing benchmark-based definition
df.loc[first, "analysis_pressure_delivery"] = (
    df.loc[first, "is_pressure_delivery"]
    .fillna(False)
    .astype(bool)
)

# Second innings: Rule B
df.loc[second, "analysis_pressure_delivery"] = (
    (df.loc[second, "required_run_rate_before"] >= 10) &
    (
        (df.loc[second, "wickets_in_hand_before"] <= 6) |
        (df.loc[second, "balls_remaining_before"] <= 30)
    )
)

# Normalize text columns
df["extras_clean"] = (
    df["extras_type_clean"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)

df["dismissal_clean"] = (
    df["dismissal_type"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(" ", "", regex=False)
)

df["innings_key"] = (
    df["match_id"].astype(str) + "_" +
    df["innings"].astype(str)
)

# --------------------------------------------------
# 2. PREPARE BATTER METRICS
# --------------------------------------------------

print("Preparing batter metrics...")

# A batter faces a ball except on a wide.
df["batter_ball_faced"] = (
    df["extras_clean"] != "wide"
).astype(int)

df["batter_dismissed"] = (
    (df["is_wicket"] == 1) &
    (df["dismissed_player_id"] == df["striker_id"])
).astype(int)

df["batter_boundary"] = (
    df["is_four"].astype(bool) |
    df["is_six"].astype(bool)
).astype(int)

# --------------------------------------------------
# 3. PREPARE BOWLER METRICS
# --------------------------------------------------

print("Preparing bowler metrics...")

# Byes and leg-byes are not charged to the bowler.
# All other extras remain charged to the bowler.
df["bowler_runs_conceded"] = df["team_runs_this_delivery"]

not_bowler_charged = df["extras_clean"].isin(
    ["byes", "legbyes"]
)

df.loc[
    not_bowler_charged,
    "bowler_runs_conceded"
] -= (
    df.loc[not_bowler_charged, "extras1_runs"] +
    df.loc[not_bowler_charged, "extras_2_runs"]
)

# Conservative bowler-credit dismissal classification.
bowler_credit_types = {
    "caught",
    "bowled",
    "lbw",
    "stump",
    "hitwicket"
}

df["bowler_credit_wicket"] = (
    (df["is_wicket"] == 1) &
    (df["dismissal_clean"].isin(bowler_credit_types))
).astype(int)

df["bowler_dot_ball"] = (
    (df["is_legal_ball"] == 1) &
    (df["bowler_runs_conceded"] == 0)
).astype(int)

df["bowler_boundary_conceded"] = (
    df["is_four"].astype(bool) |
    df["is_six"].astype(bool)
).astype(int)

# --------------------------------------------------
# 4. AGGREGATION FUNCTION
# --------------------------------------------------

def aggregate_players(data, player_id, player_name, role):

    if role == "batter":

        grouped = data.groupby(
            [player_id, player_name],
            dropna=False
        ).agg(
            delivery_records=("match_id", "size"),
            matches=("match_id", "nunique"),
            innings=("innings_key", "nunique"),
            runs=("runs", "sum"),
            balls_faced=("batter_ball_faced", "sum"),
            fours=("is_four", "sum"),
            sixes=("is_six", "sum"),
            dismissals=("batter_dismissed", "sum"),
            pressure_deliveries=(
                "analysis_pressure_delivery", "sum"
            )
        ).reset_index()

        grouped["boundaries"] = (
            grouped["fours"] + grouped["sixes"]
        )

        grouped["strike_rate"] = np.where(
            grouped["balls_faced"] > 0,
            grouped["runs"] * 100 /
            grouped["balls_faced"],
            np.nan
        )

        grouped["boundary_percentage"] = np.where(
            grouped["balls_faced"] > 0,
            grouped["boundaries"] * 100 /
            grouped["balls_faced"],
            np.nan
        )

        grouped["dismissal_rate"] = np.where(
            grouped["dismissals"] > 0,
            grouped["balls_faced"] /
            grouped["dismissals"],
            np.nan
        )

        grouped["dot_balls"] = np.nan
        grouped["economy"] = np.nan
        grouped["wickets"] = np.nan

        return grouped

    grouped = data.groupby(
        [player_id, player_name],
        dropna=False
    ).agg(
        delivery_records=("match_id", "size"),
        matches=("match_id", "nunique"),
        innings=("innings_key", "nunique"),
        runs_conceded=("bowler_runs_conceded", "sum"),
        legal_balls=("is_legal_ball", "sum"),
        wickets=("bowler_credit_wicket", "sum"),
        dot_balls=("bowler_dot_ball", "sum"),
        boundaries_conceded=(
            "bowler_boundary_conceded", "sum"
        ),
        pressure_deliveries=(
            "analysis_pressure_delivery", "sum"
        )
    ).reset_index()

    grouped["overs"] = grouped["legal_balls"] / 6

    grouped["economy"] = np.where(
        grouped["legal_balls"] > 0,
        grouped["runs_conceded"] * 6 /
        grouped["legal_balls"],
        np.nan
    )

    grouped["dot_ball_percentage"] = np.where(
        grouped["legal_balls"] > 0,
        grouped["dot_balls"] * 100 /
        grouped["legal_balls"],
        np.nan
    )

    grouped["wickets_per_100_balls"] = np.where(
        grouped["legal_balls"] > 0,
        grouped["wickets"] * 100 /
        grouped["legal_balls"],
        np.nan
    )

    grouped["strike_rate"] = np.nan
    grouped["boundary_percentage"] = np.nan
    grouped["dismissal_rate"] = np.nan

    return grouped


# --------------------------------------------------
# 5. CREATE ALL-DELIVERY AND PRESSURE TABLES
# --------------------------------------------------

print("\nAggregating batter performances...")

batter_all = aggregate_players(
    df,
    "striker_id",
    "striker_name",
    "batter"
)

batter_pressure = aggregate_players(
    df[df["analysis_pressure_delivery"]],
    "striker_id",
    "striker_name",
    "batter"
)

batter_all["performance_scope"] = "All deliveries"
batter_pressure["performance_scope"] = "Pressure deliveries"

batter_all.to_csv(
    REPORT_DIR / "batter_all_delivery_performance.csv",
    index=False
)

batter_pressure.to_csv(
    REPORT_DIR / "batter_pressure_performance.csv",
    index=False
)

print("Batter tables saved.")

print("\nAggregating bowler performances...")

bowler_all = aggregate_players(
    df,
    "bowler_id",
    "bowler_name",
    "bowler"
)

bowler_pressure = aggregate_players(
    df[df["analysis_pressure_delivery"]],
    "bowler_id",
    "bowler_name",
    "bowler"
)

bowler_all["performance_scope"] = "All deliveries"
bowler_pressure["performance_scope"] = "Pressure deliveries"

bowler_all.to_csv(
    REPORT_DIR / "bowler_all_delivery_performance.csv",
    index=False
)

bowler_pressure.to_csv(
    REPORT_DIR / "bowler_pressure_performance.csv",
    index=False
)

print("Bowler tables saved.")

# --------------------------------------------------
# 6. PHASE-WISE PRESSURE PERFORMANCE
# --------------------------------------------------

print("\nCreating phase-wise pressure tables...")

pressure_data = df[
    df["analysis_pressure_delivery"]
].copy()

batter_phase = (
    pressure_data.groupby(
        ["striker_id", "striker_name", "innings_phase"],
        dropna=False
    )
    .agg(
        pressure_deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        runs=("runs", "sum"),
        balls_faced=("batter_ball_faced", "sum"),
        fours=("is_four", "sum"),
        sixes=("is_six", "sum"),
        dismissals=("batter_dismissed", "sum")
    )
    .reset_index()
)

batter_phase["strike_rate"] = np.where(
    batter_phase["balls_faced"] > 0,
    batter_phase["runs"] * 100 /
    batter_phase["balls_faced"],
    np.nan
)

batter_phase.to_csv(
    REPORT_DIR / "batter_pressure_by_phase.csv",
    index=False
)

bowler_phase = (
    pressure_data.groupby(
        ["bowler_id", "bowler_name", "innings_phase"],
        dropna=False
    )
    .agg(
        pressure_deliveries=("match_id", "size"),
        matches=("match_id", "nunique"),
        runs_conceded=("bowler_runs_conceded", "sum"),
        legal_balls=("is_legal_ball", "sum"),
        wickets=("bowler_credit_wicket", "sum"),
        dot_balls=("bowler_dot_ball", "sum"),
        boundaries_conceded=(
            "bowler_boundary_conceded", "sum"
        )
    )
    .reset_index()
)

bowler_phase["economy"] = np.where(
    bowler_phase["legal_balls"] > 0,
    bowler_phase["runs_conceded"] * 6 /
    bowler_phase["legal_balls"],
    np.nan
)

bowler_phase.to_csv(
    REPORT_DIR / "bowler_pressure_by_phase.csv",
    index=False
)

# --------------------------------------------------
# 7. SUMMARY AND VALIDATION
# --------------------------------------------------

print("\n" + "=" * 85)
print("PLAYER PERFORMANCE DATASET SUMMARY")
print("=" * 85)

print("Total delivery records:", len(df))
print("Pressure deliveries:", int(
    df["analysis_pressure_delivery"].sum()
))

print("\nUnique batters:", df["striker_id"].nunique())
print("Unique bowlers:", df["bowler_id"].nunique())

print("\nBatter pressure records:", len(batter_pressure))
print("Bowler pressure records:", len(bowler_pressure))

print("\nTOP 10 BATTERS BY PRESSURE RUNS")
print("=" * 85)

print(
    batter_pressure.sort_values(
        ["runs", "balls_faced"],
        ascending=False
    )[
        [
            "striker_name",
            "matches",
            "pressure_deliveries",
            "runs",
            "balls_faced",
            "strike_rate",
            "dismissals"
        ]
    ].head(10).to_string(index=False)
)

print("\nTOP 10 BOWLERS BY PRESSURE WICKETS")
print("=" * 85)

print(
    bowler_pressure.sort_values(
        ["wickets", "legal_balls"],
        ascending=[False, False]
    )[
        [
            "bowler_name",
            "matches",
            "pressure_deliveries",
            "legal_balls",
            "runs_conceded",
            "wickets",
            "economy",
            "dot_balls"
        ]
    ].head(10).to_string(index=False)
)

print("\n" + "=" * 85)
print("SCRIPT 22 COMPLETED")
print("Reports saved in:", REPORT_DIR)
print("=" * 85)
