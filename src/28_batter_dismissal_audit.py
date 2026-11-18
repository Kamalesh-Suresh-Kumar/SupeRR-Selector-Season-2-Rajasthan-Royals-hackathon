
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT = BASE_DIR / "reports" / "unified_pressure_deliveries.csv.gz"
REPORTS = BASE_DIR / "reports"

print("Loading IPL data...")
df = pd.read_csv(INPUT, low_memory=False)

# ============================================================
# 1. RECREATE PRESSURE FLAG
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
# 2. BUILD PLAYER ID-TO-NAME MAPPING
# ============================================================

player_names = {}

for id_col, name_col in [
    ("striker_id", "striker_name"),
    ("non_striker_id", "non_striker_name")
]:
    temp = df[[id_col, name_col]].dropna().drop_duplicates()

    for _, row in temp.iterrows():
        player_id = str(row[id_col])
        player_name = str(row[name_col])

        if player_id not in player_names:
            player_names[player_id] = player_name

# ============================================================
# 3. EXTRACT ACTUAL DISMISSAL EVENTS
# ============================================================

print("Extracting dismissal events...")

df["is_wicket"] = (
    df["is_wicket"].fillna(False).astype(bool)
)

dismissals = df[
    df["is_wicket"] &
    df["dismissed_player_id"].notna()
].copy()

dismissals["dismissed_player_id"] = (
    dismissals["dismissed_player_id"].astype(str)
)

dismissals["dismissed_player_name"] = (
    dismissals["dismissed_player_id"].map(player_names)
)

dismissals["dismissal_type"] = (
    dismissals["dismissal_type"].fillna("Unknown").astype(str)
)

# ============================================================
# 4. AUDIT DISMISSAL DATA QUALITY
# ============================================================

print("\n" + "=" * 90)
print("DISMISSAL DATA QUALITY AUDIT")
print("=" * 90)

print("Total delivery rows:", len(df))
print("Rows marked as wickets:", int(df["is_wicket"].sum()))
print("Dismissal events with player ID:", len(dismissals))

print(
    "Dismissal events with unknown player name:",
    int(dismissals["dismissed_player_name"].isna().sum())
)

print(
    "Unique dismissed players:",
    dismissals["dismissed_player_id"].nunique()
)

print("\nDISMISSAL TYPES")
print(
    dismissals["dismissal_type"]
    .value_counts(dropna=False)
    .to_string()
)

# ============================================================
# 5. PRESSURE VS NORMAL DISMISSALS
# ============================================================

dismissal_summary = (
    dismissals.groupby(
        [
            "dismissed_player_id",
            "dismissed_player_name",
            "is_pressure"
        ],
        dropna=False
    )
    .agg(
        dismissals=("match_id", "size"),
        dismissal_matches=("match_id", "nunique")
    )
    .reset_index()
)

dismissal_pivot = dismissal_summary.pivot_table(
    index=["dismissed_player_id", "dismissed_player_name"],
    columns="is_pressure",
    values="dismissals",
    aggfunc="sum",
    fill_value=0
).reset_index()

dismissal_pivot.columns.name = None

dismissal_pivot = dismissal_pivot.rename(
    columns={
        False: "normal_dismissals",
        True: "pressure_dismissals"
    }
)

if "normal_dismissals" not in dismissal_pivot.columns:
    dismissal_pivot["normal_dismissals"] = 0

if "pressure_dismissals" not in dismissal_pivot.columns:
    dismissal_pivot["pressure_dismissals"] = 0

# ============================================================
# 6. ADD PRESSURE AND NORMAL BATTING OPPORTUNITIES
# ============================================================

bat = df.dropna(
    subset=["striker_id", "striker_name"]
).copy()

bat["striker_id"] = bat["striker_id"].astype(str)

bat["balls_faced"] = (
    bat["extras_type_clean"].fillna("").str.lower() != "wide"
).astype(int)

opportunities = (
    bat.groupby(["striker_id", "striker_name", "is_pressure"])
    .agg(
        batting_runs=("runs", "sum"),
        batting_balls=("balls_faced", "sum"),
        batting_matches=("match_id", "nunique")
    )
    .reset_index()
)

opportunity_pivot = opportunities.pivot_table(
    index=["striker_id", "striker_name"],
    columns="is_pressure",
    values=["batting_runs", "batting_balls", "batting_matches"],
    aggfunc="sum",
    fill_value=0
)

opportunity_pivot.columns = [
    f"{metric}_{'pressure' if pressure else 'normal'}"
    for metric, pressure in opportunity_pivot.columns
]

opportunity_pivot = opportunity_pivot.reset_index()

# ============================================================
# 7. MERGE DISMISSALS WITH BATTING OPPORTUNITIES
# ============================================================

result = opportunity_pivot.merge(
    dismissal_pivot,
    left_on="striker_id",
    right_on="dismissed_player_id",
    how="left"
)

for col in ["normal_dismissals", "pressure_dismissals"]:
    result[col] = result[col].fillna(0).astype(int)

# Ensure missing opportunity columns are handled.
for col in [
    "batting_runs_pressure",
    "batting_balls_pressure",
    "batting_matches_pressure",
    "batting_runs_normal",
    "batting_balls_normal",
    "batting_matches_normal"
]:
    if col not in result.columns:
        result[col] = 0

# ============================================================
# 8. CALCULATE DISMISSAL RATES
# ============================================================

result["pressure_dismissal_rate"] = (
    result["pressure_dismissals"]
    / result["batting_balls_pressure"].replace(0, pd.NA)
    * 100
)

result["normal_dismissal_rate"] = (
    result["normal_dismissals"]
    / result["batting_balls_normal"].replace(0, pd.NA)
    * 100
)

result["dismissal_rate_difference"] = (
    result["pressure_dismissal_rate"]
    - result["normal_dismissal_rate"]
)

result["pressure_strike_rate"] = (
    result["batting_runs_pressure"]
    * 100
    / result["batting_balls_pressure"].replace(0, pd.NA)
)

result["normal_strike_rate"] = (
    result["batting_runs_normal"]
    * 100
    / result["batting_balls_normal"].replace(0, pd.NA)
)

# ============================================================
# 9. SAVE RESULTS
# ============================================================

output = REPORTS / "batter_dismissal_pressure_audit.csv"

result.to_csv(output, index=False)

dismissals.to_csv(
    REPORTS / "batter_dismissal_events.csv",
    index=False
)

# ============================================================
# 10. DISPLAY
# ============================================================

print("\n" + "=" * 90)
print("TOP BATTERS BY PRESSURE DISMISSALS")
print("=" * 90)

print(
    result.sort_values(
        ["pressure_dismissals", "batting_runs_pressure"],
        ascending=[False, False]
    )[
        [
            "striker_name",
            "batting_runs_pressure",
            "batting_balls_pressure",
            "pressure_dismissals",
            "pressure_dismissal_rate",
            "normal_dismissal_rate",
            "dismissal_rate_difference"
        ]
    ].head(20).to_string(index=False)
)

print("\nOUTPUT FILES")
print(output)
print(REPORTS / "batter_dismissal_events.csv")

print("\nSCRIPT 28 COMPLETED")
