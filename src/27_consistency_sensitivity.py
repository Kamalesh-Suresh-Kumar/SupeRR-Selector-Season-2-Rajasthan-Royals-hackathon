
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

BATTER_FILE = REPORTS / "batter_leave_one_out_match_details.csv"
BOWLER_FILE = REPORTS / "bowler_leave_one_out_match_details.csv"

print("Loading leave-one-match-out match details...")

bat = pd.read_csv(BATTER_FILE)
bowl = pd.read_csv(BOWLER_FILE)

# Only use matches where a valid independent baseline exists.
bat = bat[bat["valid_comparison"] == True].copy()
bowl = bowl[bowl["valid_comparison"] == True].copy()

# ============================================================
# BATTER SENSITIVITY
# ============================================================

def batter_summary(data, minimum_balls):
    d = data[data["pressure_balls"] >= minimum_balls].copy()

    result = (
        d.groupby(["striker_id", "striker_name"])
        .agg(
            qualifying_matches=("match_id", "nunique"),
            pressure_runs=("pressure_runs", "sum"),
            pressure_balls=("pressure_balls", "sum"),
            matches_above_baseline=("outperformed_baseline", "sum"),
            average_sr_difference=("sr_difference", "mean")
        )
        .reset_index()
    )

    result["consistency_percentage"] = (
        result["matches_above_baseline"]
        / result["qualifying_matches"] * 100
    )

    result["pressure_strike_rate"] = (
        result["pressure_runs"] * 100 / result["pressure_balls"]
    )

    result["minimum_match_balls"] = minimum_balls

    return result


bat_6 = batter_summary(bat, 6)
bat_12 = batter_summary(bat, 12)

# ============================================================
# BOWLER SENSITIVITY
# ============================================================

def bowler_summary(data, minimum_balls):
    d = data[data["pressure_balls"] >= minimum_balls].copy()

    result = (
        d.groupby(["bowler_id", "bowler_name"])
        .agg(
            qualifying_matches=("match_id", "nunique"),
            pressure_runs_conceded=("pressure_runs", "sum"),
            pressure_legal_balls=("pressure_balls", "sum"),
            pressure_wickets=("pressure_wickets", "sum"),
            matches_better_than_baseline=("outperformed_baseline", "sum"),
            average_economy_difference=("economy_difference", "mean")
        )
        .reset_index()
    )

    result["consistency_percentage"] = (
        result["matches_better_than_baseline"]
        / result["qualifying_matches"] * 100
    )

    result["pressure_economy"] = (
        result["pressure_runs_conceded"] * 6
        / result["pressure_legal_balls"]
    )

    result["minimum_match_balls"] = minimum_balls

    return result


bowl_6 = bowler_summary(bowl, 6)
bowl_12 = bowler_summary(bowl, 12)

# ============================================================
# APPLY OVERALL ELIGIBILITY REQUIREMENTS
# ============================================================

for d in [bat_6, bat_12]:
    d["eligible"] = (
        (d["qualifying_matches"] >= 8)
        & (d["pressure_balls"] >= 100)
    )

for d in [bowl_6, bowl_12]:
    d["eligible"] = (
        (d["qualifying_matches"] >= 8)
        & (d["pressure_legal_balls"] >= 120)
    )

# ============================================================
# SAVE
# ============================================================

bat_6.to_csv(
    REPORTS / "batter_consistency_min6.csv",
    index=False
)

bat_12.to_csv(
    REPORTS / "batter_consistency_min12.csv",
    index=False
)

bowl_6.to_csv(
    REPORTS / "bowler_consistency_min6.csv",
    index=False
)

bowl_12.to_csv(
    REPORTS / "bowler_consistency_min12.csv",
    index=False
)

# ============================================================
# DISPLAY
# ============================================================

print("\n" + "=" * 100)
print("BATTER CONSISTENCY SENSITIVITY")
print("=" * 100)

for label, data in [("MINIMUM 6 BALLS", bat_6), ("MINIMUM 12 BALLS", bat_12)]:
    print(f"\n{label}")
    print("Eligible:", int(data["eligible"].sum()))

    print(
        data[data["eligible"]][
            [
                "striker_name",
                "qualifying_matches",
                "pressure_runs",
                "pressure_balls",
                "consistency_percentage",
                "average_sr_difference"
            ]
        ]
        .sort_values(
            ["consistency_percentage", "pressure_runs"],
            ascending=[False, False]
        )
        .head(15)
        .to_string(index=False)
    )

print("\n" + "=" * 100)
print("BOWLER CONSISTENCY SENSITIVITY")
print("=" * 100)

for label, data in [("MINIMUM 6 BALLS", bowl_6), ("MINIMUM 12 BALLS", bowl_12)]:
    print(f"\n{label}")
    print("Eligible:", int(data["eligible"].sum()))

    print(
        data[data["eligible"]][
            [
                "bowler_name",
                "qualifying_matches",
                "pressure_wickets",
                "pressure_legal_balls",
                "consistency_percentage",
                "average_economy_difference"
            ]
        ]
        .sort_values(
            ["consistency_percentage", "pressure_wickets"],
            ascending=[False, False]
        )
        .head(15)
        .to_string(index=False)
    )

print("\nOUTPUT FILES")
print("batter_consistency_min6.csv")
print("batter_consistency_min12.csv")
print("bowler_consistency_min6.csv")
print("bowler_consistency_min12.csv")

print("\nSCRIPT 27 COMPLETED")
