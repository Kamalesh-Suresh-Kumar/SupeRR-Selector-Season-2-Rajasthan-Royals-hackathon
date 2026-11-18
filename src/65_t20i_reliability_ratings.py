
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# STEP 65: T20I RELIABILITY RATINGS
# ============================================================

REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)

BATTER_FILE = REPORTS / "t20i_batter_corrected_exposure_audit.csv"
BOWLER_FILE = REPORTS / "t20i_bowler_corrected_exposure_audit.csv"

BATTER_ELIGIBILITY_FILE = REPORTS / "t20i_batter_eligibility_sensitivity.csv"
BOWLER_ELIGIBILITY_FILE = REPORTS / "t20i_bowler_eligibility_sensitivity.csv"

BATTER_CONSISTENCY_FILE = REPORTS / "t20i_batter_pressure_consistency.csv"
BOWLER_CONSISTENCY_FILE = REPORTS / "t20i_bowler_pressure_consistency.csv"


print("\n" + "=" * 80)
print("STEP 65: T20I RELIABILITY RATINGS")
print("=" * 80)


# ============================================================
# 1. LOAD DATA
# ============================================================

batters = pd.read_csv(BATTER_FILE)
bowlers = pd.read_csv(BOWLER_FILE)

batter_eligibility = pd.read_csv(BATTER_ELIGIBILITY_FILE)
bowler_eligibility = pd.read_csv(BOWLER_ELIGIBILITY_FILE)

batter_consistency = pd.read_csv(BATTER_CONSISTENCY_FILE)
bowler_consistency = pd.read_csv(BOWLER_CONSISTENCY_FILE)

print("Batter exposure records:", len(batters))
print("Bowler exposure records:", len(bowlers))


# ============================================================
# 2. VALIDATE INPUTS
# ============================================================

required_batter = [
    "striker_id",
    "striker_name",
    "matches_pressure",
    "balls_pressure",
    "balls_normal",
    "strike_rate_pressure",
    "strike_rate_normal",
    "dismissal_rate_pressure",
    "dismissal_rate_normal"
]

required_bowler = [
    "bowler_id",
    "bowler_name",
    "matches_pressure",
    "legal_balls_pressure",
    "legal_balls_normal",
    "economy_pressure",
    "economy_normal",
    "wickets_pressure"
]

required_batter_consistency = [
    "striker_id",
    "consistency_pct"
]

required_bowler_consistency = [
    "bowler_id",
    "consistency_pct"
]

for name, data, required in [
    ("Batter exposure", batters, required_batter),
    ("Bowler exposure", bowlers, required_bowler),
    ("Batter consistency", batter_consistency,
     required_batter_consistency),
    ("Bowler consistency", bowler_consistency,
     required_bowler_consistency)
]:
    missing = [c for c in required if c not in data.columns]

    if missing:
        raise ValueError(
            f"{name} missing columns: {missing}"
        )

if "primary_eligible" not in batter_eligibility.columns:
    raise ValueError("Batter primary eligibility column missing.")

if "primary_eligible" not in bowler_eligibility.columns:
    raise ValueError("Bowler primary eligibility column missing.")


# ============================================================
# 3. PREPARE PRIMARY ELIGIBLE PLAYERS
# ============================================================

batters["striker_id"] = pd.to_numeric(
    batters["striker_id"], errors="coerce"
)

bowlers["bowler_id"] = pd.to_numeric(
    bowlers["bowler_id"], errors="coerce"
)

batter_consistency["striker_id"] = pd.to_numeric(
    batter_consistency["striker_id"], errors="coerce"
)

bowler_consistency["bowler_id"] = pd.to_numeric(
    bowler_consistency["bowler_id"], errors="coerce"
)

batter_eligibility["striker_id"] = pd.to_numeric(
    batter_eligibility["striker_id"], errors="coerce"
)

bowler_eligibility["bowler_id"] = pd.to_numeric(
    bowler_eligibility["bowler_id"], errors="coerce"
)

batters = batters.merge(
    batter_eligibility[
        ["striker_id", "primary_eligible"]
    ],
    on="striker_id",
    how="left",
    validate="one_to_one"
)

bowlers = bowlers.merge(
    bowler_eligibility[
        ["bowler_id", "primary_eligible"]
    ],
    on="bowler_id",
    how="left",
    validate="one_to_one"
)

batters = batters[
    batters["primary_eligible"].fillna(False)
].copy()

bowlers = bowlers[
    bowlers["primary_eligible"].fillna(False)
].copy()

print("Primary eligible batters:", len(batters))
print("Primary eligible bowlers:", len(bowlers))


# ============================================================
# 4. MERGE CONSISTENCY METRICS
# ============================================================

if batter_consistency["striker_id"].duplicated().any():
    raise ValueError("Duplicate batter IDs in consistency file.")

if bowler_consistency["bowler_id"].duplicated().any():
    raise ValueError("Duplicate bowler IDs in consistency file.")

batters = batters.merge(
    batter_consistency[
        ["striker_id", "consistency_pct"]
    ],
    on="striker_id",
    how="left",
    validate="one_to_one"
)

bowlers = bowlers.merge(
    bowler_consistency[
        ["bowler_id", "consistency_pct"]
    ],
    on="bowler_id",
    how="left",
    validate="one_to_one"
)

missing_batter_consistency = int(
    batters["consistency_pct"].isna().sum()
)

missing_bowler_consistency = int(
    bowlers["consistency_pct"].isna().sum()
)

print("Missing batter consistency:", missing_batter_consistency)
print("Missing bowler consistency:", missing_bowler_consistency)

if missing_batter_consistency > 0:
    raise ValueError(
        "Some eligible batters have no consistency measurement."
    )

if missing_bowler_consistency > 0:
    raise ValueError(
        "Some eligible bowlers have no consistency measurement."
    )


# ============================================================
# 5. CALCULATE BATTER PERFORMANCE COMPONENTS
# ============================================================

batters["strike_rate_improvement"] = (
    batters["strike_rate_pressure"]
    - batters["strike_rate_normal"]
)

batters["dismissal_rate_improvement"] = (
    batters["dismissal_rate_normal"]
    - batters["dismissal_rate_pressure"]
)

# Higher is better for both improvement metrics.

batters["sample_match_score"] = (
    batters["matches_pressure"] / 20
).clip(upper=1) * 100

batters["sample_ball_score"] = (
    batters["balls_pressure"] / 300
).clip(upper=1) * 100

batters["sample_score"] = (
    0.60 * batters["sample_match_score"]
    + 0.40 * batters["sample_ball_score"]
)


# ============================================================
# 6. CALCULATE BOWLER PERFORMANCE COMPONENTS
# ============================================================

bowlers["economy_improvement"] = (
    bowlers["economy_normal"]
    - bowlers["economy_pressure"]
)

bowlers["pressure_wickets_per_100_balls"] = (
    bowlers["wickets_pressure"] * 100
    / bowlers["legal_balls_pressure"]
)

bowlers["sample_match_score"] = (
    bowlers["matches_pressure"] / 20
).clip(upper=1) * 100

bowlers["sample_ball_score"] = (
    bowlers["legal_balls_pressure"] / 300
).clip(upper=1) * 100

bowlers["sample_score"] = (
    0.60 * bowlers["sample_match_score"]
    + 0.40 * bowlers["sample_ball_score"]
)


# ============================================================
# 7. PERCENTILE RANKING
# ============================================================

# Percentiles are calculated within the eligible T20I
# population, separately for batters and bowlers.

def percentile_score(series, higher_is_better=True):

    values = pd.to_numeric(series, errors="coerce")

    if values.isna().any():
        raise ValueError(
            "Missing values found in a scoring component."
        )

    if higher_is_better:
        return values.rank(method="average", pct=True) * 100

    return (
        values.rank(method="average", pct=True, ascending=False)
        * 100
    )


# Batter percentile components.

batters["strike_rate_score"] = percentile_score(
    batters["strike_rate_improvement"],
    higher_is_better=True
)

batters["dismissal_improvement_score"] = percentile_score(
    batters["dismissal_rate_improvement"],
    higher_is_better=True
)

batters["consistency_score"] = percentile_score(
    batters["consistency_pct"],
    higher_is_better=True
)

batters["sample_percentile_score"] = percentile_score(
    batters["sample_score"],
    higher_is_better=True
)


# Bowler percentile components.

bowlers["economy_score"] = percentile_score(
    bowlers["economy_improvement"],
    higher_is_better=True
)

bowlers["pressure_wicket_score"] = percentile_score(
    bowlers["pressure_wickets_per_100_balls"],
    higher_is_better=True
)

bowlers["consistency_score"] = percentile_score(
    bowlers["consistency_pct"],
    higher_is_better=True
)

bowlers["sample_percentile_score"] = percentile_score(
    bowlers["sample_score"],
    higher_is_better=True
)


# ============================================================
# 8. CALCULATE PRIMARY RELIABILITY RATINGS
# ============================================================

# Same weight structure as the IPL reliability framework.

BATTER_WEIGHTS = {
    "strike_rate_score": 0.30,
    "dismissal_improvement_score": 0.25,
    "consistency_score": 0.30,
    "sample_percentile_score": 0.15
}

BOWLER_WEIGHTS = {
    "economy_score": 0.30,
    "pressure_wicket_score": 0.25,
    "consistency_score": 0.30,
    "sample_percentile_score": 0.15
}

batters["reliability_rating"] = sum(
    batters[column] * weight
    for column, weight in BATTER_WEIGHTS.items()
)

bowlers["reliability_rating"] = sum(
    bowlers[column] * weight
    for column, weight in BOWLER_WEIGHTS.items()
)


# ============================================================
# 9. ALTERNATIVE WEIGHT SCENARIOS
# ============================================================

SCENARIOS = {
    "primary": {
        "performance": 0.30,
        "secondary": 0.25,
        "consistency": 0.30,
        "sample": 0.15
    },
    "performance_heavy": {
        "performance": 0.35,
        "secondary": 0.20,
        "consistency": 0.30,
        "sample": 0.15
    },
    "consistency_heavy": {
        "performance": 0.25,
        "secondary": 0.20,
        "consistency": 0.40,
        "sample": 0.15
    },
    "sample_conservative": {
        "performance": 0.30,
        "secondary": 0.25,
        "consistency": 0.25,
        "sample": 0.20
    }
}

for scenario, weights in SCENARIOS.items():

    batters[f"rating_{scenario}"] = (
        weights["performance"] * batters["strike_rate_score"]
        + weights["secondary"] * batters["dismissal_improvement_score"]
        + weights["consistency"] * batters["consistency_score"]
        + weights["sample"] * batters["sample_percentile_score"]
    )

    bowlers[f"rating_{scenario}"] = (
        weights["performance"] * bowlers["economy_score"]
        + weights["secondary"] * bowlers["pressure_wicket_score"]
        + weights["consistency"] * bowlers["consistency_score"]
        + weights["sample"] * bowlers["sample_percentile_score"]
    )


# ============================================================
# 10. GENERATE RANKINGS
# ============================================================

batters = batters.sort_values(
    ["reliability_rating", "matches_pressure"],
    ascending=[False, False]
).reset_index(drop=True)

bowlers = bowlers.sort_values(
    ["reliability_rating", "matches_pressure"],
    ascending=[False, False]
).reset_index(drop=True)

batters["t20i_rank"] = np.arange(1, len(batters) + 1)
bowlers["t20i_rank"] = np.arange(1, len(bowlers) + 1)

batters["reliability_rating"] = (
    batters["reliability_rating"].round(4)
)

bowlers["reliability_rating"] = (
    bowlers["reliability_rating"].round(4)
)


# ============================================================
# 11. SAVE COMPLETE RATING DATASETS
# ============================================================

batters.to_csv(
    REPORTS / "t20i_batter_reliability_ratings.csv",
    index=False
)

bowlers.to_csv(
    REPORTS / "t20i_bowler_reliability_ratings.csv",
    index=False
)

batters.head(10).to_csv(
    REPORTS / "t20i_batter_top10.csv",
    index=False
)

bowlers.head(10).to_csv(
    REPORTS / "t20i_bowler_top10.csv",
    index=False
)


# ============================================================
# 12. RANKING SENSITIVITY
# ============================================================

sensitivity_rows = []

for player_type, data, id_col in [
    ("Batter", batters, "striker_id"),
    ("Bowler", bowlers, "bowler_id")
]:

    primary_top10 = set(
        data.nlargest(10, "rating_primary")[id_col]
    )

    for scenario in [
        "performance_heavy",
        "consistency_heavy",
        "sample_conservative"
    ]:

        alternative_top10 = set(
            data.nlargest(10, f"rating_{scenario}")[id_col]
        )

        common = primary_top10 & alternative_top10

        sensitivity_rows.append({
            "player_type": player_type,
            "scenario": scenario,
            "primary_top10_count": len(primary_top10),
            "alternative_top10_count": len(alternative_top10),
            "common_top10_players": len(common),
            "top10_overlap_pct": round(
                len(common) / 10 * 100, 2
            )
        })

sensitivity = pd.DataFrame(sensitivity_rows)

sensitivity.to_csv(
    REPORTS / "t20i_reliability_ranking_sensitivity.csv",
    index=False
)


# ============================================================
# 13. PRINT TOP 15 BATTERS
# ============================================================

print("\n" + "=" * 80)
print("TOP 15 T20I BATTERS")
print("=" * 80)

print(
    batters[
        [
            "t20i_rank",
            "striker_name",
            "runs_pressure",
            "balls_pressure",
            "matches_pressure",
            "strike_rate_pressure",
            "strike_rate_normal",
            "strike_rate_improvement",
            "dismissal_rate_improvement",
            "consistency_pct",
            "reliability_rating"
        ]
    ].head(15).round(2).to_string(index=False)
)


# ============================================================
# 14. PRINT TOP 15 BOWLERS
# ============================================================

print("\n" + "=" * 80)
print("TOP 15 T20I BOWLERS")
print("=" * 80)

print(
    bowlers[
        [
            "t20i_rank",
            "bowler_name",
            "wickets_pressure",
            "legal_balls_pressure",
            "matches_pressure",
            "economy_pressure",
            "economy_normal",
            "economy_improvement",
            "pressure_wickets_per_100_balls",
            "consistency_pct",
            "reliability_rating"
        ]
    ].head(15).round(2).to_string(index=False)
)


# ============================================================
# 15. PRINT SENSITIVITY RESULTS
# ============================================================

print("\n" + "=" * 80)
print("RANKING SENSITIVITY")
print("=" * 80)

print(sensitivity.to_string(index=False))


# ============================================================
# 16. COMPLETION
# ============================================================

print("\n" + "=" * 80)
print("STEP 65 COMPLETED")
print("=" * 80)

print("\nGenerated reports:")

for name in [
    "t20i_batter_reliability_ratings.csv",
    "t20i_bowler_reliability_ratings.csv",
    "t20i_batter_top10.csv",
    "t20i_bowler_top10.csv",
    "t20i_reliability_ranking_sensitivity.csv"
]:
    print(" -", REPORTS / name)

print("\nNote:")
print(
    "Ratings are percentile-based within the eligible T20I "
    "player population."
)
print(
    "They are not directly comparable as absolute scores "
    "against IPL ratings."
)
