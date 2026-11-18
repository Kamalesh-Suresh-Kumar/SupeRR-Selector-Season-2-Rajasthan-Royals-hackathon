
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"

REPORTS.mkdir(exist_ok=True)

MATCH_FILE = RAW / "matches.csv"
COMP_FILE = RAW / "competitions.csv"
BALL_FILE = RAW / "ball_by_ball.csv"

print("=" * 75)
print("T20I BALL-BY-BALL DATA AUDIT")
print("=" * 75)

# --------------------------------------------------
# 1. LOAD MATCH AND COMPETITION METADATA
# --------------------------------------------------

print("\nLoading match and competition metadata...")

matches = pd.read_csv(MATCH_FILE, low_memory=False)
competitions = pd.read_csv(COMP_FILE, low_memory=False)

competitions["match_format"] = (
    competitions["match_format"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.upper()
)

# Only T20I competitions from 2022 onwards
t20i_competitions = competitions[
    competitions["match_format"] == "T20I"
].copy()

t20i_matches = matches.merge(
    t20i_competitions[
        ["comp_id", "comp_name", "match_format", "season"]
    ],
    on="comp_id",
    how="inner",
    validate="many_to_one"
)

t20i_matches["match_date"] = pd.to_datetime(
    t20i_matches["match_date"],
    errors="coerce"
)

t20i_matches = t20i_matches[
    t20i_matches["match_date"].dt.year >= 2022
].copy()

t20i_ids = set(t20i_matches["match_id"].dropna())

print("\nT20I competitions:", len(t20i_competitions))
print("T20I matches from 2022 onwards:", len(t20i_matches))
print("Unique T20I match IDs:", len(t20i_ids))

print("\nT20I matches by season:")
print(
    t20i_matches["season"]
    .value_counts(dropna=False)
    .sort_index()
    .to_string()
)

print("\nT20I matches by year:")
print(
    t20i_matches["match_date"]
    .dt.year
    .value_counts()
    .sort_index()
    .to_string()
)

t20i_matches.to_csv(
    REPORTS / "t20i_match_list.csv",
    index=False
)

# --------------------------------------------------
# 2. INSPECT BALL-BY-BALL SCHEMA
# --------------------------------------------------

print("\n" + "=" * 75)
print("BALL-BY-BALL SOURCE SCHEMA")
print("=" * 75)

balls = pd.read_csv(BALL_FILE, low_memory=False)

print("\nBall-by-ball shape:", balls.shape)

print("\nColumns:")
for col in balls.columns:
    print(" -", col)

print("\nFirst 5 rows:")
print(balls.head().to_string(index=False))

if "match_id" not in balls.columns:
    raise ValueError(
        "match_id column is missing from ball_by_ball.csv"
    )

# --------------------------------------------------
# 3. MATCH COVERAGE
# --------------------------------------------------

print("\n" + "=" * 75)
print("T20I DELIVERY COVERAGE")
print("=" * 75)

balls["match_id"] = pd.to_numeric(
    balls["match_id"],
    errors="coerce"
)

t20i_balls = balls[
    balls["match_id"].isin(t20i_ids)
].copy()

covered_ids = set(t20i_balls["match_id"].dropna())

missing_ids = t20i_ids - covered_ids
extra_ids = covered_ids - t20i_ids

print("\nTotal source delivery records:", len(balls))
print("T20I delivery records:", len(t20i_balls))
print("T20I matches with delivery data:", len(covered_ids))
print("T20I matches without delivery data:", len(missing_ids))
print("Unexpected match IDs:", len(extra_ids))

if len(t20i_balls) > 0:

    print("\nDelivery records per match:")
    match_counts = (
        t20i_balls.groupby("match_id")
        .size()
        .describe()
    )
    print(match_counts.to_string())

    print("\nSample T20I delivery records:")
    print(t20i_balls.head(10).to_string(index=False))

# --------------------------------------------------
# 4. JOIN COVERAGE WITH MATCH METADATA
# --------------------------------------------------

coverage = (
    t20i_matches[
        ["match_id", "comp_id", "comp_name",
         "match_date", "season", "home_team",
         "away_team"]
    ]
    .merge(
        t20i_balls.groupby("match_id")
        .size()
        .rename("delivery_records")
        .reset_index(),
        on="match_id",
        how="left"
    )
)

coverage["delivery_records"] = (
    coverage["delivery_records"].fillna(0).astype(int)
)

coverage["has_delivery_data"] = (
    coverage["delivery_records"] > 0
)

coverage.to_csv(
    REPORTS / "t20i_delivery_coverage.csv",
    index=False
)

print("\nCoverage by season:")
print(
    coverage.groupby("season").agg(
        matches=("match_id", "nunique"),
        matches_with_deliveries=("has_delivery_data", "sum"),
        delivery_records=("delivery_records", "sum")
    ).to_string()
)

# --------------------------------------------------
# 5. CHECK IMPORTANT DELIVERY COLUMNS
# --------------------------------------------------

print("\n" + "=" * 75)
print("IMPORTANT COLUMN AVAILABILITY")
print("=" * 75)

expected_columns = [
    "match_id",
    "innings",
    "over",
    "ball",
    "batter",
    "bowler",
    "batsman_runs",
    "extra_runs",
    "total_runs",
    "extras_type",
    "player_dismissed",
    "dismissal_kind"
]

for col in expected_columns:
    print(
        f"{col}:",
        "AVAILABLE" if col in t20i_balls.columns else "NOT FOUND"
    )

# --------------------------------------------------
# 6. SAVE T20I DELIVERY DATA FOR LATER ANALYSIS
# --------------------------------------------------

if len(t20i_balls) > 0:

    output = REPORTS / "t20i_raw_deliveries.csv.gz"

    t20i_balls.to_csv(
        output,
        index=False,
        compression="gzip"
    )

    print("\nFiltered T20I deliveries saved:")
    print(output)

if missing_ids:
    pd.DataFrame(
        {"missing_match_id": sorted(missing_ids)}
    ).to_csv(
        REPORTS / "t20i_matches_missing_deliveries.csv",
        index=False
    )

print("\n" + "=" * 75)
print("T20I BALL DATA AUDIT COMPLETED")
print("=" * 75)
