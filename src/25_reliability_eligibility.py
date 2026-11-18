
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

BATTER_FILE = REPORTS / "batter_match_consistency.csv"
BOWLER_FILE = REPORTS / "bowler_match_consistency.csv"

print("Loading Script 24 outputs...")

bat = pd.read_csv(BATTER_FILE)
bowl = pd.read_csv(BOWLER_FILE)

# ------------------------------------------------------------
# BATTER ELIGIBILITY
# ------------------------------------------------------------

# Minimum requirements for initial candidate screening.
# These are screening thresholds, not claims of statistical certainty.

bat["eligible_matches"] = bat["pressure_matches"] >= 8
bat["eligible_balls"] = bat["pressure_balls"] >= 100
bat["eligible_baseline"] = bat["normal_matches"] >= 8

bat["eligible"] = (
    bat["eligible_matches"]
    & bat["eligible_balls"]
    & bat["eligible_baseline"]
)

bat["sample_status"] = np.select(
    [
        bat["eligible"],
        bat["pressure_matches"] < 5,
        bat["pressure_balls"] < 60
    ],
    [
        "Eligible for ranking review",
        "Insufficient pressure matches",
        "Insufficient pressure balls"
    ],
    default="Needs further review"
)

bat = bat.sort_values(
    [
        "eligible",
        "consistency_percentage",
        "pressure_matches",
        "pressure_balls"
    ],
    ascending=[False, False, False, False]
)

# ------------------------------------------------------------
# BOWLER ELIGIBILITY
# ------------------------------------------------------------

bowl["eligible_matches"] = bowl["pressure_matches"] >= 8
bowl["eligible_balls"] = bowl["pressure_legal_balls"] >= 120
bowl["eligible_baseline"] = bowl["normal_matches"] >= 8

bowl["eligible"] = (
    bowl["eligible_matches"]
    & bowl["eligible_balls"]
    & bowl["eligible_baseline"]
)

bowl["sample_status"] = np.select(
    [
        bowl["eligible"],
        bowl["pressure_matches"] < 5,
        bowl["pressure_legal_balls"] < 60
    ],
    [
        "Eligible for ranking review",
        "Insufficient pressure matches",
        "Insufficient pressure legal balls"
    ],
    default="Needs further review"
)

bowl = bowl.sort_values(
    [
        "eligible",
        "consistency_percentage",
        "pressure_matches",
        "pressure_legal_balls"
    ],
    ascending=[False, False, False, False]
)

# ------------------------------------------------------------
# SAVE
# ------------------------------------------------------------

bat.to_csv(
    REPORTS / "batter_reliability_eligibility.csv",
    index=False
)

bowl.to_csv(
    REPORTS / "bowler_reliability_eligibility.csv",
    index=False
)

# ------------------------------------------------------------
# DISPLAY
# ------------------------------------------------------------

print("\n" + "=" * 90)
print("BATTER ELIGIBILITY SUMMARY")
print("=" * 90)

print("Total batters:", len(bat))
print("Eligible batters:", int(bat["eligible"].sum()))
print("Not eligible:", int((~bat["eligible"]).sum()))

print("\nTOP 20 ELIGIBLE BATTERS")
print(
    bat[bat["eligible"]][
        [
            "striker_name",
            "pressure_matches",
            "pressure_runs",
            "pressure_balls",
            "normal_strike_rate",
            "consistency_percentage",
            "average_sr_difference"
        ]
    ].head(20).to_string(index=False)
)

print("\n" + "=" * 90)
print("BOWLER ELIGIBILITY SUMMARY")
print("=" * 90)

print("Total bowlers:", len(bowl))
print("Eligible bowlers:", int(bowl["eligible"].sum()))
print("Not eligible:", int((~bowl["eligible"]).sum()))

print("\nTOP 20 ELIGIBLE BOWLERS")
print(
    bowl[bowl["eligible"]][
        [
            "bowler_name",
            "pressure_matches",
            "pressure_wickets",
            "pressure_legal_balls",
            "normal_economy",
            "consistency_percentage",
            "average_economy_difference"
        ]
    ].head(20).to_string(index=False)
)

print("\nOUTPUT FILES")
print(REPORTS / "batter_reliability_eligibility.csv")
print(REPORTS / "bowler_reliability_eligibility.csv")

print("\nSCRIPT 25 COMPLETED")
