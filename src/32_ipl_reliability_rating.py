
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

print("=" * 70)
print("IPL PLAYER RELIABILITY RATING MODEL")
print("=" * 70)


# ------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------

TOP_N = 10

# Minimum eligibility is already established in Script 31.
# These weights are initial modelling choices and will be
# tested against alternative weight combinations.

WEIGHT_SCENARIOS = {
    "primary": {
        "performance": 0.30,
        "risk": 0.25,
        "consistency": 0.30,
        "sample": 0.15
    },
    "performance_heavy": {
        "performance": 0.35,
        "risk": 0.20,
        "consistency": 0.30,
        "sample": 0.15
    },
    "consistency_heavy": {
        "performance": 0.25,
        "risk": 0.20,
        "consistency": 0.40,
        "sample": 0.15
    },
    "sample_conservative": {
        "performance": 0.30,
        "risk": 0.25,
        "consistency": 0.25,
        "sample": 0.20
    }
}


# ------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------

def require_columns(df, columns, report_name):
    missing = [col for col in columns if col not in df.columns]

    if missing:
        raise ValueError(
            f"\nMissing columns in {report_name}: {missing}\n"
            f"Available columns:\n{df.columns.tolist()}"
        )


def percentile_score(series, higher_is_better=True):
    """
    Convert a metric into a percentile score between 0 and 100.
    Higher scores always represent better performance.
    """

    values = pd.to_numeric(series, errors="coerce")

    return (
        values.rank(
            pct=True,
            ascending=higher_is_better,
            method="average"
        ) * 100
    )


def calculate_sample_strength(matches, balls, target_matches, target_balls):
    """
    Reward meaningful sample sizes without allowing large-volume
    players to dominate indefinitely.

    60% comes from qualifying matches.
    40% comes from pressure-ball opportunities.
    """

    matches = pd.to_numeric(matches, errors="coerce").fillna(0)
    balls = pd.to_numeric(balls, errors="coerce").fillna(0)

    match_strength = (matches / target_matches).clip(upper=1)
    ball_strength = (balls / target_balls).clip(upper=1)

    return (
        0.60 * match_strength
        + 0.40 * ball_strength
    ) * 100


def apply_rating_weights(df, scenarios):
    for scenario_name, weights in scenarios.items():

        df[f"rating_{scenario_name}"] = (
            df["performance_score"] * weights["performance"]
            + df["risk_score"] * weights["risk"]
            + df["consistency_score"] * weights["consistency"]
            + df["sample_score"] * weights["sample"]
        )

        df[f"rank_{scenario_name}"] = (
            df[f"rating_{scenario_name}"]
            .rank(method="min", ascending=False)
            .astype(int)
        )

    return df


def calculate_top10_stability(df):
    """
    Compare the primary top 10 with the top 10 from each
    alternative weighting scenario.
    """

    primary = set(
        df.nsmallest(TOP_N, "rank_primary")["player_name"]
    )

    results = []

    for scenario in WEIGHT_SCENARIOS:

        alternative = set(
            df.nsmallest(TOP_N, f"rank_{scenario}")["player_name"]
        )

        overlap = len(primary.intersection(alternative))

        results.append({
            "scenario": scenario,
            "primary_top10_overlap": overlap,
            "overlap_percentage": overlap / TOP_N * 100
        })

    return pd.DataFrame(results)


# ------------------------------------------------------------
# LOAD DATA
# ------------------------------------------------------------

print("\nLoading consolidated player datasets...")

batter = pd.read_csv(
    REPORTS / "batter_final_metric_dataset.csv"
)

bowler = pd.read_csv(
    REPORTS / "bowler_final_metric_dataset.csv"
)


# ------------------------------------------------------------
# BATTER RELIABILITY MODEL
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("BATTER RELIABILITY MODEL")
print("=" * 70)

require_columns(
    batter,
    [
        "striker_name",
        "eligible_min6",
        "qualifying_matches",
        "consistency_pressure_balls",
        "strike_rate_difference",
        "consistency_percentage",
        "dismissal_rate_difference_y"
    ],
    "batter_final_metric_dataset.csv"
)

# Only eligible players are considered for final rankings.
b = batter[
    batter["eligible_min6"] == True
].copy()

# Corrected dismissal-rate difference:
# Negative means fewer dismissals per 100 balls under pressure.
# Therefore, negate it so higher values are better.
b["dismissal_improvement"] = (
    -pd.to_numeric(
        b["dismissal_rate_difference_y"],
        errors="coerce"
    )
)

# Performance: pressure strike-rate improvement over baseline.
b["performance_score"] = percentile_score(
    b["strike_rate_difference"],
    higher_is_better=True
)

# Risk: lower dismissal rate under pressure is better.
b["risk_score"] = percentile_score(
    b["dismissal_improvement"],
    higher_is_better=True
)

# Consistency: percentage of qualifying matches above baseline.
b["consistency_score"] = percentile_score(
    b["consistency_percentage"],
    higher_is_better=True
)

# Sample strength: match count and pressure balls.
b["sample_score"] = calculate_sample_strength(
    b["qualifying_matches"],
    b["consistency_pressure_balls"],
    target_matches=20,
    target_balls=300
)

b["player_name"] = b["striker_name"]

b = apply_rating_weights(
    b,
    WEIGHT_SCENARIOS
)

b = b.sort_values(
    "rating_primary",
    ascending=False
).reset_index(drop=True)

b["final_rank"] = range(1, len(b) + 1)

b.to_csv(
    REPORTS / "batter_reliability_ratings.csv",
    index=False
)

batter_top10 = b.head(TOP_N).copy()

batter_top10.to_csv(
    REPORTS / "batter_ipl_top10.csv",
    index=False
)

print("\nEligible batters:", len(b))

print("\nTOP 10 BATTERS")

print(
    batter_top10[
        [
            "final_rank",
            "player_name",
            "rating_primary",
            "strike_rate_difference",
            "dismissal_rate_difference_y",
            "consistency_percentage",
            "qualifying_matches",
            "consistency_pressure_balls"
        ]
    ].to_string(index=False)
)


# ------------------------------------------------------------
# BOWLER RELIABILITY MODEL
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("BOWLER RELIABILITY MODEL")
print("=" * 70)

require_columns(
    bowler,
    [
        "bowler_name",
        "eligible_min6",
        "qualifying_matches",
        "pressure_legal_balls",
        "economy_difference",
        "wickets_pressure",
        "legal_balls_pressure",
        "consistency_percentage"
    ],
    "bowler_final_metric_dataset.csv"
)

bo = bowler[
    bowler["eligible_min6"] == True
].copy()

# Economy improvement:
# economy_difference = pressure economy - normal economy.
# Negative is better, so reverse the direction.
bo["economy_improvement"] = (
    -pd.to_numeric(
        bo["economy_difference"],
        errors="coerce"
    )
)

# Wickets per 100 legal pressure balls.
bo["pressure_wickets_per_100_balls"] = (
    pd.to_numeric(bo["wickets_pressure"], errors="coerce")
    / pd.to_numeric(bo["legal_balls_pressure"], errors="coerce")
    * 100
)

# Performance: better pressure economy relative to baseline.
bo["performance_score"] = percentile_score(
    bo["economy_improvement"],
    higher_is_better=True
)

# Risk/control: higher pressure wicket-taking rate.
bo["risk_score"] = percentile_score(
    bo["pressure_wickets_per_100_balls"],
    higher_is_better=True
)

# Consistency: percentage of qualifying matches better than baseline.
bo["consistency_score"] = percentile_score(
    bo["consistency_percentage"],
    higher_is_better=True
)

# Sample strength.
bo["sample_score"] = calculate_sample_strength(
    bo["qualifying_matches"],
    bo["pressure_legal_balls"],
    target_matches=20,
    target_balls=300
)

bo["player_name"] = bo["bowler_name"]

bo = apply_rating_weights(
    bo,
    WEIGHT_SCENARIOS
)

bo = bo.sort_values(
    "rating_primary",
    ascending=False
).reset_index(drop=True)

bo["final_rank"] = range(1, len(bo) + 1)

bo.to_csv(
    REPORTS / "bowler_reliability_ratings.csv",
    index=False
)

bowler_top10 = bo.head(TOP_N).copy()

bowler_top10.to_csv(
    REPORTS / "bowler_ipl_top10.csv",
    index=False
)

print("\nEligible bowlers:", len(bo))

print("\nTOP 10 BOWLERS")

print(
    bowler_top10[
        [
            "final_rank",
            "player_name",
            "rating_primary",
            "economy_difference",
            "pressure_wickets_per_100_balls",
            "consistency_percentage",
            "qualifying_matches",
            "pressure_legal_balls"
        ]
    ].to_string(index=False)
)


# ------------------------------------------------------------
# RANKING SENSITIVITY ANALYSIS
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("RANKING SENSITIVITY ANALYSIS")
print("=" * 70)

batter_stability = calculate_top10_stability(b)
bowler_stability = calculate_top10_stability(bo)

batter_stability.to_csv(
    REPORTS / "batter_ranking_sensitivity.csv",
    index=False
)

bowler_stability.to_csv(
    REPORTS / "bowler_ranking_sensitivity.csv",
    index=False
)

print("\nBATTER TOP 10 STABILITY")

print(batter_stability.to_string(index=False))

print("\nBOWLER TOP 10 STABILITY")

print(bowler_stability.to_string(index=False))


# ------------------------------------------------------------
# FINAL OUTPUT SUMMARY
# ------------------------------------------------------------

print("\n" + "=" * 70)
print("SCRIPT 32 COMPLETED")
print("=" * 70)

print("\nGenerated files:")

output_files = [
    "batter_reliability_ratings.csv",
    "bowler_reliability_ratings.csv",
    "batter_ipl_top10.csv",
    "bowler_ipl_top10.csv",
    "batter_ranking_sensitivity.csv",
    "bowler_ranking_sensitivity.csv"
]

for filename in output_files:
    print("reports/" + filename)

print("\nThe primary ranking uses the initial proposed weights.")
print("Alternative scenarios are saved for robustness evaluation.")
print("\nDo not treat these as final hackathon rankings until")
print("the sensitivity results and T20I supplementary evidence")
print("have been reviewed.")
