
import pandas as pd
from pathlib import Path

folder = Path("reports")

df = pd.read_csv(folder / "batter_reliability_ratings.csv")

# Convert relevant fields to numeric
numeric_cols = [
    "balls_normal",
    "matches_normal",
    "balls_pressure",
    "matches_pressure",
    "strike_rate_difference",
    "dismissal_improvement",
    "consistency_percentage",
    "sample_score",
    "rating_primary",
    "final_rank"
]

for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

print("=" * 85)
print("STEP 71: IPL BATTER NORMAL-SAMPLE SENSITIVITY AUDIT")
print("=" * 85)

# Current eligibility and ranking
eligible = df[df["eligible"] == True].copy()

print("\nCURRENT POPULATION")
print("Eligible batters:", len(eligible))

# Inspect current top 10
current_top10 = eligible.nsmallest(10, "final_rank")

print("\nCURRENT TOP 10 — NORMAL EXPOSURE")
print(
    current_top10[
        [
            "final_rank",
            "striker_name",
            "balls_normal",
            "matches_normal",
            "balls_pressure",
            "matches_pressure",
            "rating_primary"
        ]
    ].to_string(index=False)
)

# Test alternative normal-ball thresholds
thresholds = [60, 100, 150]

summary = []
scenario_results = []

for threshold in thresholds:

    scenario = eligible[
        (eligible["balls_normal"] >= threshold) &
        (eligible["matches_normal"] >= 8)
    ].copy()

    scenario = scenario.sort_values(
        "rating_primary",
        ascending=False
    )

    surviving_top10 = set(
        scenario["striker_id"].head(10)
    )

    original_top10_ids = set(
        current_top10["striker_id"]
    )

    overlap = len(surviving_top10 & original_top10_ids)

    summary.append({
        "minimum_normal_balls": threshold,
        "minimum_normal_matches": 8,
        "eligible_players": len(scenario),
        "top10_overlap_with_original": overlap,
        "top10_overlap_percentage": overlap * 10
    })

    top = scenario.head(10).copy()
    top["normal_ball_threshold"] = threshold
    top["scenario_rank"] = range(1, len(top) + 1)

    scenario_results.append(top)

    print("\n" + "-" * 85)
    print(f"SCENARIO: NORMAL BALLS >= {threshold}, NORMAL MATCHES >= 8")
    print("Eligible players:", len(scenario))
    print("Top-10 overlap with original:", overlap, "/ 10")

    if len(scenario):
        print(
            top[
                [
                    "scenario_rank",
                    "striker_name",
                    "balls_normal",
                    "matches_normal",
                    "balls_pressure",
                    "rating_primary"
                ]
            ].to_string(index=False)
        )

# Rashid's survival
rashid = eligible[eligible["striker_id"] == 4722]

print("\n" + "=" * 85)
print("RASHID KHAN SCENARIO CHECK")
print("=" * 85)

if rashid.empty:
    print("Rashid Khan not found in current eligible population.")
else:
    print(
        rashid[
            [
                "striker_name",
                "balls_normal",
                "matches_normal",
                "balls_pressure",
                "matches_pressure",
                "rating_primary",
                "final_rank"
            ]
        ].to_string(index=False)
    )

    for threshold in thresholds:
        qualifies = (
            rashid.iloc[0]["balls_normal"] >= threshold
            and rashid.iloc[0]["matches_normal"] >= 8
        )
        print(f"Normal balls >= {threshold}: {qualifies}")

summary_df = pd.DataFrame(summary)

summary_df.to_csv(
    folder / "ipl_batter_normal_sample_sensitivity_summary.csv",
    index=False
)

if scenario_results:
    pd.concat(
        scenario_results,
        ignore_index=True
    ).to_csv(
        folder / "ipl_batter_normal_sample_sensitivity_top10.csv",
        index=False
    )

print("\nSaved:")
print("reports/ipl_batter_normal_sample_sensitivity_summary.csv")
print("reports/ipl_batter_normal_sample_sensitivity_top10.csv")

print("\nSTEP 71 COMPLETED")
