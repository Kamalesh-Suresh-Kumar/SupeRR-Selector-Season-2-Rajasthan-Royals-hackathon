
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# STEP 62: T20I PLAYER PRESSURE PERFORMANCE
# ============================================================

ROOT = Path(".")
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

PRESSURE_FILE = REPORTS / "t20i_pressure_context_scaled_deliveries.csv.gz"
PAR_FILE = REPORTS / "t20i_first_innings_par_deliveries.csv.gz"

print("\n" + "=" * 78)
print("STEP 62: T20I PLAYER PRESSURE PERFORMANCE")
print("=" * 78)


# ============================================================
# 1. LOAD DATA
# ============================================================

df = pd.read_csv(PRESSURE_FILE)
par = pd.read_csv(PAR_FILE)

print("Pressure dataset rows:", len(df))
print("First-innings benchmark rows:", len(par))

required_df = [
    "match_id", "innings", "innings_ball_num",
    "striker_id", "striker_name",
    "bowler_id", "bowler_name",
    "batter_runs", "team_runs",
    "extras_clean", "is_legal_ball",
    "is_counted_delivery", "is_wicket_clean",
    "dismissal_type", "dismissed_player_id",
    "legal_balls_before", "scheduled_legal_balls",
    "wickets_in_hand_before",
    "is_chase_pressure_scaled"
]

missing = [c for c in required_df if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns in pressure dataset: {missing}")

required_par = [
    "match_id", "innings", "striker_id", "bowler_id",
    "is_first_innings_pressure",
    "runs_below_par", "wickets_in_hand_before",
    "legal_balls_before", "scheduled_legal_balls"
]

missing = [c for c in required_par if c not in par.columns]

if missing:
    raise ValueError(f"Missing columns in first-innings benchmark: {missing}")



# ============================================================
# 2. PREPARE AND VALIDATE PRESSURE LABELS
# ============================================================

# Create a delivery sequence for every innings.
# This allows first-innings benchmark labels to be joined
# without confusing illegal deliveries that share ball counts.

df = df.sort_values(
    ["match_id", "innings", "innings_ball_num"]
).reset_index(drop=True)

df["_delivery_seq"] = (
    df.groupby(["match_id", "innings"], sort=False).cumcount()
)

first = df[df["innings"] == 1].copy()

par = par.copy().reset_index(drop=True)

par["_delivery_seq"] = (
    par.groupby(["match_id", "innings"], sort=False).cumcount()
)

merge_keys = ["match_id", "innings", "_delivery_seq"]

# First-innings benchmark and delivery row counts must match.

if len(first) != len(par):
    raise ValueError(
        "First-innings row count mismatch: "
        f"delivery data={len(first)}, benchmark={len(par)}"
    )

# Verify delivery alignment using player IDs and legal-ball state.

check = first[
    merge_keys + [
        "striker_id",
        "bowler_id",
        "legal_balls_before"
    ]
].merge(
    par[
        merge_keys + [
            "striker_id",
            "bowler_id",
            "legal_balls_before"
        ]
    ],
    on=merge_keys,
    how="outer",
    suffixes=("_full", "_par"),
    validate="one_to_one",
    indicator=True
)

if not (check["_merge"] == "both").all():
    raise ValueError(
        "First-innings delivery sequence does not match."
    )

for col in [
    "striker_id",
    "bowler_id",
    "legal_balls_before"
]:
    left = check[f"{col}_full"].fillna(-999999)
    right = check[f"{col}_par"].fillna(-999999)

    if not left.equals(right):
        raise ValueError(
            f"First-innings alignment failed for {col}."
        )

print("First-innings delivery alignment: PASSED")

# Only bring the pressure labels from the benchmark file.
# runs_below_par is not needed for the performance calculations.

par_labels = par[
    merge_keys + [
        "is_first_innings_pressure",
        "first_innings_pressure_severity"
    ]
].copy()

# Join labels to the complete delivery dataset.
# Second innings will naturally have missing first-innings labels.

df = df.merge(
    par_labels,
    on=merge_keys,
    how="left",
    validate="one_to_one"
)

# Assign the correct pressure definition to each innings.

df["is_pressure"] = False

first_mask = df["innings"] == 1
second_mask = df["innings"] == 2

df.loc[first_mask, "is_pressure"] = (
    df.loc[first_mask, "is_first_innings_pressure"]
    .fillna(False)
    .astype(bool)
)

df.loc[second_mask, "is_pressure"] = (
    df.loc[second_mask, "is_chase_pressure_scaled"]
    .fillna(False)
    .astype(bool)
)

df["is_pressure"] = df["is_pressure"].astype(bool)

print("Combined pressure labels assigned.")
print(
    "First-innings pressure deliveries:",
    int(df.loc[first_mask, "is_pressure"].sum())
)
print(
    "Second-innings pressure deliveries:",
    int(df.loc[second_mask, "is_pressure"].sum())
)


# ============================================================
# 3. CREATE PERFORMANCE FIELDS
# ============================================================

df["batter_runs"] = pd.to_numeric(
    df["batter_runs"], errors="coerce"
).fillna(0)

df["team_runs"] = pd.to_numeric(
    df["team_runs"], errors="coerce"
).fillna(0)

df["is_legal_ball"] = (
    df["is_legal_ball"].fillna(False).astype(bool)
)

df["is_counted_delivery"] = (
    df["is_counted_delivery"].fillna(False).astype(bool)
)

df["is_wicket_clean"] = (
    df["is_wicket_clean"].fillna(False).astype(bool)
)

df["extras_clean"] = (
    df["extras_clean"].fillna("none").astype(str).str.lower().str.strip()
)

df["dismissal_type_clean"] = (
    df["dismissal_type"]
    .fillna("")
    .astype(str)
    .str.lower()
    .str.replace("_", " ", regex=False)
    .str.strip()
)

# A batter faces a ball except on a wide or administrative penalty event.
df["is_batter_ball"] = (
    df["is_counted_delivery"]
    & (df["extras_clean"] != "wide")
    & (df["extras_clean"] != "penalty")
    & df["striker_id"].notna()
)

# Batter dismissal attribution.
df["is_batter_dismissal"] = (
    df["is_wicket_clean"]
    & df["dismissed_player_id"].notna()
    & df["striker_id"].notna()
    & (
        pd.to_numeric(df["dismissed_player_id"], errors="coerce")
        == pd.to_numeric(df["striker_id"], errors="coerce")
    )
)

# Bowler-credit dismissal types.
bowler_credit_types = [
    "caught",
    "bowled",
    "lbw",
    "stump",
    "stumped",
    "hitwicket",
    "hit wicket"
]

df["is_bowler_wicket"] = (
    df["is_wicket_clean"]
    & df["dismissal_type_clean"].isin(bowler_credit_types)
    & df["bowler_id"].notna()
)

# Byes, leg-byes and penalties are not charged to the bowler.
# Other extras remain charged under this working assumption.
not_bowler_extras = df["extras_clean"].isin(
    ["byes", "bye", "legbyes", "legbye", "penalty"]
)

extras_amount = (df["team_runs"] - df["batter_runs"]).clip(lower=0)

df["bowler_runs"] = (
    df["team_runs"] - np.where(not_bowler_extras, extras_amount, 0)
)

df["bowler_runs"] = df["bowler_runs"].clip(lower=0)

# Bowler legal balls.
df["bowler_legal_ball"] = (
    df["is_legal_ball"]
    & df["is_counted_delivery"]
    & df["bowler_id"].notna()
)

# Identify unusual extras for transparent auditing.
df["needs_extras_review"] = (
    df["extras_clean"].isin(["other", "none"])
    & (df["team_runs"] != df["batter_runs"])
)


# ============================================================
# 4. CREATE PRESSURE / NORMAL GROUPS
# ============================================================

df["performance_group"] = np.where(
    df["is_pressure"],
    "Pressure",
    "Normal"
)

# Exclude super overs and innings outside the main match.
df = df[df["innings"].isin([1, 2])].copy()

print("\nPerformance dataset rows:", len(df))
print("Pressure rows:", int(df["is_pressure"].sum()))
print("Normal rows:", int((~df["is_pressure"]).sum()))


# ============================================================
# 5. BATTER PERFORMANCE
# ============================================================

batter_data = df[
    df["striker_id"].notna()
    & df["is_batter_ball"]
].copy()

batter_group = (
    batter_data.groupby(
        ["striker_id", "striker_name", "performance_group"],
        dropna=False
    )
    .agg(
        runs=("batter_runs", "sum"),
        balls=("is_batter_ball", "sum"),
        dismissals=("is_batter_dismissal", "sum"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

batter_group["strike_rate"] = np.where(
    batter_group["balls"] > 0,
    batter_group["runs"] * 100 / batter_group["balls"],
    np.nan
)

batter_group["dismissals_per_100_balls"] = np.where(
    batter_group["balls"] > 0,
    batter_group["dismissals"] * 100 / batter_group["balls"],
    np.nan
)

batter_group.to_csv(
    REPORTS / "t20i_batter_pressure_group_metrics.csv",
    index=False
)

batter_wide = batter_group.pivot(
    index=["striker_id", "striker_name"],
    columns="performance_group",
    values=["runs", "balls", "dismissals", "matches",
            "strike_rate", "dismissals_per_100_balls"]
)

batter_wide.columns = [
    f"{metric}_{group.lower()}"
    for metric, group in batter_wide.columns
]

batter_wide = batter_wide.reset_index()

for col in [
    "runs_pressure", "balls_pressure", "dismissals_pressure",
    "matches_pressure", "strike_rate_pressure",
    "dismissals_per_100_balls_pressure",
    "runs_normal", "balls_normal", "dismissals_normal",
    "matches_normal", "strike_rate_normal",
    "dismissals_per_100_balls_normal"
]:
    if col not in batter_wide.columns:
        batter_wide[col] = np.nan

batter_wide["strike_rate_difference"] = (
    batter_wide["strike_rate_pressure"]
    - batter_wide["strike_rate_normal"]
)

# Positive dismissal-rate improvement means fewer dismissals under pressure.
batter_wide["dismissal_rate_improvement"] = (
    batter_wide["dismissals_per_100_balls_normal"]
    - batter_wide["dismissals_per_100_balls_pressure"]
)

batter_wide = batter_wide.sort_values(
    ["strike_rate_difference", "matches_pressure"],
    ascending=[False, False]
)

batter_wide.to_csv(
    REPORTS / "t20i_batter_pressure_vs_normal.csv",
    index=False
)


# ============================================================
# 6. BOWLER PERFORMANCE
# ============================================================

bowler_data = df[
    df["bowler_id"].notna()
    & df["is_counted_delivery"]
].copy()

bowler_group = (
    bowler_data.groupby(
        ["bowler_id", "bowler_name", "performance_group"],
        dropna=False
    )
    .agg(
        runs_conceded=("bowler_runs", "sum"),
        legal_balls=("bowler_legal_ball", "sum"),
        wickets=("is_bowler_wicket", "sum"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

bowler_group["overs"] = bowler_group["legal_balls"] / 6

bowler_group["economy"] = np.where(
    bowler_group["legal_balls"] > 0,
    bowler_group["runs_conceded"] * 6 / bowler_group["legal_balls"],
    np.nan
)

bowler_group["wickets_per_100_legal_balls"] = np.where(
    bowler_group["legal_balls"] > 0,
    bowler_group["wickets"] * 100 / bowler_group["legal_balls"],
    np.nan
)

bowler_group.to_csv(
    REPORTS / "t20i_bowler_pressure_group_metrics.csv",
    index=False
)

bowler_wide = bowler_group.pivot(
    index=["bowler_id", "bowler_name"],
    columns="performance_group",
    values=[
        "runs_conceded", "legal_balls", "wickets",
        "matches", "economy", "wickets_per_100_legal_balls"
    ]
)

bowler_wide.columns = [
    f"{metric}_{group.lower()}"
    for metric, group in bowler_wide.columns
]

bowler_wide = bowler_wide.reset_index()

for col in [
    "runs_conceded_pressure", "legal_balls_pressure",
    "wickets_pressure", "matches_pressure", "economy_pressure",
    "wickets_per_100_legal_balls_pressure",
    "runs_conceded_normal", "legal_balls_normal",
    "wickets_normal", "matches_normal", "economy_normal",
    "wickets_per_100_legal_balls_normal"
]:
    if col not in bowler_wide.columns:
        bowler_wide[col] = np.nan

# Negative economy difference means the bowler is more economical under pressure.
bowler_wide["economy_difference"] = (
    bowler_wide["economy_pressure"]
    - bowler_wide["economy_normal"]
)

bowler_wide["wicket_rate_improvement"] = (
    bowler_wide["wickets_per_100_legal_balls_pressure"]
    - bowler_wide["wickets_per_100_legal_balls_normal"]
)

bowler_wide = bowler_wide.sort_values(
    ["economy_difference", "matches_pressure"],
    ascending=[True, False]
)

bowler_wide.to_csv(
    REPORTS / "t20i_bowler_pressure_vs_normal.csv",
    index=False
)


# ============================================================
# 7. PLAYER MATCH CONSISTENCY
# ============================================================

# Batter match-level pressure strike rate.
batter_match = (
    batter_data.groupby(
        ["striker_id", "striker_name", "match_id", "is_pressure"],
        dropna=False
    )
    .agg(
        runs=("batter_runs", "sum"),
        balls=("is_batter_ball", "sum")
    )
    .reset_index()
)

batter_match = batter_match[batter_match["balls"] > 0].copy()

batter_match["strike_rate"] = (
    batter_match["runs"] * 100 / batter_match["balls"]
)

normal_baseline = (
    batter_match[~batter_match["is_pressure"]]
    .groupby("striker_id")["strike_rate"]
    .median()
    .rename("normal_match_median_sr")
)

pressure_matches = batter_match[
    batter_match["is_pressure"]
].copy()

pressure_matches = pressure_matches.merge(
    normal_baseline,
    on="striker_id",
    how="left"
)

pressure_matches["performed_above_normal"] = (
    pressure_matches["strike_rate"]
    > pressure_matches["normal_match_median_sr"]
)

batter_consistency = (
    pressure_matches.groupby(
        ["striker_id", "striker_name"]
    )
    .agg(
        pressure_matches=("match_id", "nunique"),
        matches_above_normal=("performed_above_normal", "sum"),
        average_pressure_match_sr=("strike_rate", "mean")
    )
    .reset_index()
)

batter_consistency["consistency_pct"] = (
    batter_consistency["matches_above_normal"]
    * 100
    / batter_consistency["pressure_matches"]
)

batter_consistency.to_csv(
    REPORTS / "t20i_batter_pressure_consistency.csv",
    index=False
)


# Bowler match-level pressure economy.
bowler_match_data = bowler_data.copy()

bowler_match = (
    bowler_match_data.groupby(
        ["bowler_id", "bowler_name", "match_id", "is_pressure"],
        dropna=False
    )
    .agg(
        runs_conceded=("bowler_runs", "sum"),
        legal_balls=("bowler_legal_ball", "sum"),
        wickets=("is_bowler_wicket", "sum")
    )
    .reset_index()
)

bowler_match = bowler_match[bowler_match["legal_balls"] > 0].copy()

bowler_match["economy"] = (
    bowler_match["runs_conceded"] * 6
    / bowler_match["legal_balls"]
)

normal_bowler_baseline = (
    bowler_match[~bowler_match["is_pressure"]]
    .groupby("bowler_id")["economy"]
    .median()
    .rename("normal_match_median_economy")
)

pressure_bowler_matches = bowler_match[
    bowler_match["is_pressure"]
].copy()

pressure_bowler_matches = pressure_bowler_matches.merge(
    normal_bowler_baseline,
    on="bowler_id",
    how="left"
)

pressure_bowler_matches["performed_better_than_normal"] = (
    pressure_bowler_matches["economy"]
    < pressure_bowler_matches["normal_match_median_economy"]
)

bowler_consistency = (
    pressure_bowler_matches.groupby(
        ["bowler_id", "bowler_name"]
    )
    .agg(
        pressure_matches=("match_id", "nunique"),
        matches_better_than_normal=("performed_better_than_normal", "sum"),
        average_pressure_match_economy=("economy", "mean")
    )
    .reset_index()
)

bowler_consistency["consistency_pct"] = (
    bowler_consistency["matches_better_than_normal"]
    * 100
    / bowler_consistency["pressure_matches"]
)

bowler_consistency.to_csv(
    REPORTS / "t20i_bowler_pressure_consistency.csv",
    index=False
)


# ============================================================
# 8. DATA QUALITY AND RECONCILIATION
# ============================================================

quality = {
    "delivery_rows": len(df),
    "first_innings_rows": int((df["innings"] == 1).sum()),
    "second_innings_rows": int((df["innings"] == 2).sum()),
    "pressure_rows": int(df["is_pressure"].sum()),
    "normal_rows": int((~df["is_pressure"]).sum()),
    "total_batter_runs": int(df["batter_runs"].sum()),
    "total_team_runs": int(df["team_runs"].sum()),
    "total_bowler_runs": int(df["bowler_runs"].sum()),
    "total_legal_balls": int(df["is_legal_ball"].sum()),
    "total_batter_dismissals": int(df["is_batter_dismissal"].sum()),
    "total_bowler_credit_wickets": int(df["is_bowler_wicket"].sum()),
    "extras_review_rows": int(df["needs_extras_review"].sum()),
    "unique_batters": int(df["striker_id"].nunique()),
    "unique_bowlers": int(df["bowler_id"].nunique())
}

pd.DataFrame(
    list(quality.items()),
    columns=["metric", "value"]
).to_csv(
    REPORTS / "t20i_player_performance_quality_audit.csv",
    index=False
)

print("\n" + "=" * 78)
print("DATA QUALITY SUMMARY")
print("=" * 78)

for key, value in quality.items():
    print(f"{key}: {value}")


# ============================================================
# 9. DISPLAY TOP PLAYER COMPARISONS
# ============================================================

print("\n" + "=" * 78)
print("TOP 15 BATTERS BY PRESSURE STRIKE-RATE IMPROVEMENT")
print("=" * 78)

print(
    batter_wide[
        [
            "striker_name",
            "runs_pressure",
            "balls_pressure",
            "matches_pressure",
            "strike_rate_pressure",
            "strike_rate_normal",
            "strike_rate_difference"
        ]
    ].head(15).round(2).to_string(index=False)
)

print("\n" + "=" * 78)
print("TOP 15 BOWLERS BY PRESSURE ECONOMY IMPROVEMENT")
print("=" * 78)

print(
    bowler_wide[
        [
            "bowler_name",
            "wickets_pressure",
            "legal_balls_pressure",
            "matches_pressure",
            "economy_pressure",
            "economy_normal",
            "economy_difference"
        ]
    ].head(15).round(2).to_string(index=False)
)


# ============================================================
# 10. COMPLETION
# ============================================================

print("\n" + "=" * 78)
print("STEP 62 COMPLETED")
print("=" * 78)

print("\nGenerated reports:")
for name in [
    "t20i_batter_pressure_group_metrics.csv",
    "t20i_batter_pressure_vs_normal.csv",
    "t20i_batter_pressure_consistency.csv",
    "t20i_bowler_pressure_group_metrics.csv",
    "t20i_bowler_pressure_vs_normal.csv",
    "t20i_bowler_pressure_consistency.csv",
    "t20i_player_performance_quality_audit.csv"
]:
    print(" -", REPORTS / name)
