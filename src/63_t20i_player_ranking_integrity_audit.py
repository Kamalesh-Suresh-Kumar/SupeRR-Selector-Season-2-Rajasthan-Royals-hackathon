
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# STEP 63: T20I PLAYER RANKING INTEGRITY AUDIT
# ============================================================

REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)

PRESSURE_FILE = REPORTS / "t20i_pressure_context_scaled_deliveries.csv.gz"
PAR_FILE = REPORTS / "t20i_first_innings_par_deliveries.csv.gz"

print("\n" + "=" * 80)
print("STEP 63: T20I PLAYER RANKING INTEGRITY AUDIT")
print("=" * 80)


# ============================================================
# 1. LOAD DATA
# ============================================================

df = pd.read_csv(PRESSURE_FILE, low_memory=False)
par = pd.read_csv(PAR_FILE, low_memory=False)

print("Full delivery rows:", len(df))
print("First-innings benchmark rows:", len(par))


# ============================================================
# 2. VALIDATE REQUIRED COLUMNS
# ============================================================

required = [
    "match_id", "innings", "innings_ball_num",
    "striker_id", "striker_name",
    "non_striker_id", "non_striker_name",
    "bowler_id", "bowler_name",
    "batter_runs", "team_runs",
    "extras_clean", "is_legal_ball",
    "is_counted_delivery", "is_wicket_clean",
    "dismissal_type", "dismissed_player_id",
    "is_chase_pressure_scaled"
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing delivery columns: {missing}")

par_required = [
    "match_id", "innings",
    "striker_id", "bowler_id",
    "legal_balls_before",
    "is_first_innings_pressure"
]

missing = [c for c in par_required if c not in par.columns]

if missing:
    raise ValueError(f"Missing benchmark columns: {missing}")


# ============================================================
# 3. RECONSTRUCT AND VALIDATE PRESSURE LABELS
# ============================================================

# Follow the same delivery ordering used in Step 62.

df = df.sort_values(
    ["match_id", "innings", "innings_ball_num"]
).reset_index(drop=True)

df["_delivery_seq"] = (
    df.groupby(["match_id", "innings"], sort=False).cumcount()
)

par = par.copy().reset_index(drop=True)

par["_delivery_seq"] = (
    par.groupby(["match_id", "innings"], sort=False).cumcount()
)

keys = ["match_id", "innings", "_delivery_seq"]

first = df[df["innings"] == 1].copy()

if len(first) != len(par):
    raise ValueError(
        f"First-innings count mismatch: {len(first)} vs {len(par)}"
    )

alignment = first[
    keys + ["striker_id", "bowler_id", "legal_balls_before"]
].merge(
    par[
        keys + ["striker_id", "bowler_id", "legal_balls_before"]
    ],
    on=keys,
    how="outer",
    suffixes=("_full", "_par"),
    validate="one_to_one",
    indicator=True
)

if not (alignment["_merge"] == "both").all():
    raise ValueError("First-innings delivery alignment failed.")

for col in ["striker_id", "bowler_id", "legal_balls_before"]:
    left = alignment[f"{col}_full"].fillna(-999999)
    right = alignment[f"{col}_par"].fillna(-999999)

    if not left.equals(right):
        raise ValueError(f"Alignment mismatch: {col}")

print("First-innings delivery alignment: PASSED")

labels = par[
    keys + [
        "is_first_innings_pressure",
        "first_innings_pressure_severity"
    ]
].copy()

df = df.merge(
    labels,
    on=keys,
    how="left",
    validate="one_to_one"
)

df["is_pressure"] = False

mask1 = df["innings"] == 1
mask2 = df["innings"] == 2

df.loc[mask1, "is_pressure"] = (
    df.loc[mask1, "is_first_innings_pressure"]
    .fillna(False)
    .astype(bool)
)

df.loc[mask2, "is_pressure"] = (
    df.loc[mask2, "is_chase_pressure_scaled"]
    .fillna(False)
    .astype(bool)
)

df["is_pressure"] = df["is_pressure"].astype(bool)

print(
    "First-innings pressure deliveries:",
    int(df.loc[mask1, "is_pressure"].sum())
)

print(
    "Second-innings pressure deliveries:",
    int(df.loc[mask2, "is_pressure"].sum())
)


# ============================================================
# 4. NORMALIZE DATA TYPES AND DISMISSAL CATEGORIES
# ============================================================

for col in [
    "striker_id", "non_striker_id",
    "bowler_id", "dismissed_player_id"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

for col in ["batter_runs", "team_runs"]:
    df[col] = pd.to_numeric(
        df[col], errors="coerce"
    ).fillna(0)

for col in [
    "is_legal_ball",
    "is_counted_delivery",
    "is_wicket_clean"
]:
    df[col] = df[col].fillna(False).astype(bool)

df["extras_clean"] = (
    df["extras_clean"]
    .fillna("none")
    .astype(str)
    .str.lower()
    .str.strip()
)

df["dismissal_type_clean"] = (
    df["dismissal_type"]
    .fillna("unknown")
    .astype(str)
    .str.lower()
    .str.strip()
    .str.replace("_", " ", regex=False)
)


# ============================================================
# 5. TOTAL RUN RECONCILIATION
# ============================================================

df["extras_runs"] = (
    df["team_runs"] - df["batter_runs"]
).clip(lower=0)

not_bowler_extras = df["extras_clean"].isin(
    ["byes", "bye", "legbyes", "legbye", "penalty"]
)

df["bowler_runs"] = (
    df["team_runs"]
    - np.where(not_bowler_extras, df["extras_runs"], 0)
)

df["bowler_runs"] = df["bowler_runs"].clip(lower=0)

df["needs_extras_review"] = (
    df["extras_clean"].isin(["other", "none"])
    & (df["extras_runs"] > 0)
)

total_batter_runs = int(df["batter_runs"].sum())
total_team_runs = int(df["team_runs"].sum())
total_extras_runs = int(df["extras_runs"].sum())
total_bowler_runs = int(df["bowler_runs"].sum())

run_reconciliation = pd.DataFrame([
    ["Batter runs", total_batter_runs],
    ["Extras runs", total_extras_runs],
    ["Team runs", total_team_runs],
    ["Bowler runs conceded", total_bowler_runs],
    [
        "Batter runs + extras",
        total_batter_runs + total_extras_runs
    ],
    [
        "Bowler runs not charged",
        total_team_runs - total_bowler_runs
    ]
], columns=["metric", "value"])

run_reconciliation.to_csv(
    REPORTS / "t20i_run_reconciliation_audit.csv",
    index=False
)

print("\nRUN RECONCILIATION")
print(run_reconciliation.to_string(index=False))


# ============================================================
# 6. DISMISSAL CATEGORY AUDIT
# ============================================================

wickets = df[df["is_wicket_clean"]].copy()

dismissal_counts = (
    wickets.groupby(
        "dismissal_type_clean",
        dropna=False
    )
    .agg(
        wicket_events=("match_id", "size"),
        matches=("match_id", "nunique")
    )
    .reset_index()
    .sort_values("wicket_events", ascending=False)
)

dismissal_counts.to_csv(
    REPORTS / "t20i_dismissal_category_audit.csv",
    index=False
)

total_wicket_events = len(wickets)

print("\nDISMISSAL CATEGORY AUDIT")
print(dismissal_counts.to_string(index=False))
print("\nTotal wicket records:", total_wicket_events)


# ============================================================
# 7. CORRECT BATTER DISMISSAL ATTRIBUTION
# ============================================================

# A batter dismissal belongs to dismissed_player_id,
# not necessarily striker_id.

# Create a player ID-to-name mapping using striker and non-striker
# appearances.

name_data = pd.concat([
    df[["striker_id", "striker_name"]].rename(
        columns={
            "striker_id": "player_id",
            "striker_name": "player_name"
        }
    ),
    df[["non_striker_id", "non_striker_name"]].rename(
        columns={
            "non_striker_id": "player_id",
            "non_striker_name": "player_name"
        }
    )
], ignore_index=True)

name_data = name_data.dropna(
    subset=["player_id", "player_name"]
)

name_data["player_id"] = pd.to_numeric(
    name_data["player_id"], errors="coerce"
)

name_data = name_data.dropna(subset=["player_id"])

name_map = (
    name_data.sort_values("player_name")
    .drop_duplicates("player_id")
    .set_index("player_id")["player_name"]
)

wickets["dismissed_player_id"] = pd.to_numeric(
    wickets["dismissed_player_id"], errors="coerce"
)

wickets["dismissed_player_name"] = (
    wickets["dismissed_player_id"].map(name_map)
)

wickets["dismissed_player_known"] = (
    wickets["dismissed_player_id"].notna()
)

wickets["is_striker_dismissed"] = (
    wickets["dismissed_player_id"] == wickets["striker_id"]
)

wickets["is_non_striker_dismissed"] = (
    wickets["dismissed_player_id"] == wickets["non_striker_id"]
)

wickets["is_other_player_dismissed"] = (
    wickets["dismissed_player_id"].notna()
    & ~wickets["is_striker_dismissed"]
    & ~wickets["is_non_striker_dismissed"]
)

batter_dismissal_audit = (
    wickets.groupby(
        "dismissal_type_clean",
        dropna=False
    )
    .agg(
        total_events=("match_id", "size"),
        identified_dismissed_player=(
            "dismissed_player_known", "sum"
        ),
        striker_dismissals=("is_striker_dismissed", "sum"),
        non_striker_dismissals=(
            "is_non_striker_dismissed", "sum"
        ),
        other_player_dismissals=(
            "is_other_player_dismissed", "sum"
        )
    )
    .reset_index()
)

batter_dismissal_audit.to_csv(
    REPORTS / "t20i_batter_dismissal_attribution_audit.csv",
    index=False
)

identified_wickets = wickets[
    wickets["dismissed_player_id"].notna()
].copy()

player_dismissals = (
    identified_wickets.groupby(
        ["dismissed_player_id", "dismissed_player_name"],
        dropna=False
    )
    .agg(
        total_dismissals=("match_id", "size"),
        pressure_dismissals=("is_pressure", "sum"),
        matches_dismissed=("match_id", "nunique")
    )
    .reset_index()
    .sort_values("total_dismissals", ascending=False)
)

player_dismissals.to_csv(
    REPORTS / "t20i_corrected_player_dismissals.csv",
    index=False
)

print("\nBATTER DISMISSAL ATTRIBUTION")
print(
    "Total wicket events:", total_wicket_events
)
print(
    "Identified dismissed players:",
    len(identified_wickets)
)
print(
    "Striker dismissals:",
    int(wickets["is_striker_dismissed"].sum())
)
print(
    "Non-striker dismissals:",
    int(wickets["is_non_striker_dismissed"].sum())
)
print(
    "Other-player dismissals:",
    int(wickets["is_other_player_dismissed"].sum())
)
print(
    "Missing dismissed-player IDs:",
    int(wickets["dismissed_player_id"].isna().sum())
)


# ============================================================
# 8. BOWLER-CREDIT WICKET AUDIT
# ============================================================

# Include common spelling variants.
# Do not count run-outs, retirements or obstructing the field.

bowler_credit_types = {
    "caught",
    "bowled",
    "lbw",
    "stump",
    "stumped",
    "hitwicket",
    "hit wicket"
}

wickets["is_bowler_credit_type"] = (
    wickets["dismissal_type_clean"].isin(
        bowler_credit_types
    )
)

wickets["is_bowler_credit_wicket"] = (
    wickets["is_bowler_credit_type"]
    & wickets["bowler_id"].notna()
)

bowler_wicket_counts = (
    wickets.groupby("dismissal_type_clean")
    .agg(
        wicket_events=("match_id", "size"),
        bowler_credit_type=("is_bowler_credit_type", "sum"),
        bowler_credit_wickets=("is_bowler_credit_wicket", "sum")
    )
    .reset_index()
)

bowler_wicket_counts.to_csv(
    REPORTS / "t20i_bowler_wicket_category_audit.csv",
    index=False
)

total_bowler_credit_wickets = int(
    wickets["is_bowler_credit_wicket"].sum()
)

missing_bowler_id_credit_types = int(
    (
        wickets["is_bowler_credit_type"]
        & wickets["bowler_id"].isna()
    ).sum()
)

print("\nBOWLER-CREDIT WICKET AUDIT")
print(bowler_wicket_counts.to_string(index=False))
print(
    "Total bowler-credit wickets:",
    total_bowler_credit_wickets
)
print(
    "Bowler-credit types with missing bowler ID:",
    missing_bowler_id_credit_types
)


# ============================================================
# 9. PLAYER PRESSURE AND NORMAL EXPOSURE
# ============================================================

# Batter exposure: balls faced and matches played in each group.

batter_balls = df[
    df["striker_id"].notna()
    & df["is_counted_delivery"]
    & (df["extras_clean"] != "wide")
    & (df["extras_clean"] != "penalty")
].copy()

batter_exposure = (
    batter_balls.groupby(
        ["striker_id", "striker_name", "is_pressure"]
    )
    .agg(
        balls=("match_id", "size"),
        runs=("batter_runs", "sum"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

batter_exposure["group"] = np.where(
    batter_exposure["is_pressure"],
    "pressure",
    "normal"
)

batter_exposure_wide = batter_exposure.pivot(
    index=["striker_id", "striker_name"],
    columns="group",
    values=["balls", "runs", "matches"]
)

batter_exposure_wide.columns = [
    f"{metric}_{group}"
    for metric, group in batter_exposure_wide.columns
]

batter_exposure_wide = batter_exposure_wide.reset_index()

# Ensure all columns exist even if a group is absent.

for col in [
    "balls_pressure", "runs_pressure", "matches_pressure",
    "balls_normal", "runs_normal", "matches_normal"
]:
    if col not in batter_exposure_wide.columns:
        batter_exposure_wide[col] = 0

batter_exposure_wide = batter_exposure_wide.fillna({
    "balls_pressure": 0,
    "runs_pressure": 0,
    "matches_pressure": 0,
    "balls_normal": 0,
    "runs_normal": 0,
    "matches_normal": 0
})

batter_exposure_wide["strike_rate_pressure"] = np.where(
    batter_exposure_wide["balls_pressure"] > 0,
    batter_exposure_wide["runs_pressure"] * 100
    / batter_exposure_wide["balls_pressure"],
    np.nan
)

batter_exposure_wide["strike_rate_normal"] = np.where(
    batter_exposure_wide["balls_normal"] > 0,
    batter_exposure_wide["runs_normal"] * 100
    / batter_exposure_wide["balls_normal"],
    np.nan
)

batter_exposure_wide["strike_rate_difference"] = (
    batter_exposure_wide["strike_rate_pressure"]
    - batter_exposure_wide["strike_rate_normal"]
)

# Correct dismissal attribution: use dismissed_player_id.
# Join the pressure state of the actual wicket event.

player_dismissals_exposure = (
    identified_wickets.groupby(
        ["dismissed_player_id", "is_pressure"]
    )
    .size()
    .unstack(fill_value=0)
)

player_dismissals_exposure = (
    player_dismissals_exposure.rename(
        columns={
            False: "dismissals_normal",
            True: "dismissals_pressure"
        }
    )
    .reset_index()
    .rename(columns={
        "dismissed_player_id": "striker_id"
    })
)

for col in ["dismissals_pressure", "dismissals_normal"]:
    if col not in player_dismissals_exposure.columns:
        player_dismissals_exposure[col] = 0

batter_exposure_wide = batter_exposure_wide.merge(
    player_dismissals_exposure,
    on="striker_id",
    how="left",
    validate="one_to_one"
)

batter_exposure_wide[
    ["dismissals_pressure", "dismissals_normal"]
] = batter_exposure_wide[
    ["dismissals_pressure", "dismissals_normal"]
].fillna(0)

batter_exposure_wide["dismissal_rate_pressure"] = np.where(
    batter_exposure_wide["balls_pressure"] > 0,
    batter_exposure_wide["dismissals_pressure"] * 100
    / batter_exposure_wide["balls_pressure"],
    np.nan
)

batter_exposure_wide["dismissal_rate_normal"] = np.where(
    batter_exposure_wide["balls_normal"] > 0,
    batter_exposure_wide["dismissals_normal"] * 100
    / batter_exposure_wide["balls_normal"],
    np.nan
)

batter_exposure_wide.to_csv(
    REPORTS / "t20i_batter_corrected_exposure_audit.csv",
    index=False
)


# ============================================================
# 10. BOWLER PRESSURE AND NORMAL EXPOSURE
# ============================================================

bowler_data = df[
    df["bowler_id"].notna()
    & df["is_counted_delivery"]
].copy()

bowler_data["bowler_legal_ball"] = (
    bowler_data["is_legal_ball"]
)

bowler_data["is_bowler_credit_wicket"] = (
    bowler_data["is_wicket_clean"]
    & bowler_data["dismissal_type_clean"].isin(
        bowler_credit_types
    )
    & bowler_data["bowler_id"].notna()
)

bowler_exposure = (
    bowler_data.groupby(
        ["bowler_id", "bowler_name", "is_pressure"]
    )
    .agg(
        delivery_records=("match_id", "size"),
        legal_balls=("bowler_legal_ball", "sum"),
        runs_conceded=("bowler_runs", "sum"),
        wickets=("is_bowler_credit_wicket", "sum"),
        matches=("match_id", "nunique")
    )
    .reset_index()
)

bowler_exposure["group"] = np.where(
    bowler_exposure["is_pressure"],
    "pressure",
    "normal"
)

bowler_exposure_wide = bowler_exposure.pivot(
    index=["bowler_id", "bowler_name"],
    columns="group",
    values=[
        "delivery_records", "legal_balls",
        "runs_conceded", "wickets", "matches"
    ]
)

bowler_exposure_wide.columns = [
    f"{metric}_{group}"
    for metric, group in bowler_exposure_wide.columns
]

bowler_exposure_wide = bowler_exposure_wide.reset_index()

for col in [
    "delivery_records_pressure", "legal_balls_pressure",
    "runs_conceded_pressure", "wickets_pressure",
    "matches_pressure", "delivery_records_normal",
    "legal_balls_normal", "runs_conceded_normal",
    "wickets_normal", "matches_normal"
]:
    if col not in bowler_exposure_wide.columns:
        bowler_exposure_wide[col] = 0

bowler_exposure_wide = bowler_exposure_wide.fillna(0)

bowler_exposure_wide["economy_pressure"] = np.where(
    bowler_exposure_wide["legal_balls_pressure"] > 0,
    bowler_exposure_wide["runs_conceded_pressure"] * 6
    / bowler_exposure_wide["legal_balls_pressure"],
    np.nan
)

bowler_exposure_wide["economy_normal"] = np.where(
    bowler_exposure_wide["legal_balls_normal"] > 0,
    bowler_exposure_wide["runs_conceded_normal"] * 6
    / bowler_exposure_wide["legal_balls_normal"],
    np.nan
)

bowler_exposure_wide["economy_difference"] = (
    bowler_exposure_wide["economy_pressure"]
    - bowler_exposure_wide["economy_normal"]
)

bowler_exposure_wide["wickets_per_100_pressure_balls"] = np.where(
    bowler_exposure_wide["legal_balls_pressure"] > 0,
    bowler_exposure_wide["wickets_pressure"] * 100
    / bowler_exposure_wide["legal_balls_pressure"],
    np.nan
)

bowler_exposure_wide["wickets_per_100_normal_balls"] = np.where(
    bowler_exposure_wide["legal_balls_normal"] > 0,
    bowler_exposure_wide["wickets_normal"] * 100
    / bowler_exposure_wide["legal_balls_normal"],
    np.nan
)

bowler_exposure_wide.to_csv(
    REPORTS / "t20i_bowler_corrected_exposure_audit.csv",
    index=False
)


# ============================================================
# 11. PRELIMINARY SAMPLE ELIGIBILITY
# ============================================================

# These are audit thresholds, not final ranking decisions.

BATTER_MIN_MATCHES = 8
BATTER_MIN_BALLS = 100

BOWLER_MIN_MATCHES = 8
BOWLER_MIN_BALLS = 120

batter_exposure_wide["eligible_pressure"] = (
    (batter_exposure_wide["matches_pressure"] >= BATTER_MIN_MATCHES)
    & (batter_exposure_wide["balls_pressure"] >= BATTER_MIN_BALLS)
)

batter_exposure_wide["eligible_normal"] = (
    (batter_exposure_wide["matches_normal"] >= BATTER_MIN_MATCHES)
    & (batter_exposure_wide["balls_normal"] >= BATTER_MIN_BALLS)
)

batter_exposure_wide["eligible_comparison"] = (
    batter_exposure_wide["eligible_pressure"]
    & batter_exposure_wide["eligible_normal"]
)

bowler_exposure_wide["eligible_pressure"] = (
    (bowler_exposure_wide["matches_pressure"] >= BOWLER_MIN_MATCHES)
    & (bowler_exposure_wide["legal_balls_pressure"] >= BOWLER_MIN_BALLS)
)

bowler_exposure_wide["eligible_normal"] = (
    (bowler_exposure_wide["matches_normal"] >= BOWLER_MIN_MATCHES)
    & (bowler_exposure_wide["legal_balls_normal"] >= BOWLER_MIN_BALLS)
)

bowler_exposure_wide["eligible_comparison"] = (
    bowler_exposure_wide["eligible_pressure"]
    & bowler_exposure_wide["eligible_normal"]
)

batter_exposure_wide.to_csv(
    REPORTS / "t20i_batter_corrected_exposure_audit.csv",
    index=False
)

bowler_exposure_wide.to_csv(
    REPORTS / "t20i_bowler_corrected_exposure_audit.csv",
    index=False
)


# ============================================================
# 12. FINAL INTEGRITY SUMMARY
# ============================================================

summary = [
    ["Total delivery records", len(df)],
    ["Total wicket events", total_wicket_events],
    ["Identified dismissed players", len(identified_wickets)],
    [
        "Missing dismissed-player IDs",
        int(wickets["dismissed_player_id"].isna().sum())
    ],
    ["Bowler-credit wickets", total_bowler_credit_wickets],
    ["Batter runs", total_batter_runs],
    ["Extras runs", total_extras_runs],
    ["Team runs", total_team_runs],
    ["Bowler runs conceded", total_bowler_runs],
    [
        "Run reconciliation difference",
        total_team_runs - total_batter_runs - total_extras_runs
    ],
    [
        "Extras requiring review",
        int(df["needs_extras_review"].sum())
    ],
    [
        "Eligible batters: pressure exposure",
        int(batter_exposure_wide["eligible_pressure"].sum())
    ],
    [
        "Eligible batters: normal exposure",
        int(batter_exposure_wide["eligible_normal"].sum())
    ],
    [
        "Eligible batters: both groups",
        int(batter_exposure_wide["eligible_comparison"].sum())
    ],
    [
        "Eligible bowlers: pressure exposure",
        int(bowler_exposure_wide["eligible_pressure"].sum())
    ],
    [
        "Eligible bowlers: normal exposure",
        int(bowler_exposure_wide["eligible_normal"].sum())
    ],
    [
        "Eligible bowlers: both groups",
        int(bowler_exposure_wide["eligible_comparison"].sum())
    ]
]

summary_df = pd.DataFrame(
    summary,
    columns=["metric", "value"]
)

summary_df.to_csv(
    REPORTS / "t20i_player_ranking_integrity_summary.csv",
    index=False
)

print("\n" + "=" * 80)
print("PLAYER EXPOSURE AND ELIGIBILITY")
print("=" * 80)

print(
    "Eligible batters - pressure:",
    int(batter_exposure_wide["eligible_pressure"].sum())
)
print(
    "Eligible batters - normal:",
    int(batter_exposure_wide["eligible_normal"].sum())
)
print(
    "Eligible batters - both:",
    int(batter_exposure_wide["eligible_comparison"].sum())
)

print(
    "Eligible bowlers - pressure:",
    int(bowler_exposure_wide["eligible_pressure"].sum())
)
print(
    "Eligible bowlers - normal:",
    int(bowler_exposure_wide["eligible_normal"].sum())
)
print(
    "Eligible bowlers - both:",
    int(bowler_exposure_wide["eligible_comparison"].sum())
)

print("\n" + "=" * 80)
print("STEP 63: INTEGRITY SUMMARY")
print("=" * 80)

print(summary_df.to_string(index=False))

print("\nGenerated reports:")

for name in [
    "t20i_run_reconciliation_audit.csv",
    "t20i_dismissal_category_audit.csv",
    "t20i_batter_dismissal_attribution_audit.csv",
    "t20i_corrected_player_dismissals.csv",
    "t20i_bowler_wicket_category_audit.csv",
    "t20i_batter_corrected_exposure_audit.csv",
    "t20i_bowler_corrected_exposure_audit.csv",
    "t20i_player_ranking_integrity_summary.csv"
]:
    print(" -", REPORTS / name)

print("\n" + "=" * 80)
print("STEP 63 COMPLETED")
print("=" * 80)
