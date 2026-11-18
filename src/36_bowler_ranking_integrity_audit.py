
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

print("=" * 70)
print("BOWLER RANKING INTEGRITY AUDIT")
print("=" * 70)

ratings = pd.read_csv(
    REPORTS / "bowler_reliability_ratings.csv"
)

print("\nTOP 10 BOWLERS")

columns = [
    "final_rank",
    "bowler_id",
    "bowler_name",
    "qualifying_matches",
    "pressure_legal_balls",
    "wickets_pressure",
    "wickets_normal",
    "economy_pressure",
    "economy_normal",
    "economy_difference",
    "pressure_wickets_per_100_balls",
    "consistency_percentage",
    "rating_primary"
]

available = [c for c in columns if c in ratings.columns]

print(
    ratings.sort_values("final_rank")
    .head(10)[available]
    .to_string(index=False)
)

print("\n" + "=" * 70)
print("BOWLER METRIC VALIDATION")
print("=" * 70)

# Validate wicket attribution and pressure wicket totals
# using the consolidated source dataset.

source = pd.read_csv(
    REPORTS.parent / "reports" / "unified_pressure_deliveries.csv.gz"
)

print("\nSource rows:", len(source))

if "is_wicket" in source.columns:
    print("Total wicket deliveries:", int(source["is_wicket"].sum()))

if "dismissal_type" in source.columns:
    print("\nDismissal types:")
    print(
        source.loc[source["is_wicket"] == 1, "dismissal_type"]
        .value_counts(dropna=False)
        .to_string()
    )

if "is_legal_ball" in source.columns:
    print("\nLegal-ball classification:")
    print(source["is_legal_ball"].value_counts(dropna=False))

if "is_pressure_delivery" in source.columns:
    print("\nLegacy pressure flag counts:")
    print(source["is_pressure_delivery"].value_counts(dropna=False))

print("\nAudit completed.")
