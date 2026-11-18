
import pandas as pd
from pathlib import Path

folder = Path("reports")
df = pd.read_csv(folder / "bowler_reliability_ratings.csv")

print("=" * 85)
print("STEP 72: IPL BOWLER NORMAL-SAMPLE SENSITIVITY AUDIT")
print("=" * 85)

print("\nAVAILABLE COLUMNS:")
print(df.columns.tolist())

# Identify the relevant columns
id_col = "bowler_id"
name_col = "bowler_name"

required = [
    id_col, name_col, "eligible",
    "final_rank", "rating_primary"
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing required columns: {missing}")

# Locate normal and pressure exposure columns
normal_ball_col = next(
    (c for c in ["balls_normal", "legal_balls_normal",
                 "deliveries_normal"] if c in df.columns),
    None
)

normal_match_col = next(
    (c for c in ["matches_normal"] if c in df.columns),
    None
)

pressure_ball_col = next(
    (c for c in ["balls_pressure", "legal_balls_pressure",
                 "deliveries_pressure"] if c in df.columns),
    None
)

if not all([normal_ball_col, normal_match_col, pressure_ball_col]):
    raise ValueError(
        "Could not identify exposure columns. "
        "Inspect the available columns printed above."
    )

for col in [
    normal_ball_col, normal_match_col,
    pressure_ball_col, "final_rank", "rating_primary"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

eligible = df[df["eligible"].astype(str).str.lower().isin(
    ["true", "1"]
)].copy()

current_top10 = eligible.nsmallest(10, "final_rank")

print("\nCURRENT BOWLER POPULATION:", len(eligible))

print("\nCURRENT TOP 10 — NORMAL EXPOSURE")
print(
    current_top10[
        [
            "final_rank", name_col,
            normal_ball_col, normal_match_col,
            pressure_ball_col, "rating_primary"
        ]
    ].to_string(index=False)
)

thresholds = [90, 120, 180]

summary = []
all_tops = []

original_ids = set(current_top10[id_col])

for threshold in thresholds:

    scenario = eligible[
        (eligible[normal_ball_col] >= threshold) &
        (eligible[normal_match_col] >= 8)
    ].copy()

    scenario = scenario.sort_values(
        "rating_primary", ascending=False
    )

    top = scenario.head(10).copy()
    top["normal_ball_threshold"] = threshold
    top["scenario_rank"] = range(1, len(top) + 1)

    overlap = len(set(top[id_col]) & original_ids)

    summary.append({
        "minimum_normal_legal_balls": threshold,
        "minimum_normal_matches": 8,
        "eligible_bowlers": len(scenario),
        "top10_overlap_with_original": overlap,
        "top10_overlap_percentage": overlap * 10
    })

    all_tops.append(top)

    print("\n" + "-" * 85)
    print(
        f"SCENARIO: NORMAL LEGAL BALLS >= {threshold}, "
        "NORMAL MATCHES >= 8"
    )
    print("Eligible bowlers:", len(scenario))
    print("Top-10 overlap:", overlap, "/ 10")

    if not top.empty:
        print(
            top[
                [
                    "scenario_rank", name_col,
                    normal_ball_col, normal_match_col,
                    pressure_ball_col, "rating_primary"
                ]
            ].to_string(index=False)
        )

pd.DataFrame(summary).to_csv(
    folder / "ipl_bowler_normal_sample_sensitivity_summary.csv",
    index=False
)

if all_tops:
    pd.concat(all_tops, ignore_index=True).to_csv(
        folder / "ipl_bowler_normal_sample_sensitivity_top10.csv",
        index=False
    )

print("\nSaved bowler normal-sample sensitivity files.")
print("STEP 72 COMPLETED")
