
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

TOP_N = 10

# Revised eligibility requirements
BATTER_PRESSURE_MATCHES = 8
BATTER_PRESSURE_BALLS = 100
BATTER_NORMAL_MATCHES = 8
BATTER_NORMAL_BALLS = 100

BOWLER_PRESSURE_MATCHES = 8
BOWLER_PRESSURE_BALLS = 120
BOWLER_NORMAL_MATCHES = 8
BOWLER_NORMAL_BALLS = 180

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


def require_columns(df, columns, filename):
    missing = [c for c in columns if c not in df.columns]

    if missing:
        raise ValueError(
            f"{filename} is missing columns: {missing}"
        )


def percentile_score(series):
    values = pd.to_numeric(series, errors="coerce")

    return values.rank(
        pct=True,
        ascending=True,
        method="average"
    ) * 100


def calculate_sample_strength(matches, balls):
    matches = pd.to_numeric(matches, errors="coerce").fillna(0)
    balls = pd.to_numeric(balls, errors="coerce").fillna(0)

    match_strength = (matches / 20).clip(upper=1)
    ball_strength = (balls / 300).clip(upper=1)

    return (
        0.60 * match_strength
        + 0.40 * ball_strength
    ) * 100


def add_ratings(df):
    df = df.copy()

    df["performance_score"] = percentile_score(
        df["performance_metric"]
    )

    df["risk_score"] = percentile_score(
        df["risk_metric"]
    )

    df["consistency_score"] = percentile_score(
        df["consistency_percentage"]
    )

    df["sample_score"] = calculate_sample_strength(
        df["qualifying_matches"],
        df["sample_pressure_balls"]
    )

    for scenario, weights in WEIGHT_SCENARIOS.items():

        df[f"rating_{scenario}"] = (
            df["performance_score"] * weights["performance"]
            + df["risk_score"] * weights["risk"]
            + df["consistency_score"] * weights["consistency"]
            + df["sample_score"] * weights["sample"]
        )

        df[f"rank_{scenario}"] = (
            df[f"rating_{scenario}"]
            .rank(method="min", ascending=False)
            .astype(int)
        )

    df = df.sort_values(
        "rating_primary",
        ascending=False
    ).reset_index(drop=True)

    df["final_rank"] = range(1, len(df) + 1)

    return df


def save_comparison(new_df, old_file, id_col, name_col, output_file):

    old_path = REPORTS / old_file

    if not old_path.exists():
        print(f"WARNING: Original file not found: {old_file}")
        return

    old = pd.read_csv(old_path)

    require_columns(
        old,
        [id_col, "final_rank", "rating_primary"],
        old_file
    )

    old_top = old.nsmallest(TOP_N, "final_rank")[
        [id_col, name_col, "final_rank", "rating_primary"]
    ].copy()

    old_top = old_top.rename(columns={
        "final_rank": "old_rank",
        "rating_primary": "old_rating",
        name_col: "old_player_name"
    })

    new_top = new_df.nsmallest(TOP_N, "final_rank")[
        [id_col, name_col, "final_rank", "rating_primary"]
    ].copy()

    new_top = new_top.rename(columns={
        "final_rank": "new_rank",
        "rating_primary": "new_rating",
        name_col: "new_player_name"
    })

    comparison = old_top.merge(
        new_top,
        on=id_col,
        how="outer"
    )

    comparison["ranking_status"] = np.select(
        [
            comparison["old_rank"].notna()
            & comparison["new_rank"].notna(),

            comparison["old_rank"].notna()
            & comparison["new_rank"].isna(),

            comparison["old_rank"].isna()
            & comparison["new_rank"].notna()
        ],
        [
            "RETAINED_IN_BOTH_TOP10",
            "REMOVED_FROM_TOP10",
            "NEW_IN_TOP10"
        ],
        default="OTHER"
    )

    comparison.to_csv(
        REPORTS / output_file,
        index=False
    )

    old_ids = set(old_top[id_col])
    new_ids = set(new_top[id_col])

    print("\nOriginal top 10:", len(old_ids))
    print("Revised top 10:", len(new_ids))
    print("Common players:", len(old_ids & new_ids))
    print("Top-10 overlap:", len(old_ids & new_ids) * 10, "%")

    print("\nTOP 10 COMPARISON")
    print(comparison.to_string(index=False))


print("=" * 85)
print("STEP 73: REVISED IPL PLAYER RELIABILITY MODEL")
print("=" * 85)

# ------------------------------------------------------------
# LOAD ORIGINAL CONSOLIDATED DATASETS
# ------------------------------------------------------------

batter = pd.read_csv(
    REPORTS / "batter_final_metric_dataset.csv"
)

bowler = pd.read_csv(
    REPORTS / "bowler_final_metric_dataset.csv"
)

# ------------------------------------------------------------
# BATTER MODEL
# ------------------------------------------------------------

print("\n" + "=" * 85)
print("REVISED BATTER MODEL")
print("=" * 85)

batter_columns = [
    "striker_id",
    "striker_name",
    "qualifying_matches",
    "consistency_pressure_balls",
    "matches_normal",
    "balls_normal",
    "strike_rate_difference",
    "dismissal_rate_difference_y",
    "consistency_percentage"
]

require_columns(
    batter,
    batter_columns,
    "batter_final_metric_dataset.csv"
)

for col in [
    "qualifying_matches",
    "consistency_pressure_balls",
    "matches_normal",
    "balls_normal",
    "strike_rate_difference",
    "dismissal_rate_difference_y",
    "consistency_percentage"
]:
    batter[col] = pd.to_numeric(
        batter[col], errors="coerce"
    )

batter["eligible_revised"] = (
    (batter["qualifying_matches"] >= BATTER_PRESSURE_MATCHES)
    & (batter["consistency_pressure_balls"] >= BATTER_PRESSURE_BALLS)
    & (batter["matches_normal"] >= BATTER_NORMAL_MATCHES)
    & (batter["balls_normal"] >= BATTER_NORMAL_BALLS)
)

batter["exclusion_reason"] = ""

conditions = [
    batter["qualifying_matches"] < BATTER_PRESSURE_MATCHES,
    batter["consistency_pressure_balls"] < BATTER_PRESSURE_BALLS,
    batter["matches_normal"] < BATTER_NORMAL_MATCHES,
    batter["balls_normal"] < BATTER_NORMAL_BALLS
]

reasons = [
    "Insufficient pressure matches",
    "Insufficient pressure balls",
    "Insufficient normal matches",
    "Insufficient normal balls"
]

for condition, reason in zip(conditions, reasons):
    batter.loc[
        condition,
        "exclusion_reason"
    ] += reason + "; "

batter["exclusion_reason"] = (
    batter["exclusion_reason"].str.rstrip("; ")
)

b = batter[batter["eligible_revised"]].copy()

b["performance_metric"] = b["strike_rate_difference"]

# Negative dismissal-rate difference means improvement.
b["risk_metric"] = -b["dismissal_rate_difference_y"]

b["sample_pressure_balls"] = b["consistency_pressure_balls"]

b["player_name"] = b["striker_name"]

b = add_ratings(b)

b.to_csv(
    REPORTS / "batter_reliability_ratings_revised.csv",
    index=False
)

b.head(TOP_N).to_csv(
    REPORTS / "batter_ipl_top10_revised.csv",
    index=False
)

batter.to_csv(
    REPORTS / "batter_revised_eligibility_audit.csv",
    index=False
)

print("Original eligible population:",
      int(batter["eligible_min6"].sum()))

print("Revised eligible population:", len(b))

print("\nREVISED TOP 10 BATTERS")

print(
    b.head(TOP_N)[
        [
            "final_rank",
            "player_name",
            "rating_primary",
            "strike_rate_difference",
            "dismissal_rate_difference_y",
            "consistency_percentage",
            "qualifying_matches",
            "consistency_pressure_balls",
            "matches_normal",
            "balls_normal"
        ]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# BOWLER MODEL
# ------------------------------------------------------------

print("\n" + "=" * 85)
print("REVISED BOWLER MODEL")
print("=" * 85)

bowler_columns = [
    "bowler_id",
    "bowler_name",
    "qualifying_matches",
    "pressure_legal_balls",
    "matches_normal",
    "legal_balls_normal",
    "economy_difference",
    "wickets_pressure",
    "legal_balls_pressure",
    "consistency_percentage"
]

require_columns(
    bowler,
    bowler_columns,
    "bowler_final_metric_dataset.csv"
)

for col in [
    "qualifying_matches",
    "pressure_legal_balls",
    "matches_normal",
    "legal_balls_normal",
    "economy_difference",
    "wickets_pressure",
    "legal_balls_pressure",
    "consistency_percentage"
]:
    bowler[col] = pd.to_numeric(
        bowler[col], errors="coerce"
    )

bowler["eligible_revised"] = (
    (bowler["qualifying_matches"] >= BOWLER_PRESSURE_MATCHES)
    & (bowler["pressure_legal_balls"] >= BOWLER_PRESSURE_BALLS)
    & (bowler["matches_normal"] >= BOWLER_NORMAL_MATCHES)
    & (bowler["legal_balls_normal"] >= BOWLER_NORMAL_BALLS)
)

bowler["exclusion_reason"] = ""

conditions = [
    bowler["qualifying_matches"] < BOWLER_PRESSURE_MATCHES,
    bowler["pressure_legal_balls"] < BOWLER_PRESSURE_BALLS,
    bowler["matches_normal"] < BOWLER_NORMAL_MATCHES,
    bowler["legal_balls_normal"] < BOWLER_NORMAL_BALLS
]

reasons = [
    "Insufficient pressure matches",
    "Insufficient pressure legal balls",
    "Insufficient normal matches",
    "Insufficient normal legal balls"
]

for condition, reason in zip(conditions, reasons):
    bowler.loc[
        condition,
        "exclusion_reason"
    ] += reason + "; "

bowler["exclusion_reason"] = (
    bowler["exclusion_reason"].str.rstrip("; ")
)

bo = bowler[bowler["eligible_revised"]].copy()

# Negative economy difference means improvement.
bo["performance_metric"] = -bo["economy_difference"]

bo["risk_metric"] = (
    pd.to_numeric(bo["wickets_pressure"], errors="coerce")
    / pd.to_numeric(bo["legal_balls_pressure"], errors="coerce")
    * 100
)

bo["sample_pressure_balls"] = bo["pressure_legal_balls"]

bo["player_name"] = bo["bowler_name"]

bo = add_ratings(bo)

bo.to_csv(
    REPORTS / "bowler_reliability_ratings_revised.csv",
    index=False
)

bo.head(TOP_N).to_csv(
    REPORTS / "bowler_ipl_top10_revised.csv",
    index=False
)

bowler.to_csv(
    REPORTS / "bowler_revised_eligibility_audit.csv",
    index=False
)

print("Original eligible population:",
      int(bowler["eligible_min6"].sum()))

print("Revised eligible population:", len(bo))

print("\nREVISED TOP 10 BOWLERS")

print(
    bo.head(TOP_N)[
        [
            "final_rank",
            "player_name",
            "rating_primary",
            "economy_difference",
            "wickets_pressure",
            "legal_balls_pressure",
            "consistency_percentage",
            "qualifying_matches",
            "pressure_legal_balls",
            "matches_normal",
            "legal_balls_normal"
        ]
    ].to_string(index=False)
)

# ------------------------------------------------------------
# OLD VS REVISED TOP 10 COMPARISON
# ------------------------------------------------------------

print("\n" + "=" * 85)
print("ORIGINAL VS REVISED RANKING COMPARISON")
print("=" * 85)

save_comparison(
    b,
    "batter_reliability_ratings.csv",
    "striker_id",
    "striker_name",
    "batter_original_vs_revised_top10.csv"
)

save_comparison(
    bo,
    "bowler_reliability_ratings.csv",
    "bowler_id",
    "bowler_name",
    "bowler_original_vs_revised_top10.csv"
)

# ------------------------------------------------------------
# RASHID KHAN CHECK
# ------------------------------------------------------------

print("\n" + "=" * 85)
print("RASHID KHAN ELIGIBILITY CHECK")
print("=" * 85)

rashid = batter[batter["striker_id"] == 4722]

if rashid.empty:
    print("Rashid Khan not found.")
else:
    print(
        rashid[
            [
                "striker_name",
                "qualifying_matches",
                "consistency_pressure_balls",
                "matches_normal",
                "balls_normal",
                "eligible_revised",
                "exclusion_reason"
            ]
        ].to_string(index=False)
    )

# ------------------------------------------------------------
# SENSITIVITY ANALYSIS
# ------------------------------------------------------------

sensitivity_rows = []

for player_type, frame in [
    ("Batter", b),
    ("Bowler", bo)
]:
    primary_ids = set(
        frame.nsmallest(TOP_N, "rank_primary")["player_name"]
    )

    for scenario in WEIGHT_SCENARIOS:
        scenario_ids = set(
            frame.nsmallest(
                TOP_N,
                f"rank_{scenario}"
            )["player_name"]
        )

        overlap = len(primary_ids & scenario_ids)

        sensitivity_rows.append({
            "player_type": player_type,
            "scenario": scenario,
            "primary_top10_overlap": overlap,
            "overlap_percentage": overlap * 10
        })

pd.DataFrame(sensitivity_rows).to_csv(
    REPORTS / "ipl_revised_ranking_weight_sensitivity.csv",
    index=False
)

# ------------------------------------------------------------
# SUMMARY
# ------------------------------------------------------------

summary = pd.DataFrame([
    {
        "player_type": "Batter",
        "original_eligible": int(batter["eligible_min6"].sum()),
        "revised_eligible": len(b)
    },
    {
        "player_type": "Bowler",
        "original_eligible": int(bowler["eligible_min6"].sum()),
        "revised_eligible": len(bo)
    }
])

summary.to_csv(
    REPORTS / "ipl_revised_eligibility_summary.csv",
    index=False
)

print("\n" + "=" * 85)
print("STEP 73 COMPLETED")
print("=" * 85)

print("\nGenerated files:")
for filename in [
    "batter_reliability_ratings_revised.csv",
    "bowler_reliability_ratings_revised.csv",
    "batter_ipl_top10_revised.csv",
    "bowler_ipl_top10_revised.csv",
    "batter_revised_eligibility_audit.csv",
    "bowler_revised_eligibility_audit.csv",
    "batter_original_vs_revised_top10.csv",
    "bowler_original_vs_revised_top10.csv",
    "ipl_revised_ranking_weight_sensitivity.csv",
    "ipl_revised_eligibility_summary.csv"
]:
    print("reports/" + filename)
