
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

print("\n" + "=" * 75)
print("STEP 54: T20I FIRST-INNINGS BENCHMARK SUPPORT AUDIT")
print("=" * 75)

# ---------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------

df = pd.read_csv(
    REPORTS / "t20i_pressure_context_scaled_deliveries.csv.gz",
    low_memory=False
)

first = df[df["innings"] == 1].copy()

print("All delivery records:", len(df))
print("First-innings delivery records:", len(first))
print("First-innings matches:", first["match_id"].nunique())

# ---------------------------------------------------------
# 2. CREATE SIX-BALL SEGMENTS
# ---------------------------------------------------------

first["over_segment"] = (
    first["legal_balls_before"] // 6
).astype(int)

# Wickets lost before the delivery.
first["wicket_band"] = pd.cut(
    first["wickets_before"],
    bins=[-1, 1, 3, 5, 7, 10],
    labels=[
        "0-1 wickets",
        "2-3 wickets",
        "4-5 wickets",
        "6-7 wickets",
        "8-10 wickets",
    ]
)

# ---------------------------------------------------------
# 3. SEASON COVERAGE
# ---------------------------------------------------------

season_summary = (
    first.groupby("season")
    .agg(
        matches=("match_id", "nunique"),
        deliveries=("match_id", "size"),
        unique_batters=("striker_id", "nunique"),
        unique_bowlers=("bowler_id", "nunique"),
    )
    .reset_index()
)

print("\n" + "-" * 75)
print("SEASON COVERAGE")
print("-" * 75)

print(season_summary.to_string(index=False))

# ---------------------------------------------------------
# 4. SUPPORT BY SEASON AND OVER SEGMENT
# ---------------------------------------------------------

segment_support = (
    first.groupby(
        ["season", "over_segment"],
        observed=True
    )
    .agg(
        matches=("match_id", "nunique"),
        deliveries=("match_id", "size"),
    )
    .reset_index()
)

print("\n" + "-" * 75)
print("OVER-SEGMENT SUPPORT BY SEASON")
print("-" * 75)

for season in sorted(first["season"].dropna().unique()):
    print(f"\nSeason: {season}")

    print(
        segment_support[
            segment_support["season"] == season
        ].to_string(index=False)
    )

# ---------------------------------------------------------
# 5. SUPPORT BY SEASON, SEGMENT AND WICKET BAND
# ---------------------------------------------------------

group_support = (
    first.groupby(
        ["season", "over_segment", "wicket_band"],
        observed=True
    )
    .agg(
        matches=("match_id", "nunique"),
        deliveries=("match_id", "size"),
    )
    .reset_index()
)

print("\n" + "-" * 75)
print("HIERARCHICAL GROUP SUPPORT")
print("-" * 75)

print(
    "Groups with at least 5 matches:",
    int((group_support["matches"] >= 5).sum())
)

print(
    "Groups with 3-4 matches:",
    int(
        (
            (group_support["matches"] >= 3) &
            (group_support["matches"] < 5)
        ).sum()
    )
)

print(
    "Groups with fewer than 3 matches:",
    int((group_support["matches"] < 3).sum())
)

# ---------------------------------------------------------
# 6. SUPPORT BY PHASE AND WICKET BAND
# ---------------------------------------------------------

phase_support = (
    first.groupby(
        ["season", "scaled_innings_phase", "wicket_band"],
        observed=True
    )
    .agg(
        matches=("match_id", "nunique"),
        deliveries=("match_id", "size"),
    )
    .reset_index()
)

print("\n" + "-" * 75)
print("PHASE-LEVEL FALLBACK SUPPORT")
print("-" * 75)

print(phase_support.to_string(index=False))

# ---------------------------------------------------------
# 7. SCHEDULED INNINGS LENGTH DISTRIBUTION
# ---------------------------------------------------------

length_summary = (
    first.groupby("scheduled_legal_balls")
    .agg(
        matches=("match_id", "nunique"),
        deliveries=("match_id", "size"),
    )
    .reset_index()
    .sort_values("scheduled_legal_balls")
)

print("\n" + "-" * 75)
print("FIRST-INNINGS SCHEDULED LENGTHS")
print("-" * 75)

print(length_summary.to_string(index=False))

# ---------------------------------------------------------
# 8. SAVE REPORTS
# ---------------------------------------------------------

season_summary.to_csv(
    REPORTS / "t20i_first_innings_season_support.csv",
    index=False
)

segment_support.to_csv(
    REPORTS / "t20i_first_innings_segment_support.csv",
    index=False
)

group_support.to_csv(
    REPORTS / "t20i_first_innings_group_support.csv",
    index=False
)

phase_support.to_csv(
    REPORTS / "t20i_first_innings_phase_support.csv",
    index=False
)

length_summary.to_csv(
    REPORTS / "t20i_first_innings_length_support.csv",
    index=False
)

summary = {
    "first_innings_deliveries": int(len(first)),
    "first_innings_matches": int(first["match_id"].nunique()),
    "season_count": int(first["season"].nunique()),
    "groups_at_least_5_matches": int(
        (group_support["matches"] >= 5).sum()
    ),
    "groups_3_to_4_matches": int(
        (
            (group_support["matches"] >= 3) &
            (group_support["matches"] < 5)
        ).sum()
    ),
    "groups_below_3_matches": int(
        (group_support["matches"] < 3).sum()
    ),
}

with open(
    REPORTS / "t20i_first_innings_benchmark_support_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4)

print("\n" + "=" * 75)
print("STEP 54 COMPLETED")
print("=" * 75)

print(json.dumps(summary, indent=4))
print("\nReports saved in:", REPORTS)
