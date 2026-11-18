
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

print("=" * 70)
print("BATTER RANKING INTEGRITY AUDIT")
print("=" * 70)

ratings = pd.read_csv(
    REPORTS / "batter_reliability_ratings.csv"
)

dismissals = pd.read_csv(
    REPORTS / "batter_corrected_dismissal_analysis.csv"
)

events = pd.read_csv(
    REPORTS / "batter_identified_dismissal_events.csv"
)

# --------------------------------------------------
# 1. AUDIT TOP 10 BATTERS
# --------------------------------------------------

print("\nTOP 10 BATTER METRIC VALIDATION")

top10 = ratings.sort_values("final_rank").head(10)

columns = [
    "final_rank",
    "striker_id",
    "striker_name",
    "qualifying_matches",
    "consistency_pressure_balls",
    "pressure_runs",
    "pressure_strike_rate",
    "strike_rate_normal",
    "strike_rate_difference",
    "pressure_dismissals",
    "normal_dismissals",
    "pressure_dismissals_per_100_balls",
    "normal_dismissals_per_100_balls",
    "dismissal_rate_difference_y",
    "consistency_percentage",
    "rating_primary"
]

available = [c for c in columns if c in top10.columns]

print(top10[available].to_string(index=False))


# --------------------------------------------------
# 2. RASHID KHAN DEEP AUDIT
# --------------------------------------------------

print("\n" + "=" * 70)
print("RASHID KHAN DISMISSAL AUDIT")
print("=" * 70)

rashid = dismissals[
    dismissals["striker_name"].astype(str).str.contains(
        "Rashid Khan",
        case=False,
        na=False
    )
]

if rashid.empty:
    print("Rashid Khan not found in dismissal report.")
else:
    print("\nCorrected dismissal report:")
    print(rashid.to_string(index=False))

    rashid_ids = rashid["striker_id_clean"].dropna().unique()

    rashid_events = events[
        events["dismissed_player_id"].isin(rashid_ids)
    ]

    print("\nIdentified dismissal events:")
    print("Total:", len(rashid_events))

    if "is_pressure_delivery" in rashid_events.columns:
        print(
            "\nPressure classification:"
        )
        print(
            rashid_events["is_pressure_delivery"]
            .value_counts(dropna=False)
            .to_string()
        )

    if "dismissal_type" in rashid_events.columns:
        print("\nDismissal types:")
        print(
            rashid_events["dismissal_type"]
            .value_counts(dropna=False)
            .to_string()
        )


# --------------------------------------------------
# 3. CHECK NAME AND ID CONSISTENCY
# --------------------------------------------------

print("\n" + "=" * 70)
print("PLAYER ID AND NAME CONSISTENCY")
print("=" * 70)

name_check = (
    ratings.groupby("striker_id")["striker_name"]
    .nunique()
    .reset_index(name="unique_names")
)

name_issues = name_check[name_check["unique_names"] > 1]

print("Players with multiple names:", len(name_issues))

if not name_issues.empty:
    print(name_issues.to_string(index=False))


# --------------------------------------------------
# 4. CHECK MISSING OR INVALID METRICS
# --------------------------------------------------

print("\n" + "=" * 70)
print("METRIC QUALITY CHECK")
print("=" * 70)

check_columns = [
    "strike_rate_difference",
    "dismissal_rate_difference_y",
    "consistency_percentage",
    "rating_primary"
]

for col in check_columns:
    if col in ratings.columns:
        print(
            f"{col}: "
            f"missing={ratings[col].isna().sum()}, "
            f"infinite={pd.Series(ratings[col]).isin([float('inf'), float('-inf')]).sum()}"
        )

print("\nAudit complete.")
