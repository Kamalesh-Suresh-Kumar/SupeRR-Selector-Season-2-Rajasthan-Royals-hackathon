
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

print("=" * 70)
print("BOWLER DISMISSAL ATTRIBUTION AUDIT")
print("=" * 70)

df = pd.read_csv(
    REPORTS / "unified_pressure_deliveries.csv.gz",
    low_memory=False
)

# --------------------------------------------------
# NORMALIZE DISMISSAL TYPES
# --------------------------------------------------

df["dismissal_clean"] = (
    df["dismissal_type"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)

# Normalize spelling variations.
df["dismissal_clean"] = df["dismissal_clean"].replace({
    "obstracting the field": "obstructing the field"
})

bowler_credit_types = [
    "caught",
    "bowled",
    "lbw",
    "stump",
    "hit wicket"
]

non_bowler_credit_types = [
    "runout",
    "retire out",
    "obstructing the field"
]

wickets = df[df["is_wicket"] == 1].copy()

wickets["bowler_credit"] = (
    wickets["dismissal_clean"].isin(bowler_credit_types)
)

wickets["analysis_pressure"] = False

first = wickets["innings"] == 1
second = wickets["innings"] == 2

wickets.loc[first, "analysis_pressure"] = (
    wickets.loc[first, "is_pressure_delivery"]
    .fillna(False)
    .astype(bool)
)

wickets.loc[second, "analysis_pressure"] = (
    (wickets.loc[second, "required_run_rate_before"] >= 10)
    & (
        (wickets.loc[second, "wickets_in_hand_before"] <= 6)
        | (wickets.loc[second, "balls_remaining_before"] <= 30)
    )
)

# --------------------------------------------------
# OVERALL RECONCILIATION
# --------------------------------------------------

print("\n1. TOTAL WICKET RECONCILIATION")

print("All wicket deliveries:", len(wickets))
print("Bowler-credit wickets:", int(wickets["bowler_credit"].sum()))
print(
    "Non-bowler-credit wickets:",
    int((~wickets["bowler_credit"]).sum())
)

print("\n2. DISMISSAL TYPE BREAKDOWN")

print(
    wickets.groupby(
        ["dismissal_clean", "bowler_credit"],
        dropna=False
    ).size().to_string()
)

# --------------------------------------------------
# PRESSURE / NORMAL SPLIT
# --------------------------------------------------

print("\n3. PRESSURE AND NORMAL WICKET COUNTS")

print(
    pd.crosstab(
        wickets["analysis_pressure"],
        wickets["bowler_credit"],
        margins=True
    )
)

# --------------------------------------------------
# PLAYER-LEVEL AGGREGATION
# --------------------------------------------------

credited = wickets[wickets["bowler_credit"]].copy()

player_metrics = (
    credited.groupby(
        ["bowler_id", "bowler_name", "analysis_pressure"],
        dropna=False
    )
    .size()
    .reset_index(name="credited_wickets")
)

player_wide = player_metrics.pivot_table(
    index=["bowler_id", "bowler_name"],
    columns="analysis_pressure",
    values="credited_wickets",
    fill_value=0
).reset_index()

player_wide = player_wide.rename(columns={
    False: "normal_credited_wickets",
    True: "pressure_credited_wickets"
})

if "normal_credited_wickets" not in player_wide.columns:
    player_wide["normal_credited_wickets"] = 0

if "pressure_credited_wickets" not in player_wide.columns:
    player_wide["pressure_credited_wickets"] = 0

# --------------------------------------------------
# COMPARE WITH EXISTING BOWLER REPORT
# --------------------------------------------------

existing = pd.read_csv(
    REPORTS / "bowler_pressure_vs_baseline.csv"
)

comparison = existing[
    [
        "bowler_id",
        "bowler_name",
        "wickets_pressure",
        "wickets_normal"
    ]
].merge(
    player_wide,
    on="bowler_id",
    how="left",
    suffixes=("_report", "_audit")
)

for col in [
    "normal_credited_wickets",
    "pressure_credited_wickets"
]:
    comparison[col] = comparison[col].fillna(0)

comparison["pressure_difference"] = (
    comparison["wickets_pressure"]
    - comparison["pressure_credited_wickets"]
)

comparison["normal_difference"] = (
    comparison["wickets_normal"]
    - comparison["normal_credited_wickets"]
)

print("\n4. BOWLER WICKET RECONCILIATION")

print(
    comparison.sort_values(
        "pressure_difference",
        key=lambda x: x.abs(),
        ascending=False
    ).head(20).to_string(index=False)
)

print("\nPressure wicket mismatches:",
      int((comparison["pressure_difference"] != 0).sum()))

print("Normal wicket mismatches:",
      int((comparison["normal_difference"] != 0).sum()))

comparison.to_csv(
    REPORTS / "bowler_wicket_attribution_audit.csv",
    index=False
)

print("\nSaved:")
print("reports/bowler_wicket_attribution_audit.csv")

print("\nAudit completed.")
