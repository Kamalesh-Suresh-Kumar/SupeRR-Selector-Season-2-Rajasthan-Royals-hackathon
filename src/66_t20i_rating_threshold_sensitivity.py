
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# STEP 66: T20I RATING THRESHOLD SENSITIVITY
# ============================================================

REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)

FILES = {
    "batters": REPORTS / "t20i_batter_corrected_exposure_audit.csv",
    "bowlers": REPORTS / "t20i_bowler_corrected_exposure_audit.csv",
    "batter_consistency": REPORTS / "t20i_batter_pressure_consistency.csv",
    "bowler_consistency": REPORTS / "t20i_bowler_pressure_consistency.csv"
}

SCENARIOS = {
    "flexible": {
        "matches": 6,
        "batter_balls": 75,
        "bowler_balls": 90
    },
    "primary": {
        "matches": 8,
        "batter_balls": 100,
        "bowler_balls": 120
    },
    "strict": {
        "matches": 12,
        "batter_balls": 150,
        "bowler_balls": 180
    }
}

print("\n" + "=" * 80)
print("STEP 66: T20I RATING THRESHOLD SENSITIVITY")
print("=" * 80)


# ============================================================
# 1. CHECK AND LOAD DATA
# ============================================================

for name, file_path in FILES.items():
    if not file_path.exists():
        raise FileNotFoundError(
            f"Required file not found: {file_path}"
        )

batters = pd.read_csv(FILES["batters"])
bowlers = pd.read_csv(FILES["bowlers"])

batter_consistency = pd.read_csv(
    FILES["batter_consistency"]
)

bowler_consistency = pd.read_csv(
    FILES["bowler_consistency"]
)

print("Batter records:", len(batters))
print("Bowler records:", len(bowlers))


# ============================================================
# 2. VALIDATE AND MERGE CONSISTENCY
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

if batters["striker_id"].isna().any():
    raise ValueError("Missing or invalid batter IDs in exposure data.")

if bowlers["bowler_id"].isna().any():
    raise ValueError("Missing or invalid bowler IDs in exposure data.")

if batter_consistency["striker_id"].isna().any():
    raise ValueError("Missing or invalid batter IDs in consistency data.")

if bowler_consistency["bowler_id"].isna().any():
    raise ValueError("Missing or invalid bowler IDs in consistency data.")

if batter_consistency["striker_id"].duplicated().any():
    raise ValueError("Duplicate batter IDs in consistency data.")

if bowler_consistency["bowler_id"].duplicated().any():
    raise ValueError("Duplicate bowler IDs in consistency data.")

if "consistency_pct" not in batter_consistency.columns:
    raise ValueError("consistency_pct missing from batter consistency file.")

if "consistency_pct" not in bowler_consistency.columns:
    raise ValueError("consistency_pct missing from bowler consistency file.")

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

print("\nConsistency merge completed.")

print(
    "Batters without consistency:",
    batters["consistency_pct"].isna().sum()
)

print(
    "Bowlers without consistency:",
    bowlers["consistency_pct"].isna().sum()
)

# Missing consistency is checked after eligibility filtering.
# Ineligible players do not need a consistency score.


# ============================================================
# 3. PREPARE PERFORMANCE COMPONENTS
# ============================================================

required_batter_columns = [
    "matches_pressure",
    "matches_normal",
    "balls_pressure",
    "balls_normal",
    "strike_rate_pressure",
    "strike_rate_normal",
    "dismissal_rate_normal",
    "dismissal_rate_pressure",
    "striker_name"
]

required_bowler_columns = [
    "matches_pressure",
    "matches_normal",
    "legal_balls_pressure",
    "legal_balls_normal",
    "economy_normal",
    "economy_pressure",
    "wickets_pressure",
    "bowler_name"
]

for column in required_batter_columns:
    if column not in batters.columns:
        raise ValueError(
            f"Missing required batter column: {column}"
        )

for column in required_bowler_columns:
    if column not in bowlers.columns:
        raise ValueError(
            f"Missing required bowler column: {column}"
        )

batters["strike_rate_improvement"] = (
    batters["strike_rate_pressure"]
    - batters["strike_rate_normal"]
)

batters["dismissal_rate_improvement"] = (
    batters["dismissal_rate_normal"]
    - batters["dismissal_rate_pressure"]
)

bowlers["economy_improvement"] = (
    bowlers["economy_normal"]
    - bowlers["economy_pressure"]
)

bowlers["pressure_wickets_per_100_balls"] = (
    bowlers["wickets_pressure"] * 100
    / bowlers["legal_balls_pressure"].replace(0, np.nan)
)


# ============================================================
# 4. SCORING FUNCTIONS
# ============================================================

def percentile(series):
    values = pd.to_numeric(series, errors="coerce")

    if values.isna().any():
        raise ValueError(
            "Missing or invalid values in a scoring component."
        )

    return values.rank(method="average", pct=True) * 100


def validate_eligible_data(data, player_type):
    if len(data) < 10:
        raise ValueError(
            f"Fewer than 10 eligible {player_type}s; "
            "cannot create a top 10."
        )

    if data["consistency_pct"].isna().any():
        missing_count = data["consistency_pct"].isna().sum()

        raise ValueError(
            f"{missing_count} eligible {player_type}s have missing "
            "consistency values. Investigate the consistency source; "
            "do not replace these values with zero."
        )

    if not np.isfinite(
        pd.to_numeric(data["consistency_pct"], errors="coerce")
    ).all():
        raise ValueError(
            f"Invalid consistency values among eligible {player_type}s."
        )


def calculate_batter_ratings(data):
    data = data.copy()

    validate_eligible_data(data, "batters")

    data["sample_match_score"] = (
        data["matches_pressure"] / 20
    ).clip(upper=1) * 100

    data["sample_ball_score"] = (
        data["balls_pressure"] / 300
    ).clip(upper=1) * 100

    data["sample_score"] = (
        0.60 * data["sample_match_score"]
        + 0.40 * data["sample_ball_score"]
    )

    data["performance_score"] = percentile(
        data["strike_rate_improvement"]
    )

    data["secondary_score"] = percentile(
        data["dismissal_rate_improvement"]
    )

    data["consistency_score"] = percentile(
        data["consistency_pct"]
    )

    data["sample_percentile_score"] = percentile(
        data["sample_score"]
    )

    data["rating"] = (
        0.30 * data["performance_score"]
        + 0.25 * data["secondary_score"]
        + 0.30 * data["consistency_score"]
        + 0.15 * data["sample_percentile_score"]
    )

    return data.sort_values(
        ["rating", "matches_pressure"],
        ascending=[False, False]
    ).reset_index(drop=True)


def calculate_bowler_ratings(data):
    data = data.copy()

    validate_eligible_data(data, "bowlers")

    data["sample_match_score"] = (
        data["matches_pressure"] / 20
    ).clip(upper=1) * 100

    data["sample_ball_score"] = (
        data["legal_balls_pressure"] / 300
    ).clip(upper=1) * 100

    data["sample_score"] = (
        0.60 * data["sample_match_score"]
        + 0.40 * data["sample_ball_score"]
    )

    data["performance_score"] = percentile(
        data["economy_improvement"]
    )

    data["secondary_score"] = percentile(
        data["pressure_wickets_per_100_balls"]
    )

    data["consistency_score"] = percentile(
        data["consistency_pct"]
    )

    data["sample_percentile_score"] = percentile(
        data["sample_score"]
    )

    data["rating"] = (
        0.30 * data["performance_score"]
        + 0.25 * data["secondary_score"]
        + 0.30 * data["consistency_score"]
        + 0.15 * data["sample_percentile_score"]
    )

    return data.sort_values(
        ["rating", "matches_pressure"],
        ascending=[False, False]
    ).reset_index(drop=True)


# ============================================================
# 5. APPLY EACH ELIGIBILITY SCENARIO
# ============================================================

batter_rankings = {}
bowler_rankings = {}

summary_rows = []

for scenario, limits in SCENARIOS.items():

    print(f"\nCalculating scenario: {scenario.upper()}")

    batter_match_limit = limits["matches"]
    batter_ball_limit = limits["batter_balls"]

    bowler_match_limit = limits["matches"]
    bowler_ball_limit = limits["bowler_balls"]

    eligible_batters = batters[
        (batters["matches_pressure"] >= batter_match_limit)
        & (batters["matches_normal"] >= batter_match_limit)
        & (batters["balls_pressure"] >= batter_ball_limit)
        & (batters["balls_normal"] >= batter_ball_limit)
    ].copy()

    eligible_bowlers = bowlers[
        (bowlers["matches_pressure"] >= bowler_match_limit)
        & (bowlers["matches_normal"] >= bowler_match_limit)
        & (bowlers["legal_balls_pressure"] >= bowler_ball_limit)
        & (bowlers["legal_balls_normal"] >= bowler_ball_limit)
    ].copy()

    print(
        f"Eligible batters: {len(eligible_batters)} | "
        f"Eligible bowlers: {len(eligible_bowlers)}"
    )

    # Validate consistency only for eligible players.
    # This is the main correction to the earlier script.

    batter_ranked = calculate_batter_ratings(
        eligible_batters
    )

    bowler_ranked = calculate_bowler_ratings(
        eligible_bowlers
    )

    batter_ranked["rank"] = np.arange(
        1, len(batter_ranked) + 1
    )

    bowler_ranked["rank"] = np.arange(
        1, len(bowler_ranked) + 1
    )

    batter_rankings[scenario] = batter_ranked
    bowler_rankings[scenario] = bowler_ranked

    batter_ranked.to_csv(
        REPORTS / f"t20i_batter_ratings_{scenario}.csv",
        index=False
    )

    bowler_ranked.to_csv(
        REPORTS / f"t20i_bowler_ratings_{scenario}.csv",
        index=False
    )

    batter_top = batter_ranked.head(10).copy()
    bowler_top = bowler_ranked.head(10).copy()

    batter_top.to_csv(
        REPORTS / f"t20i_batter_top10_{scenario}.csv",
        index=False
    )

    bowler_top.to_csv(
        REPORTS / f"t20i_bowler_top10_{scenario}.csv",
        index=False
    )

    summary_rows.append({
        "scenario": scenario,
        "player_type": "Batter",
        "eligible_players": len(batter_ranked),
        "top10_available": len(batter_top)
    })

    summary_rows.append({
        "scenario": scenario,
        "player_type": "Bowler",
        "eligible_players": len(bowler_ranked),
        "top10_available": len(bowler_top)
    })


# ============================================================
# 6. COMPARE TOP-10 RANKING OVERLAP
# ============================================================

overlap_rows = []

for player_type, rankings, id_col in [
    ("Batter", batter_rankings, "striker_id"),
    ("Bowler", bowler_rankings, "bowler_id")
]:

    flexible = set(
        rankings["flexible"].head(10)[id_col]
    )

    primary = set(
        rankings["primary"].head(10)[id_col]
    )

    strict = set(
        rankings["strict"].head(10)[id_col]
    )

    for comparison, set_a, set_b in [
        ("Flexible vs Primary", flexible, primary),
        ("Primary vs Strict", primary, strict),
        ("Flexible vs Strict", flexible, strict)
    ]:

        common = set_a & set_b
        union = set_a | set_b

        overlap_rows.append({
            "player_type": player_type,
            "comparison": comparison,
            "common_top10_players": len(common),
            "top10_overlap_pct": round(
                len(common) / 10 * 100, 2
            ),
            "jaccard_overlap_pct": round(
                len(common) / len(union) * 100,
                2
            ) if union else 0
        })


overlap = pd.DataFrame(overlap_rows)

overlap.to_csv(
    REPORTS / "t20i_rating_threshold_overlap.csv",
    index=False
)

summary = pd.DataFrame(summary_rows)

summary.to_csv(
    REPORTS / "t20i_rating_threshold_summary.csv",
    index=False
)


# ============================================================
# 7. PLAYER RANK MOVEMENT
# ============================================================

movement_rows = []

for player_type, rankings, id_col, name_col in [
    ("Batter", batter_rankings, "striker_id", "striker_name"),
    ("Bowler", bowler_rankings, "bowler_id", "bowler_name")
]:

    flexible = rankings["flexible"][
        ["rank", id_col, name_col, "rating"]
    ].rename(columns={
        "rank": "flexible_rank",
        "rating": "flexible_rating"
    })

    primary = rankings["primary"][
        ["rank", id_col, "rating"]
    ].rename(columns={
        "rank": "primary_rank",
        "rating": "primary_rating"
    })

    strict = rankings["strict"][
        ["rank", id_col, "rating"]
    ].rename(columns={
        "rank": "strict_rank",
        "rating": "strict_rating"
    })

    combined = flexible.merge(
        primary, on=id_col, how="outer"
    ).merge(
        strict, on=id_col, how="outer"
    )

    combined.insert(0, "player_type", player_type)

    combined.to_csv(
        REPORTS / (
            "t20i_"
            + player_type.lower()
            + "_rating_rank_movement.csv"
        ),
        index=False
    )

    for _, row in combined.iterrows():
        movement_rows.append(row.to_dict())

movement = pd.DataFrame(movement_rows)

movement.to_csv(
    REPORTS / "t20i_rating_rank_movement_all_players.csv",
    index=False
)


# ============================================================
# 8. DISPLAY RESULTS
# ============================================================

print("\n" + "=" * 80)
print("ELIGIBLE POPULATION BY SCENARIO")
print("=" * 80)

print(summary.to_string(index=False))

print("\n" + "=" * 80)
print("TOP-10 RANKING OVERLAP")
print("=" * 80)

print(overlap.to_string(index=False))


for scenario in ["flexible", "primary", "strict"]:

    print("\n" + "=" * 80)
    print(f"{scenario.upper()} BATTER TOP 10")
    print("=" * 80)

    print(
        batter_rankings[scenario][
            ["rank", "striker_name", "rating",
             "matches_pressure", "balls_pressure"]
        ].head(10).round(2).to_string(index=False)
    )

    print("\n" + "=" * 80)
    print(f"{scenario.upper()} BOWLER TOP 10")
    print("=" * 80)

    print(
        bowler_rankings[scenario][
            ["rank", "bowler_name", "rating",
             "matches_pressure", "legal_balls_pressure"]
        ].head(10).round(2).to_string(index=False)
    )


# ============================================================
# 9. COMPLETION
# ============================================================

print("\n" + "=" * 80)
print("STEP 66 COMPLETED")
print("=" * 80)

print("\nGenerated reports:")
print(" - t20i_rating_threshold_summary.csv")
print(" - t20i_rating_threshold_overlap.csv")
print(" - t20i_rating_rank_movement_all_players.csv")
print(" - t20i_batter_rating_rank_movement.csv")
print(" - t20i_bowler_rating_rank_movement.csv")
print(" - t20i_batter_ratings_flexible.csv")
print(" - t20i_batter_ratings_primary.csv")
print(" - t20i_batter_ratings_strict.csv")
print(" - t20i_bowler_ratings_flexible.csv")
print(" - t20i_bowler_ratings_primary.csv")
print(" - t20i_bowler_ratings_strict.csv")
print(" - Six scenario-specific top-10 files")

print("\nSTEP 66 FINISHED.")
