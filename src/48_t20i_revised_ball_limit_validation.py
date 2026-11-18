
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"

REPORTS.mkdir(parents=True, exist_ok=True)

print("\n" + "=" * 75)
print("STEP 48: T20I REVISED BALL-LIMIT VALIDATION")
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
    competitions["match_format"].astype(str).str.strip()
)

t20i_comp_ids = competitions.loc[
    competitions["match_format"].str.upper() == "T20I",
    "comp_id"
]

matches = matches[matches["comp_id"].isin(t20i_comp_ids)].copy()

required_innings = [
    "match_id", "innings", "legal_balls", "team_runs", "wickets"
]

missing = [c for c in required_innings if c not in innings.columns]

if missing:
    raise ValueError(f"Missing innings columns: {missing}")

required_matches = [
    "match_id",
    "match_date",
    "home_team",
    "away_team",
    "first_inn_revised_overs",
    "second_inn_revised_overs",
    "revised_target",
    "result",
]

missing = [c for c in required_matches if c not in matches.columns]

if missing:
    raise ValueError(f"Missing match columns: {missing}")

# ---------------------------------------------------------
# 2. PREPARE MATCH METADATA
# ---------------------------------------------------------

audit = innings[required_innings].copy()

audit = audit.merge(
    matches[required_matches].drop_duplicates("match_id"),
    on="match_id",
    how="left",
    validate="many_to_one"
)

audit["source_revised_value"] = audit.apply(
    lambda r: (
        r["first_inn_revised_overs"]
        if r["innings"] == 1
        else r["second_inn_revised_overs"]
    ),
    axis=1
)

audit["source_revised_value"] = pd.to_numeric(
    audit["source_revised_value"],
    errors="coerce"
)

audit["legal_balls"] = pd.to_numeric(
    audit["legal_balls"],
    errors="coerce"
)

# ---------------------------------------------------------
# 3. TEST THREE POSSIBLE INTERPRETATIONS
# ---------------------------------------------------------

# Candidate 1: source value is already a legal-ball limit.
audit["candidate_direct_balls"] = audit["source_revised_value"]

# Candidate 2: source value is overs multiplied by six.
audit["candidate_overs_times_6"] = (
    audit["source_revised_value"] * 6
)

# Candidate 3: source value is a whole-over count.
audit["candidate_whole_overs"] = (
    audit["source_revised_value"].apply(
        lambda x: x * 6 if pd.notna(x) else None
    )
)

has_limit = audit["source_revised_value"].notna()

def compare_limit(candidate):
    comparable = audit[has_limit & audit[candidate].notna()].copy()

    return {
        "comparable_innings": int(len(comparable)),
        "actual_equal_limit": int(
            (comparable["legal_balls"] == comparable[candidate]).sum()
        ),
        "actual_below_limit": int(
            (comparable["legal_balls"] < comparable[candidate]).sum()
        ),
        "actual_above_limit": int(
            (comparable["legal_balls"] > comparable[candidate]).sum()
        ),
        "invalid_negative_limits": int(
            (comparable[candidate] < 0).sum()
        ),
    }

print("\n" + "-" * 75)
print("INTERPRETATION COMPARISON")
print("-" * 75)

results = {
    "direct_ball_limit": compare_limit("candidate_direct_balls"),
    "source_value_times_6": compare_limit("candidate_overs_times_6"),
}

for name, result in results.items():
    print(f"\n{name}")
    for key, value in result.items():
        print(f"{key}: {value}")

# ---------------------------------------------------------
# 4. CHECK WHETHER VALUES ARE MULTIPLES OF SIX
# ---------------------------------------------------------

values = (
    audit.loc[has_limit, "source_revised_value"]
    .dropna()
    .drop_duplicates()
    .sort_values()
)

print("\n" + "-" * 75)
print("SOURCE VALUE PATTERN")
print("-" * 75)

print("Unique source values:")
print(values.to_list())

print(
    "\nValues divisible by 6:",
    int((values % 6 == 0).sum()),
    "of",
    len(values)
)

print(
    "Values not divisible by 6:",
    int((values % 6 != 0).sum())
)

# ---------------------------------------------------------
# 5. SHOW DIRECT-BALL-LIMIT EXCEPTIONS
# ---------------------------------------------------------

revised = audit[has_limit].copy()

revised["direct_limit_difference"] = (
    revised["candidate_direct_balls"] - revised["legal_balls"]
)

exceptions = revised[
    revised["legal_balls"] > revised["candidate_direct_balls"]
].copy()

display_columns = [
    "match_id",
    "match_date",
    "innings",
    "home_team",
    "away_team",
    "source_revised_value",
    "legal_balls",
    "direct_limit_difference",
    "team_runs",
    "wickets",
    "result",
]

print("\n" + "-" * 75)
print("INNINGS EXCEEDING DIRECT-BALL INTERPRETATION")
print("-" * 75)

print("Exception count:", len(exceptions))

if len(exceptions):
    print(exceptions[display_columns].to_string(index=False))
else:
    print("No innings exceeded the proposed direct-ball limit.")

# ---------------------------------------------------------
# 6. CHECK REVISED TARGET MATCHES
# ---------------------------------------------------------

target_matches = matches[
    matches["revised_target"].notna()
].copy()

target_matches = target_matches[
    [
        "match_id",
        "match_date",
        "home_team",
        "away_team",
        "first_inn_revised_overs",
        "second_inn_revised_overs",
        "revised_target",
        "result",
    ]
]

target_matches = target_matches.sort_values(
    ["match_date", "match_id"]
)

print("\n" + "-" * 75)
print("REVISED TARGET MATCHES")
print("-" * 75)

print("Matches:", len(target_matches))
print(target_matches.to_string(index=False))

# ---------------------------------------------------------
# 7. SAVE AUDIT FILES
# ---------------------------------------------------------

audit.to_csv(
    REPORTS / "t20i_revised_ball_limit_full_audit.csv",
    index=False
)

exceptions.to_csv(
    REPORTS / "t20i_revised_ball_limit_exceptions.csv",
    index=False
)

target_matches.to_csv(
    REPORTS / "t20i_revised_target_matches_step48.csv",
    index=False
)

summary = {
    "innings_with_revised_limit": int(has_limit.sum()),
    "innings_without_revised_limit": int((~has_limit).sum()),
    "source_values_all_multiples_of_6": bool(
        len(values) > 0 and (values % 6 == 0).all()
    ),
    "direct_ball_interpretation": results["direct_ball_limit"],
    "times_6_interpretation": results["source_value_times_6"],
    "direct_ball_limit_exceptions": int(len(exceptions)),
    "revised_target_matches": int(len(target_matches)),
}

with open(
    REPORTS / "t20i_revised_ball_limit_validation_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)

print("\n" + "=" * 75)
print("STEP 48 COMPLETED")
print("=" * 75)

print(json.dumps(summary, indent=4))

print("\nReports saved in:", REPORTS)
