
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"

MATCH_FILE = REPORTS / "t20i_match_list.csv"
BALL_FILE = REPORTS / "t20i_raw_deliveries.csv.gz"

print("=" * 75)
print("T20I MATCH COMPLETENESS AND DELIVERY STRUCTURE AUDIT")
print("=" * 75)

matches = pd.read_csv(MATCH_FILE, low_memory=False)
balls = pd.read_csv(BALL_FILE, low_memory=False)

balls["match_id"] = pd.to_numeric(balls["match_id"], errors="coerce")
balls["innings"] = pd.to_numeric(balls["innings"], errors="coerce")

# --------------------------------------------------
# 1. MATCH-LEVEL DELIVERY COVERAGE
# --------------------------------------------------

print("\n1. MATCH-LEVEL COVERAGE")

match_stats = (
    balls.groupby("match_id")
    .agg(
        delivery_records=("innings", "size"),
        innings_count=("innings", "nunique"),
        first_innings_records=("innings", lambda x: (x == 1).sum()),
        second_innings_records=("innings", lambda x: (x == 2).sum()),
        innings_values=("innings", lambda x: ",".join(
            sorted(x.dropna().astype(int).astype(str).unique())
        ))
    )
    .reset_index()
)

coverage = matches.merge(
    match_stats,
    on="match_id",
    how="left"
)

coverage["delivery_records"] = (
    coverage["delivery_records"].fillna(0).astype(int)
)

coverage["innings_count"] = (
    coverage["innings_count"].fillna(0).astype(int)
)

coverage["first_innings_records"] = (
    coverage["first_innings_records"].fillna(0).astype(int)
)

coverage["second_innings_records"] = (
    coverage["second_innings_records"].fillna(0).astype(int)
)

coverage["coverage_status"] = "HAS_DELIVERIES"

coverage.loc[
    coverage["delivery_records"] == 0,
    "coverage_status"
] = "NO_DELIVERIES"

coverage.loc[
    (coverage["delivery_records"] > 0) &
    (coverage["delivery_records"] < 100),
    "coverage_status"
] = "VERY_LOW_DELIVERY_COUNT_REVIEW"

coverage.loc[
    (coverage["delivery_records"] >= 100) &
    (coverage["innings_count"] < 2),
    "coverage_status"
] = "ONE_OR_FEWER_INNINGS_REVIEW"

print("\nCoverage status:")
print(coverage["coverage_status"].value_counts().to_string())

print("\nDelivery count summary:")
print(coverage["delivery_records"].describe().to_string())

print("\nMatches with zero deliveries:")
print(
    coverage.loc[
        coverage["delivery_records"] == 0,
        ["match_id", "match_date", "comp_name",
         "home_team", "away_team", "result"]
    ].to_string(index=False)
)

print("\nMatches with fewer than 100 deliveries:")
print(
    coverage.loc[
        (coverage["delivery_records"] > 0) &
        (coverage["delivery_records"] < 100),
        ["match_id", "match_date", "comp_name",
         "home_team", "away_team", "delivery_records",
         "innings_values", "result"]
    ].to_string(index=False)
)

coverage.to_csv(
    REPORTS / "t20i_match_completeness.csv",
    index=False
)

# --------------------------------------------------
# 2. INNINGS-LEVEL DELIVERY STRUCTURE
# --------------------------------------------------

print("\n" + "=" * 75)
print("2. INNINGS-LEVEL STRUCTURE")
print("=" * 75)

innings_stats = (
    balls.groupby(["match_id", "innings"])
    .agg(
        delivery_records=("overid", "size"),
        unique_over_ids=("overid", "nunique"),
        min_over_id=("overid", "min"),
        max_over_id=("overid", "max"),
        max_over_ball_num=("over_ball_num", "max"),
        max_innings_ball_num=("innings_ball_num", "max"),
        total_runs=("runs", "sum"),
        wicket_records=("is_wicket", "sum")
    )
    .reset_index()
)

print("\nInnings delivery count summary:")
print(
    innings_stats["delivery_records"]
    .describe()
    .to_string()
)

print("\nInnings with fewer than 30 delivery records:")
print(
    innings_stats.loc[
        innings_stats["delivery_records"] < 30
    ].to_string(index=False)
)

print("\nInnings with more than 267 delivery records:")
print(
    innings_stats.loc[
        innings_stats["delivery_records"] > 267
    ].to_string(index=False)
)

innings_stats.to_csv(
    REPORTS / "t20i_innings_structure.csv",
    index=False
)

# --------------------------------------------------
# 3. EXTRAS CLASSIFICATION
# --------------------------------------------------

print("\n" + "=" * 75)
print("3. EXTRAS CLASSIFICATION")
print("=" * 75)

balls["extras_clean"] = (
    balls["extras_type"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)

print("\nExtras values:")
print(
    balls["extras_clean"]
    .value_counts(dropna=False)
    .to_string()
)

extras_audit = (
    balls.groupby("extras_clean", dropna=False)
    .agg(
        delivery_records=("match_id", "size"),
        batter_runs=("runs", "sum"),
        extras1_runs=("extras1_runs", "sum"),
        extras2_runs=("extras_2_runs", "sum")
    )
    .reset_index()
)

extras_audit.to_csv(
    REPORTS / "t20i_extras_audit.csv",
    index=False
)

print("\nExtras audit:")
print(extras_audit.to_string(index=False))

# --------------------------------------------------
# 4. DISMISSAL CLASSIFICATION
# --------------------------------------------------

print("\n" + "=" * 75)
print("4. DISMISSAL CLASSIFICATION")
print("=" * 75)

balls["dismissal_clean"] = (
    balls["dismissal_type"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
    .str.replace(" ", "", regex=False)
)

print("\nDismissal values:")
print(
    balls.loc[
        balls["is_wicket"].astype(str).str.lower().isin(
            ["true", "1"]
        ),
        "dismissal_clean"
    ].value_counts(dropna=False).to_string()
)

print("\nWicket flag distribution:")
print(
    balls["is_wicket"]
    .value_counts(dropna=False)
    .to_string()
)

# --------------------------------------------------
# 5. OVER AND BALL NUMBERING
# --------------------------------------------------

print("\n" + "=" * 75)
print("5. OVER AND BALL NUMBERING")
print("=" * 75)

for col in ["overid", "over_ball_num", "innings_ball_num"]:

    print(f"\n{col} value summary:")
    print(balls[col].describe().to_string())

    print(f"\n{col} unique sample:")
    print(
        sorted(balls[col].dropna().unique().tolist())[:30]
    )

# Check duplicate delivery identifiers
duplicate_columns = [
    "match_id",
    "innings",
    "overid",
    "over_ball_num"
]

duplicate_count = balls.duplicated(
    subset=duplicate_columns,
    keep=False
).sum()

print("\nDuplicate delivery identifier rows:", duplicate_count)

# --------------------------------------------------
# 6. SAVE MATCH-LEVEL FLAGS
# --------------------------------------------------

print("\n" + "=" * 75)
print("6. AUDIT SUMMARY")
print("=" * 75)

print("T20I matches:", len(matches))
print("Matches with delivery records:", len(match_stats))
print("Matches with no delivery records:", (
    coverage["delivery_records"] == 0
).sum())
print("Matches with fewer than 100 records:", (
    (coverage["delivery_records"] > 0) &
    (coverage["delivery_records"] < 100)
).sum())
print("Innings records:", len(innings_stats))
print("Duplicate delivery identifier rows:", duplicate_count)

print("\nSaved:")
print(" - reports/t20i_match_completeness.csv")
print(" - reports/t20i_innings_structure.csv")
print(" - reports/t20i_extras_audit.csv")

print("\nT20I completeness audit completed.")
