
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"

print("\n" + "=" * 75)
print("STEP 50: T20I TARGET AND INNINGS RECONCILIATION")
print("=" * 75)

# ---------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------

innings = pd.read_csv(
    REPORTS / "t20i_reconstructed_innings_summary.csv"
)

matches = pd.read_csv(RAW / "matches.csv")
competitions = pd.read_csv(RAW / "competitions.csv")

competitions["match_format"] = (
    competitions["match_format"].astype(str).str.strip().str.upper()
)

t20i_comp_ids = competitions.loc[
    competitions["match_format"] == "T20I",
    "comp_id"
]

matches = matches[
    matches["comp_id"].isin(t20i_comp_ids)
].copy()


# ---------------------------------------------------------
# 2. JOIN MATCH METADATA
# ---------------------------------------------------------

# The innings summary already contains match metadata.
# Use only the required columns from matches.csv that are
# not already present in the innings summary.

metadata = [
    "match_id",
    "match_date",
    "home_team",
    "away_team",
    "result",
]

metadata = [
    col for col in metadata
    if col not in innings.columns
]

audit = innings.merge(
    matches[["match_id"] + metadata].drop_duplicates("match_id"),
    on="match_id",
    how="left",
    validate="many_to_one"
)

audit["source_revised_limit"] = audit.apply(
    lambda r: (
        r["first_inn_revised_overs"]
        if r["innings"] == 1
        else r["second_inn_revised_overs"]
    ),
    axis=1
)

audit["source_revised_limit"] = pd.to_numeric(
    audit["source_revised_limit"],
    errors="coerce"
)

audit["revised_target"] = pd.to_numeric(
    audit["revised_target"],
    errors="coerce"
)


# ---------------------------------------------------------
# 3. DISPLAY SCENARIO DISTRIBUTION
# ---------------------------------------------------------

print("\n" + "-" * 75)
print("RECONSTRUCTION SCENARIOS")
print("-" * 75)

print(audit["scenario"].value_counts(dropna=False).to_string())

# ---------------------------------------------------------
# 4. CHECK MATCHES WITH BOTH INNINGS
# ---------------------------------------------------------

match_pivot = audit.pivot_table(
    index="match_id",
    columns="innings",
    values="team_runs",
    aggfunc="first"
).reset_index()

match_pivot = match_pivot.rename(columns={
    1: "first_innings_runs",
    2: "second_innings_runs",
})

match_pivot = match_pivot.merge(
    matches[[
        "match_id",
        "match_date",
        "home_team",
        "away_team",
        "revised_target",
        "result",
    ]].drop_duplicates("match_id"),
    on="match_id",
    how="left",
    validate="one_to_one"
)

# ---------------------------------------------------------
# 5. CALCULATE TARGET CANDIDATES
# ---------------------------------------------------------

# Ordinary second-innings target:
# first innings score + 1.

match_pivot["ordinary_target"] = (
    match_pivot["first_innings_runs"] + 1
)

# Where a revised target is available, use it as the
# source-reported target for the chase.
match_pivot["effective_target"] = (
    match_pivot["revised_target"].fillna(
        match_pivot["ordinary_target"]
    )
)

match_pivot["target_source"] = "first_innings_score_plus_1"

match_pivot.loc[
    match_pivot["revised_target"].notna(),
    "target_source"
] = "source_revised_target"

# ---------------------------------------------------------
# 6. CHECK TARGET AND SCORE RELATIONSHIPS
# ---------------------------------------------------------

match_pivot["second_innings_score_difference"] = (
    match_pivot["second_innings_runs"] -
    match_pivot["effective_target"]
)

match_pivot["chase_reached_target"] = (
    match_pivot["second_innings_runs"] >=
    match_pivot["effective_target"]
)

print("\n" + "-" * 75)
print("MATCH AND TARGET RECONCILIATION")
print("-" * 75)

print("Matches with both innings:", len(match_pivot))

print(
    "\nTarget source distribution:\n",
    match_pivot["target_source"].value_counts().to_string()
)

print(
    "\nRevised target matches with both innings:",
    int(
        (
            match_pivot["revised_target"].notna() &
            match_pivot["second_innings_runs"].notna()
        ).sum()
    )
)

print(
    "\nSecond innings reaching effective target:",
    int(match_pivot["chase_reached_target"].sum())
)

# ---------------------------------------------------------
# 7. DISPLAY REVISED TARGET MATCHES
# ---------------------------------------------------------

revised_cases = match_pivot[
    match_pivot["revised_target"].notna()
].copy()

print("\n" + "-" * 75)
print("REVISED TARGET CASES")
print("-" * 75)

columns = [
    "match_id",
    "match_date",
    "home_team",
    "away_team",
    "first_innings_runs",
    "ordinary_target",
    "revised_target",
    "second_innings_runs",
    "effective_target",
    "second_innings_score_difference",
    "result",
]

print(
    revised_cases[columns].to_string(index=False)
)

# ---------------------------------------------------------
# 8. CHECK MISSING INNINGS
# ---------------------------------------------------------

print("\n" + "-" * 75)
print("INNINGS COVERAGE")
print("-" * 75)

print(
    "Matches with only first innings:",
    int(
        (
            match_pivot["first_innings_runs"].notna() &
            match_pivot["second_innings_runs"].isna()
        ).sum()
    )
)

print(
    "Matches with only second innings:",
    int(
        (
            match_pivot["first_innings_runs"].isna() &
            match_pivot["second_innings_runs"].notna()
        ).sum()
    )
)

print(
    "Matches with both innings:",
    int(
        (
            match_pivot["first_innings_runs"].notna() &
            match_pivot["second_innings_runs"].notna()
        ).sum()
    )
)

# ---------------------------------------------------------
# 9. SAVE OUTPUTS
# ---------------------------------------------------------

match_pivot.to_csv(
    REPORTS / "t20i_match_target_reconciliation.csv",
    index=False
)

revised_cases.to_csv(
    REPORTS / "t20i_revised_target_reconciliation.csv",
    index=False
)

audit.to_csv(
    REPORTS / "t20i_innings_metadata_reconciliation.csv",
    index=False
)

summary = {
    "innings_rows": int(len(audit)),
    "matches_with_innings_data": int(len(match_pivot)),
    "matches_with_both_innings": int(
        (
            match_pivot["first_innings_runs"].notna() &
            match_pivot["second_innings_runs"].notna()
        ).sum()
    ),
    "revised_target_cases": int(len(revised_cases)),
    "revised_target_cases_with_both_innings": int(
        (
            revised_cases["first_innings_runs"].notna() &
            revised_cases["second_innings_runs"].notna()
        ).sum()
    ),
    "scenario_distribution": {
        str(k): int(v)
        for k, v in audit["scenario"].value_counts(
            dropna=False
        ).items()
    },
}

with open(
    REPORTS / "t20i_target_reconciliation_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)

print("\n" + "=" * 75)
print("STEP 50 COMPLETED")
print("=" * 75)

print(json.dumps(summary, indent=4))
print("\nReports saved in:", REPORTS)
