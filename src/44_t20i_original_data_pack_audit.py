
from pathlib import Path
import pandas as pd
import json

# ---------------------------------------------------------
# STEP 44: ORIGINAL T20I DATA-PACK AUDIT
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

REQUIRED_FILES = [
    "ball_by_ball.csv",
    "matches.csv",
    "competitions.csv",
    "teams.csv",
    "competition_team_player_mapping.csv",
    "playing_eleven.csv",
]


def locate_file(filename):
    matches = [
        p for p in ROOT.rglob(filename)
        if "__MACOSX" not in p.parts
    ]

    if not matches:
        raise FileNotFoundError(
            f"Could not find {filename} inside {ROOT}\n"
            "Extract the original data pack somewhere inside the project folder."
        )

    if len(matches) > 1:
        print(f"\nMultiple copies of {filename} found:")
        for p in matches:
            print(" -", p.relative_to(ROOT))
        print("Using:", matches[0].relative_to(ROOT))

    return matches[0]


def read_csv(filename):
    path = locate_file(filename)
    print(f"Loaded: {path.relative_to(ROOT)}")
    return pd.read_csv(path, low_memory=False)


def section(title):
    print("\n" + "=" * 75)
    print(title)
    print("=" * 75)


# ---------------------------------------------------------
# 1. LOAD ORIGINAL FILES
# ---------------------------------------------------------

print("PROJECT ROOT:", ROOT)

data = {}

for filename in REQUIRED_FILES:
    data[filename] = read_csv(filename)

balls = data["ball_by_ball.csv"].copy()
matches = data["matches.csv"].copy()
competitions = data["competitions.csv"].copy()
teams = data["teams.csv"].copy()
player_map = data["competition_team_player_mapping.csv"].copy()
playing_xi = data["playing_eleven.csv"].copy()


# ---------------------------------------------------------
# 2. BASIC DATASET DIMENSIONS
# ---------------------------------------------------------

section("1. DATASET DIMENSIONS")

dimensions = []

for filename, df in data.items():
    dimensions.append({
        "file": filename,
        "rows": len(df),
        "columns": len(df.columns),
    })

dimensions_df = pd.DataFrame(dimensions)

print(dimensions_df.to_string(index=False))
dimensions_df.to_csv(
    REPORTS / "t20i_source_file_dimensions.csv",
    index=False
)


# ---------------------------------------------------------
# 3. COMPETITION FORMAT VALIDATION
# ---------------------------------------------------------

section("2. COMPETITION FORMAT VALIDATION")

print("Competition format counts:")
print(competitions["match_format"].value_counts(dropna=False))

print("\nCompetition seasons:")
print(
    competitions.groupby(
        ["match_format", "season"],
        dropna=False
    ).size().to_string()
)

t20i_competitions = competitions[
    competitions["match_format"].astype(str).str.upper() == "T20I"
].copy()

print("\nT20I competitions:", len(t20i_competitions))
print("All competitions:", len(competitions))

valid_comp_ids = set(t20i_competitions["comp_id"])

matches["match_date"] = pd.to_datetime(
    matches["match_date"],
    errors="coerce"
)

matches_t20i = matches[
    matches["comp_id"].isin(valid_comp_ids)
].copy()

print("T20I matches:", len(matches_t20i))

if len(matches_t20i) > 0:
    print("Match date range:",
          matches_t20i["match_date"].min(),
          "to",
          matches_t20i["match_date"].max())


# ---------------------------------------------------------
# 4. DELIVERY-TO-MATCH RELATIONSHIP
# ---------------------------------------------------------

section("3. DELIVERY-TO-MATCH RELATIONSHIP")

balls["match_id"] = pd.to_numeric(
    balls["match_id"], errors="coerce"
)

matches_t20i["match_id"] = pd.to_numeric(
    matches_t20i["match_id"], errors="coerce"
)

t20i_match_ids = set(matches_t20i["match_id"].dropna())

balls_t20i = balls[
    balls["match_id"].isin(t20i_match_ids)
].copy()

unmatched_delivery_rows = balls[
    ~balls["match_id"].isin(t20i_match_ids)
].copy()

print("Original delivery rows:", len(balls))
print("T20I delivery rows:", len(balls_t20i))
print("Rows outside T20I match list:", len(unmatched_delivery_rows))
print("T20I unique matches in deliveries:",
      balls_t20i["match_id"].nunique())

print("\nDelivery innings distribution:")
print(balls_t20i["innings"].value_counts(dropna=False).sort_index())

print("\nMatches with delivery data but no match metadata:",
      len(unmatched_delivery_rows["match_id"].dropna().unique()))


# ---------------------------------------------------------
# 5. DATE AND SEASON COVERAGE
# ---------------------------------------------------------

section("4. DATE AND SEASON COVERAGE")

date_summary = matches_t20i.groupby(
    matches_t20i["match_date"].dt.year
).agg(
    matches=("match_id", "nunique"),
    competitions=("comp_id", "nunique")
).reset_index(names="year")

print(date_summary.to_string(index=False))

date_summary.to_csv(
    REPORTS / "t20i_source_year_coverage.csv",
    index=False
)


# ---------------------------------------------------------
# 6. DUPLICATE DELIVERY AUDIT
# ---------------------------------------------------------

section("5. DUPLICATE DELIVERY AUDIT")

delivery_key = [
    "match_id",
    "innings",
    "overid",
    "over_ball_num",
]

missing_key_columns = [
    c for c in delivery_key if c not in balls_t20i.columns
]

if missing_key_columns:
    raise ValueError(
        f"Missing delivery key columns: {missing_key_columns}"
    )

duplicate_mask = balls_t20i.duplicated(
    subset=delivery_key,
    keep=False
)

duplicates = balls_t20i[duplicate_mask].copy()

print("Duplicate delivery rows:", len(duplicates))
print("Duplicate delivery groups:",
      duplicates.groupby(delivery_key, dropna=False).ngroups
      if len(duplicates) else 0)

duplicates.to_csv(
    REPORTS / "t20i_source_duplicate_deliveries.csv",
    index=False
)


# ---------------------------------------------------------
# 7. MISSING VALUE AUDIT
# ---------------------------------------------------------

section("6. MISSING VALUE AUDIT")

important_columns = [
    "match_id",
    "innings",
    "overid",
    "over_ball_num",
    "innings_ball_num",
    "striker_id",
    "striker_name",
    "non_striker_id",
    "non_striker_name",
    "bowler_id",
    "bowler_name",
    "runs",
    "extras_type",
    "extras1_runs",
    "extras_2_runs",
    "is_wicket",
    "dismissal_type",
    "dismissed_player_id",
]

missing_rows = []

for col in important_columns:
    if col in balls_t20i.columns:
        missing_rows.append({
            "column": col,
            "missing_count": int(balls_t20i[col].isna().sum()),
            "missing_percent": round(
                balls_t20i[col].isna().mean() * 100, 4
            ),
        })

missing_df = pd.DataFrame(missing_rows)

print(missing_df.to_string(index=False))

missing_df.to_csv(
    REPORTS / "t20i_source_missing_values.csv",
    index=False
)


# ---------------------------------------------------------
# 8. EXTRAS AUDIT
# ---------------------------------------------------------

section("7. EXTRAS AUDIT")

extras = (
    balls_t20i["extras_type"]
    .fillna("None")
    .astype(str)
    .str.strip()
    .str.lower()
)

balls_t20i["extras_clean_audit"] = extras

extras_summary = balls_t20i.groupby(
    "extras_clean_audit",
    dropna=False
).agg(
    records=("match_id", "size"),
    batter_runs=("runs", "sum"),
    extras1_runs=("extras1_runs", "sum"),
    extras2_runs=("extras_2_runs", "sum"),
).reset_index()

print(extras_summary.to_string(index=False))

extras_summary.to_csv(
    REPORTS / "t20i_source_extras_summary.csv",
    index=False
)


# ---------------------------------------------------------
# 9. DISMISSAL AUDIT
# ---------------------------------------------------------

section("8. DISMISSAL AUDIT")

wickets = balls_t20i[
    balls_t20i["is_wicket"].astype(str).str.lower().isin(
        ["true", "1", "1.0"]
    )
].copy()

dismissal_summary = (
    wickets["dismissal_type"]
    .fillna("Missing")
    .astype(str)
    .value_counts(dropna=False)
    .rename_axis("dismissal_type")
    .reset_index(name="records")
)

print("Total wicket records:", len(wickets))
print(dismissal_summary.to_string(index=False))

print("\nMissing dismissed player IDs:",
      wickets["dismissed_player_id"].isna().sum())

print("Missing bowler IDs:",
      wickets["bowler_id"].isna().sum())

dismissal_summary.to_csv(
    REPORTS / "t20i_source_dismissal_summary.csv",
    index=False
)


# ---------------------------------------------------------
# 10. INNINGS ABOVE TWO
# ---------------------------------------------------------

section("9. EXTRA INNINGS AUDIT")

balls_t20i["innings_numeric"] = pd.to_numeric(
    balls_t20i["innings"], errors="coerce"
)

extra_innings = balls_t20i[
    balls_t20i["innings_numeric"] > 2
].copy()

print("Delivery rows in innings above 2:", len(extra_innings))

if len(extra_innings):
    print(
        extra_innings.groupby(
            ["match_id", "innings_numeric"]
        ).size().to_string()
    )

extra_innings.to_csv(
    REPORTS / "t20i_source_extra_innings.csv",
    index=False
)


# ---------------------------------------------------------
# 11. RUN RECONCILIATION
# ---------------------------------------------------------

section("10. RUN RECONCILIATION")

for col in ["runs", "extras1_runs", "extras_2_runs"]:
    balls_t20i[col] = pd.to_numeric(
        balls_t20i[col], errors="coerce"
    )

balls_t20i["reconstructed_runs"] = (
    balls_t20i["runs"]
    + balls_t20i["extras1_runs"]
    + balls_t20i["extras_2_runs"]
)

print("Total batter runs:", balls_t20i["runs"].sum())
print("Total extras 1:", balls_t20i["extras1_runs"].sum())
print("Total extras 2:", balls_t20i["extras_2_runs"].sum())
print("Total reconstructed runs:",
      balls_t20i["reconstructed_runs"].sum())

print("Missing reconstructed run rows:",
      balls_t20i["reconstructed_runs"].isna().sum())


# ---------------------------------------------------------
# 12. FINAL SUMMARY
# ---------------------------------------------------------

section("11. FINAL AUDIT SUMMARY")

summary = {
    "source_delivery_rows": int(len(balls)),
    "t20i_delivery_rows": int(len(balls_t20i)),
    "t20i_matches": int(matches_t20i["match_id"].nunique()),
    "t20i_competitions": int(t20i_competitions["comp_id"].nunique()),
    "unique_batters": int(balls_t20i["striker_id"].nunique()),
    "unique_bowlers": int(balls_t20i["bowler_id"].nunique()),
    "duplicate_delivery_rows": int(len(duplicates)),
    "unmatched_delivery_rows": int(len(unmatched_delivery_rows)),
    "wicket_records": int(len(wickets)),
    "innings_above_two_rows": int(len(extra_innings)),
    "total_reconstructed_runs": int(
        balls_t20i["reconstructed_runs"].sum()
    ),
    "date_start": str(matches_t20i["match_date"].min()),
    "date_end": str(matches_t20i["match_date"].max()),
}

print(json.dumps(summary, indent=4))

with open(
    REPORTS / "t20i_source_audit_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)

print("\nReports saved inside:", REPORTS)
print("STEP 44 COMPLETED.")
