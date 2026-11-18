
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

INPUT = REPORTS / "t20i_raw_deliveries.csv.gz"

print("=" * 75)
print("T20I DELIVERY RULES AUDIT")
print("=" * 75)

df = pd.read_csv(INPUT, low_memory=False)

# --------------------------------------------------
# 1. NORMALIZE SOURCE FIELDS
# --------------------------------------------------

df["extras_clean"] = (
    df["extras_type"]
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

for col in [
    "runs", "extras1_runs", "extras_2_runs",
    "overid", "over_ball_num", "innings_ball_num",
    "innings", "is_wicket"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# --------------------------------------------------
# 2. EXTRAS INVESTIGATION
# --------------------------------------------------

print("\n1. EXTRAS INVESTIGATION")

for extra in sorted(df["extras_clean"].unique()):

    if extra == "":
        continue

    print(f"\nEXTRAS TYPE: {extra}")

    subset = df[df["extras_clean"] == extra]

    print("Records:", len(subset))
    print("Batter runs:")
    print(subset["runs"].value_counts(dropna=False).to_string())

    print("Extras1 runs:")
    print(
        subset["extras1_runs"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("Extras2 runs:")
    print(
        subset["extras_2_runs"]
        .value_counts(dropna=False)
        .to_string()
    )

    print("Sample rows:")
    print(
        subset[
            [
                "match_id", "innings", "overid",
                "over_ball_num", "runs",
                "extras1_runs", "extras_2_runs",
                "is_wicket", "dismissal_clean"
            ]
        ].head(10).to_string(index=False)
    )

# --------------------------------------------------
# 3. OVER BALL NUMBER AUDIT
# --------------------------------------------------

print("\n" + "=" * 75)
print("2. OVER BALL NUMBER AUDIT")
print("=" * 75)

over_counts = (
    df.groupby(
        ["match_id", "innings", "overid"],
        dropna=False
    )
    .agg(
        delivery_records=("over_ball_num", "size"),
        min_sequence=("over_ball_num", "min"),
        max_sequence=("over_ball_num", "max"),
        unique_sequences=("over_ball_num", "nunique")
    )
    .reset_index()
)

print("\nOver delivery-record count distribution:")
print(
    over_counts["delivery_records"]
    .value_counts()
    .sort_index()
    .to_string()
)

print("\nOvers with over_ball_num greater than 6:")
print(
    df.loc[
        df["over_ball_num"] > 6,
        [
            "match_id", "innings", "overid",
            "over_ball_num", "extras_clean",
            "runs", "extras1_runs", "extras_2_runs"
        ]
    ].head(30).to_string(index=False)
)

print(
    "\nTotal records with over_ball_num > 6:",
    int((df["over_ball_num"] > 6).sum())
)

# --------------------------------------------------
# 4. INNINGS 3 AND 4 INVESTIGATION
# --------------------------------------------------

print("\n" + "=" * 75)
print("3. EXTRA INNINGS INVESTIGATION")
print("=" * 75)

extra_innings = df[df["innings"] > 2]

print("Records in innings above 2:", len(extra_innings))

if len(extra_innings) > 0:

    print("\nMatches containing innings above 2:")

    print(
        extra_innings.groupby(
            ["match_id", "innings"]
        ).agg(
            records=("runs", "size"),
            runs=("runs", "sum"),
            wickets=("is_wicket", "sum"),
            max_over=("overid", "max")
        ).reset_index().to_string(index=False)
    )

# --------------------------------------------------
# 5. WICKET AND DISMISSAL AUDIT
# --------------------------------------------------

print("\n" + "=" * 75)
print("4. WICKET AND DISMISSAL AUDIT")
print("=" * 75)

wickets = df[df["is_wicket"] == 1].copy()

print("Wicket records:", len(wickets))

print("\nDismissal type distribution:")
print(
    wickets["dismissal_clean"]
    .value_counts(dropna=False)
    .to_string()
)

print("\nWickets with missing dismissed player ID:")
print(
    wickets["dismissed_player_id"]
    .isna()
    .sum()
)

print("\nDismissal types with missing bowler ID:")
print(
    wickets.loc[
        wickets["bowler_id"].isna(),
        "dismissal_clean"
    ].value_counts(dropna=False).to_string()
)

# --------------------------------------------------
# 6. RUN RECONCILIATION
# --------------------------------------------------

print("\n" + "=" * 75)
print("5. RUN RECONCILIATION")
print("=" * 75)

df["reconstructed_total"] = (
    df["runs"].fillna(0) +
    df["extras1_runs"].fillna(0) +
    df["extras_2_runs"].fillna(0)
)

# The source does not provide a separate team total per delivery.
# This checks arithmetic consistency and missing numeric fields.

print(
    "Missing runs:",
    df["runs"].isna().sum()
)

print(
    "Missing extras1_runs:",
    df["extras1_runs"].isna().sum()
)

print(
    "Missing extras_2_runs:",
    df["extras_2_runs"].isna().sum()
)

print(
    "Reconstructed total runs:",
    int(df["reconstructed_total"].sum())
)

# --------------------------------------------------
# 7. CANDIDATE LEGAL-BALL ASSUMPTION
# --------------------------------------------------

print("\n" + "=" * 75)
print("6. CANDIDATE LEGAL-BALL CLASSIFICATION")
print("=" * 75)

# Provisional only: validate against source documentation.
illegal_candidates = ["wide", "overstep", "other"]

df["candidate_legal_ball"] = (
    ~df["extras_clean"].isin(illegal_candidates)
)

print(
    "Candidate legal deliveries:",
    int(df["candidate_legal_ball"].sum())
)

print(
    "Candidate illegal deliveries:",
    int((~df["candidate_legal_ball"]).sum())
)

print("\nCandidate legal-ball counts by extras:")
print(
    df.groupby("extras_clean")["candidate_legal_ball"]
    .agg(["count", "sum"])
    .to_string()
)

# --------------------------------------------------
# 8. SAVE AUDIT OUTPUTS
# --------------------------------------------------

over_counts.to_csv(
    REPORTS / "t20i_over_delivery_audit.csv",
    index=False
)

wickets.to_csv(
    REPORTS / "t20i_wicket_events_audit.csv",
    index=False
)

print("\nSaved:")
print(" - reports/t20i_over_delivery_audit.csv")
print(" - reports/t20i_wicket_events_audit.csv")

print("\nT20I delivery rules audit completed.")
