
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

print("Loading player analysis reports...")

# --------------------------------------------------
# LOAD REPORTS
# --------------------------------------------------

batter_base = pd.read_csv(REPORTS / "batter_pressure_vs_baseline.csv")
batter_consistency = pd.read_csv(REPORTS / "batter_consistency_min6.csv")
batter_dismissal = pd.read_csv(REPORTS / "batter_corrected_dismissal_analysis.csv")

bowler_base = pd.read_csv(REPORTS / "bowler_pressure_vs_baseline.csv")
bowler_consistency = pd.read_csv(REPORTS / "bowler_consistency_min6.csv")


# --------------------------------------------------
# BATTER METRIC CONSOLIDATION
# --------------------------------------------------

print("Consolidating batter metrics...")

batter_consistency_selected = batter_consistency[
    [
        "striker_id",
        "qualifying_matches",
        "pressure_runs",
        "pressure_balls",
        "matches_above_baseline",
        "average_sr_difference",
        "consistency_percentage",
        "pressure_strike_rate",
        "minimum_match_balls",
        "eligible"
    ]
].copy()

batter = batter_base.merge(
    batter_consistency_selected,
    on="striker_id",
    how="left",
    validate="one_to_one"
)

batter_dismissal_selected = batter_dismissal[
    [
        "striker_id_clean",
        "pressure_dismissals",
        "normal_dismissals",
        "pressure_dismissals_per_100_balls",
        "normal_dismissals_per_100_balls",
        "dismissal_rate_difference"
    ]
].copy()

batter = batter.merge(
    batter_dismissal_selected,
    left_on="striker_id",
    right_on="striker_id_clean",
    how="left",
    validate="one_to_one"
)

batter.drop(columns=["striker_id_clean"], inplace=True)

# Eligibility: minimum 8 qualifying pressure matches
# and at least 100 pressure balls.
batter["eligible_min6"] = (
    (batter["qualifying_matches"] >= 8)
    & (batter["pressure_balls_y"] >= 100)
)

# Explicitly preserve the consistency report's pressure-ball count.
# The base report already contains pressure_balls, so Pandas
# creates pressure_balls_x and pressure_balls_y during merging.
batter["consistency_pressure_balls"] = batter["pressure_balls_y"]

batter = batter.sort_values(
    ["eligible_min6", "consistency_percentage", "pressure_runs"],
    ascending=[False, False, False]
)

batter.to_csv(
    REPORTS / "batter_final_metric_dataset.csv",
    index=False
)


# --------------------------------------------------
# BOWLER METRIC CONSOLIDATION
# --------------------------------------------------

print("Consolidating bowler metrics...")

bowler_consistency_selected = bowler_consistency[
    [
        "bowler_id",
        "qualifying_matches",
        "pressure_runs_conceded",
        "pressure_legal_balls",
        "pressure_wickets",
        "matches_better_than_baseline",
        "average_economy_difference",
        "consistency_percentage",
        "pressure_economy",
        "minimum_match_balls",
        "eligible"
    ]
].copy()

bowler = bowler_base.merge(
    bowler_consistency_selected,
    on="bowler_id",
    how="left",
    validate="one_to_one"
)

bowler["eligible_min6"] = (
    (bowler["qualifying_matches"] >= 8)
    & (bowler["pressure_legal_balls"] >= 120)
)

bowler = bowler.sort_values(
    ["eligible_min6", "consistency_percentage", "pressure_wickets"],
    ascending=[False, False, False]
)

bowler.to_csv(
    REPORTS / "bowler_final_metric_dataset.csv",
    index=False
)


# --------------------------------------------------
# FINAL VALIDATION
# --------------------------------------------------

print("\n" + "=" * 65)
print("PLAYER METRIC CONSOLIDATION COMPLETE")
print("=" * 65)

print("\nBATTER SUMMARY")
print("Total batters:", len(batter))
print("Eligible batters:", int(batter["eligible_min6"].sum()))

print("\nTOP 15 ELIGIBLE BATTERS")

print(
    batter.loc[
        batter["eligible_min6"],
        [
            "striker_name",
            "qualifying_matches",
            "consistency_pressure_balls",
            "pressure_runs",
            "pressure_strike_rate",
            "strike_rate_normal",
            "consistency_percentage",
            "pressure_dismissals_per_100_balls",
            "normal_dismissals_per_100_balls"
        ]
    ].head(15).to_string(index=False)
)

print("\nBOWLER SUMMARY")
print("Total bowlers:", len(bowler))
print("Eligible bowlers:", int(bowler["eligible_min6"].sum()))

print("\nTOP 15 ELIGIBLE BOWLERS")

print(
    bowler.loc[
        bowler["eligible_min6"],
        [
            "bowler_name",
            "qualifying_matches",
            "pressure_legal_balls",
            "pressure_wickets",
            "economy_pressure",
            "economy_normal",
            "consistency_percentage",
            "average_economy_difference"
        ]
    ].head(15).to_string(index=False)
)

print("\nSaved:")
print("reports/batter_final_metric_dataset.csv")
print("reports/bowler_final_metric_dataset.csv")
