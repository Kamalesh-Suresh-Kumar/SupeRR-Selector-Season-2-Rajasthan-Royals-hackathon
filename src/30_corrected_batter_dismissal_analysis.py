
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"
INPUT = REPORTS / "unified_pressure_deliveries.csv.gz"

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
# 2. NORMALIZE PLAYER IDS
# ============================================================

for col in ["striker_id", "non_striker_id", "dismissed_player_id"]:
    df[col + "_clean"] = pd.to_numeric(
        df[col], errors="coerce"
    ).astype("Int64")

# ============================================================
# 3. BUILD PLAYER NAME MAPPING
# ============================================================

player_mapping = {}

for _, row in df.iterrows():

    sid = row["striker_id_clean"]
    nsid = row["non_striker_id_clean"]

    if pd.notna(sid) and pd.notna(row["striker_name"]):
        player_mapping[int(sid)] = row["striker_name"]

    if pd.notna(nsid) and pd.notna(row["non_striker_name"]):
        player_mapping[int(nsid)] = row["non_striker_name"]

# ============================================================
# 4. EXTRACT DISMISSAL EVENTS
# ============================================================

df["is_wicket"] = pd.to_numeric(
    df["is_wicket"], errors="coerce"
).fillna(0).astype(int)

dismissals = df[df["is_wicket"] == 1].copy()

dismissals["dismissed_player_name"] = (
    dismissals["dismissed_player_id_clean"].map(player_mapping)
)

identified = dismissals[
    dismissals["dismissed_player_id_clean"].notna()
].copy()

identified["dismissed_player_id_clean"] = (
    identified["dismissed_player_id_clean"].astype(int)
)

# ============================================================
# 5. DISMISSALS BY PLAYER AND CONTEXT
# ============================================================

dismissal_counts = (
    identified.groupby(
        ["dismissed_player_id_clean", "dismissed_player_name", "is_pressure"],
        dropna=False
    )
    .agg(
        dismissals=("match_id", "size"),
        dismissal_matches=("match_id", "nunique")
    )
    .reset_index()
)

dismissal_pivot = dismissal_counts.pivot_table(
    index="dismissed_player_id_clean",
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

for col in ["normal_dismissals", "pressure_dismissals"]:
    if col not in dismissal_pivot.columns:
        dismissal_pivot[col] = 0

# ============================================================
# 6. BATTING OPPORTUNITIES
# ============================================================

bat = df.dropna(
    subset=["striker_id_clean", "striker_name"]
).copy()

bat["balls_faced"] = (
    bat["extras_type_clean"].fillna("").str.lower() != "wide"
).astype(int)

batting = (
    bat.groupby(
        ["striker_id_clean", "striker_name", "is_pressure"]
    )
    .agg(
        runs=("runs", "sum"),
        balls_faced=("balls_faced", "sum"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

batting_pivot = batting.pivot_table(
    index=["striker_id_clean", "striker_name"],
    columns="is_pressure",
    values=["runs", "balls_faced", "matches"],
    aggfunc="sum",
    fill_value=0
)

batting_pivot.columns = [
    f"{metric}_{'pressure' if pressure else 'normal'}"
    for metric, pressure in batting_pivot.columns
]

batting_pivot = batting_pivot.reset_index()

# ============================================================
# 7. MERGE USING THE CORRECT COMMON ID
# ============================================================

result = batting_pivot.merge(
    dismissal_pivot,
    left_on="striker_id_clean",
    right_on="dismissed_player_id_clean",
    how="left",
    validate="one_to_one"
)

result = result.drop(columns=["dismissed_player_id_clean"])

result["player_name"] = result["striker_name"]

for col in ["normal_dismissals", "pressure_dismissals"]:
    result[col] = result[col].fillna(0).astype(int)

# ============================================================
# 8. DISMISSAL RATES AND STRIKE RATES
# ============================================================

result["pressure_dismissals_per_100_balls"] = (
    result["pressure_dismissals"] * 100
    / result["balls_faced_pressure"].replace(0, np.nan)
)

result["normal_dismissals_per_100_balls"] = (
    result["normal_dismissals"] * 100
    / result["balls_faced_normal"].replace(0, np.nan)
)

result["dismissal_rate_difference"] = (
    result["pressure_dismissals_per_100_balls"]
    - result["normal_dismissals_per_100_balls"]
)

result["pressure_strike_rate"] = (
    result["runs_pressure"] * 100
    / result["balls_faced_pressure"].replace(0, np.nan)
)

result["normal_strike_rate"] = (
    result["runs_normal"] * 100
    / result["balls_faced_normal"].replace(0, np.nan)
)

result["strike_rate_difference"] = (
    result["pressure_strike_rate"]
    - result["normal_strike_rate"]
)

# ============================================================
# 9. SAVE OUTPUTS
# ============================================================

result = result.sort_values(
    ["pressure_dismissals", "runs_pressure"],
    ascending=[False, False]
)

result.to_csv(
    REPORTS / "batter_corrected_dismissal_analysis.csv",
    index=False
)

identified.to_csv(
    REPORTS / "batter_identified_dismissal_events.csv",
    index=False
)

dismissals.to_csv(
    REPORTS / "batter_all_dismissal_events_audited.csv",
    index=False
)

# ============================================================
# 10. VALIDATION
# ============================================================

print("\n" + "=" * 90)
print("CORRECTED DISMISSAL ANALYSIS")
print("=" * 90)

print("Total wicket records:", len(dismissals))
print("Identified dismissal events:", len(identified))
print(
    "Unidentified dismissal events:",
    int(dismissals["dismissed_player_id_clean"].isna().sum())
)

print(
    "Reconciled identified dismissals:",
    int(result["normal_dismissals"].sum()
        + result["pressure_dismissals"].sum())
)

print(
    "Pressure dismissals:",
    int(result["pressure_dismissals"].sum())
)

print(
    "Normal dismissals:",
    int(result["normal_dismissals"].sum())
)

print("\nTOP 20 BATTERS BY PRESSURE DISMISSALS")

print(
    result[
        [
            "player_name",
            "runs_pressure",
            "balls_faced_pressure",
            "pressure_dismissals",
            "pressure_dismissals_per_100_balls",
            "normal_dismissals_per_100_balls",
            "dismissal_rate_difference",
            "pressure_strike_rate",
            "normal_strike_rate"
        ]
    ].head(20).to_string(index=False)
)

print("\nOUTPUT FILES")
print(REPORTS / "batter_corrected_dismissal_analysis.csv")
print(REPORTS / "batter_identified_dismissal_events.csv")
print(REPORTS / "batter_all_dismissal_events_audited.csv")

print("\nSCRIPT 30 COMPLETED")
