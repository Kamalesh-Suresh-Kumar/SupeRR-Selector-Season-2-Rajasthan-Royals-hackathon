
from pathlib import Path
import pandas as pd
import numpy as np
import json

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# ---------------------------------------------------------
# 1. LOAD RECONSTRUCTED T20I DATA
# ---------------------------------------------------------

deliveries = pd.read_csv(
    REPORTS / "t20i_reconstructed_deliveries.csv.gz",
    low_memory=False
)

innings = pd.read_csv(
    REPORTS / "t20i_reconstructed_innings_summary.csv",
    low_memory=False
)

matches = pd.read_csv(
    DATA / "matches.csv",
    low_memory=False
)

competitions = pd.read_csv(
    DATA / "competitions.csv",
    low_memory=False
)

# ---------------------------------------------------------
# 2. FILTER T20I MATCHES
# ---------------------------------------------------------

t20i_comp_ids = set(
    competitions.loc[
        competitions["match_format"].astype(str).str.upper() == "T20I",
        "comp_id"
    ]
)

matches["match_id"] = pd.to_numeric(
    matches["match_id"], errors="coerce"
)

matches = matches[
    matches["comp_id"].isin(t20i_comp_ids)
].copy()

# ---------------------------------------------------------
# 3. NORMALIZE NUMERIC FIELDS
# ---------------------------------------------------------

for col in [
    "first_inn_revised_overs",
    "second_inn_revised_overs",
    "revised_target",
]:
    if col in matches.columns:
        matches[col] = pd.to_numeric(
            matches[col], errors="coerce"
        )

for col in [
    "match_id", "innings", "legal_balls",
    "team_runs", "wickets"
]:
    innings[col] = pd.to_numeric(
        innings[col], errors="coerce"
    )


# ---------------------------------------------------------
# 4. JOIN INNINGS TO MATCH METADATA
# ---------------------------------------------------------

# Step 46 already included match metadata in the innings summary.
# Keep only the actual innings metrics here, then attach fresh
# metadata from matches.csv to avoid duplicate column names.

base_columns = [
    "match_id",
    "innings",
    "legal_balls",
    "team_runs",
    "wickets",
]

missing_columns = [
    col for col in base_columns
    if col not in innings.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required innings columns: {missing_columns}"
    )

innings_base = innings[base_columns].copy()

metadata_cols = [
    "match_id",
    "match_date",
    "stage",
    "home_team",
    "away_team",
    "result",
    "first_inn_revised_overs",
    "second_inn_revised_overs",
    "revised_target",
]

metadata_cols = [
    col for col in metadata_cols
    if col in matches.columns
]

audit = innings_base.merge(
    matches[metadata_cols].drop_duplicates("match_id"),
    on="match_id",
    how="left",
    validate="many_to_one"
)

# ---------------------------------------------------------
# 5. SELECT OVERS FIELD FOR EACH INNINGS
# ---------------------------------------------------------

audit["source_overs_value"] = np.where(
    audit["innings"] == 1,
    audit["first_inn_revised_overs"],
    audit["second_inn_revised_overs"]
)

# ---------------------------------------------------------
# 6. CALCULATE TWO POSSIBLE OVERS INTERPRETATIONS
# ---------------------------------------------------------

def decimal_overs_to_balls(value):
    if pd.isna(value):
        return np.nan
    return value * 6


def cricket_notation_to_balls(value):
    if pd.isna(value):
        return np.nan

    whole = int(np.floor(value))
    fraction = round((value - whole) * 10, 6)

    if fraction < 0 or fraction > 5:
        return np.nan

    if abs(fraction - round(fraction)) > 1e-6:
        return np.nan

    return whole * 6 + int(round(fraction))


audit["limit_balls_decimal_candidate"] = (
    audit["source_overs_value"].apply(decimal_overs_to_balls)
)

audit["limit_balls_cricket_notation_candidate"] = (
    audit["source_overs_value"].apply(cricket_notation_to_balls)
)

# Standard T20 limit is 20 overs only as a comparison baseline.
# This is not automatically substituted for missing revised values.
audit["standard_20_over_limit"] = 120

audit["actual_legal_balls"] = audit["legal_balls"]

audit["decimal_candidate_difference"] = (
    audit["limit_balls_decimal_candidate"]
    - audit["actual_legal_balls"]
)

audit["cricket_notation_candidate_difference"] = (
    audit["limit_balls_cricket_notation_candidate"]
    - audit["actual_legal_balls"]
)

# ---------------------------------------------------------
# 7. REPORT OVERS VALUE DISTRIBUTION
# ---------------------------------------------------------

print("\n" + "=" * 75)
print("STEP 47: REVISED OVERS AND TARGET AUDIT")
print("=" * 75)

print("\nRaw revised overs values:")
for col in [
    "first_inn_revised_overs",
    "second_inn_revised_overs"
]:
    if col in matches.columns:
        print(f"\n{col}")
        print(
            matches[col]
            .value_counts(dropna=False)
            .sort_index()
            .to_string()
        )

# ---------------------------------------------------------
# 8. FRACTIONAL VALUE VALIDATION
# ---------------------------------------------------------

print("\n" + "-" * 75)
print("FRACTIONAL OVERS VALUE AUDIT")
print("-" * 75)

fraction_rows = []

for col in [
    "first_inn_revised_overs",
    "second_inn_revised_overs"
]:
    values = matches[col].dropna()

    for value in sorted(values.unique()):
        whole = int(np.floor(value))
        fraction = round((value - whole) * 10, 6)

        fraction_rows.append({
            "field": col,
            "raw_value": value,
            "whole_part": whole,
            "fraction_digit_candidate": fraction,
            "valid_cricket_ball_notation": (
                fraction in [0, 1, 2, 3, 4, 5]
            ),
            "decimal_times_six": value * 6,
        })

fraction_df = pd.DataFrame(fraction_rows)

print(
    fraction_df.head(100).to_string(index=False)
    if len(fraction_df)
    else "No revised overs values available."
)

fraction_df.to_csv(
    REPORTS / "t20i_revised_overs_fraction_audit.csv",
    index=False
)

# ---------------------------------------------------------
# 9. COMPARE CANDIDATE LIMITS WITH ACTUAL LEGAL BALLS
# ---------------------------------------------------------

print("\n" + "-" * 75)
print("CANDIDATE OVERS LIMIT VALIDATION")
print("-" * 75)

has_revised_overs = audit["source_overs_value"].notna()

print("Innings with revised overs value:", int(has_revised_overs.sum()))
print("Innings without revised overs value:", int((~has_revised_overs).sum()))

for label, col in [
    ("Decimal overs x 6", "limit_balls_decimal_candidate"),
    ("Cricket notation", "limit_balls_cricket_notation_candidate"),
]:
    valid = audit[has_revised_overs & audit[col].notna()].copy()

    if len(valid):
        exceeded = valid[
            valid["actual_legal_balls"] > valid[col] + 1e-6
        ]

        equal = valid[
            (valid["actual_legal_balls"] - valid[col]).abs() <= 1e-6
        ]

        below = valid[
            valid["actual_legal_balls"] < valid[col] - 1e-6
        ]

        print(f"\n{label}")
        print("Comparable innings:", len(valid))
        print("Actual legal balls equal limit:", len(equal))
        print("Actual legal balls below limit:", len(below))
        print("Actual legal balls above limit:", len(exceeded))

# ---------------------------------------------------------
# 10. LIST INNINGS WHERE CANDIDATES DISAGREE
# ---------------------------------------------------------

candidate_disagreement = audit[
    has_revised_overs
    & audit["limit_balls_decimal_candidate"].notna()
    & audit["limit_balls_cricket_notation_candidate"].notna()
    & (
        (
            audit["limit_balls_decimal_candidate"]
            - audit["limit_balls_cricket_notation_candidate"]
        ).abs() > 1e-6
    )
].copy()

print("\nCandidate interpretations disagree on:",
      len(candidate_disagreement), "innings")

disagreement_cols = [
    "match_id", "match_date", "innings",
    "home_team", "away_team",
    "source_overs_value", "actual_legal_balls",
    "limit_balls_decimal_candidate",
    "limit_balls_cricket_notation_candidate",
    "team_runs", "wickets", "result",
]

disagreement_cols = [
    c for c in disagreement_cols if c in candidate_disagreement.columns
]

print(
    candidate_disagreement[disagreement_cols]
    .head(100)
    .to_string(index=False)
)

candidate_disagreement.to_csv(
    REPORTS / "t20i_overs_interpretation_disagreements.csv",
    index=False
)

# ---------------------------------------------------------
# 11. REVISED TARGET AUDIT
# ---------------------------------------------------------

print("\n" + "-" * 75)
print("REVISED TARGET AUDIT")
print("-" * 75)

target_matches = matches[
    matches["revised_target"].notna()
].copy()

print("Matches with revised_target:", len(target_matches))

if len(target_matches):
    print(
        target_matches[
            [
                c for c in [
                    "match_id", "match_date",
                    "home_team", "away_team",
                    "first_inn_revised_overs",
                    "second_inn_revised_overs",
                    "revised_target", "result"
                ]
                if c in target_matches.columns
            ]
        ].to_string(index=False)
    )

target_matches.to_csv(
    REPORTS / "t20i_revised_target_matches.csv",
    index=False
)

# ---------------------------------------------------------
# 12. INNINGS WITH UNUSUAL LEGAL BALL COUNTS
# ---------------------------------------------------------

print("\n" + "-" * 75)
print("LEGAL BALL COUNT DISTRIBUTION")
print("-" * 75)

print(
    audit["actual_legal_balls"]
    .describe(percentiles=[0.25, 0.5, 0.75, 0.9])
    .to_string()
)

unusual_balls = audit[
    (audit["actual_legal_balls"] > 120)
    | (audit["actual_legal_balls"] < 0)
].copy()

print("Innings above 120 or below 0 legal balls:", len(unusual_balls))

unusual_balls.to_csv(
    REPORTS / "t20i_unusual_innings_ball_counts.csv",
    index=False
)

# ---------------------------------------------------------
# 13. SAVE COMPLETE AUDIT
# ---------------------------------------------------------

audit.to_csv(
    REPORTS / "t20i_revised_overs_innings_audit.csv",
    index=False
)

summary = {
    "t20i_innings_rows": int(len(audit)),
    "innings_with_revised_overs": int(has_revised_overs.sum()),
    "innings_without_revised_overs": int((~has_revised_overs).sum()),
    "candidate_disagreement_rows": int(len(candidate_disagreement)),
    "matches_with_revised_target": int(len(target_matches)),
    "innings_above_120_legal_balls": int(len(unusual_balls)),
}

with open(
    REPORTS / "t20i_revised_overs_target_audit_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)

print("\n" + "=" * 75)
print("STEP 47 COMPLETED")
print("=" * 75)
print(json.dumps(summary, indent=4))
print("\nReports saved in:", REPORTS)
