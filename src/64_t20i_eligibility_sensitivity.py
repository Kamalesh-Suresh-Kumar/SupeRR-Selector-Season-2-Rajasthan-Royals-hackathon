
from pathlib import Path

import pandas as pd


# ============================================================
# STEP 64: T20I ELIGIBILITY AND SAMPLE-SIZE SENSITIVITY
# ============================================================

REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)

BATTER_FILE = REPORTS / "t20i_batter_corrected_exposure_audit.csv"
BOWLER_FILE = REPORTS / "t20i_bowler_corrected_exposure_audit.csv"

print("\n" + "=" * 80)
print("STEP 64: T20I ELIGIBILITY AND SAMPLE-SIZE SENSITIVITY")
print("=" * 80)


# ============================================================
# 1. LOAD CORRECTED PLAYER EXPOSURE DATA
# ============================================================

batters = pd.read_csv(BATTER_FILE)
bowlers = pd.read_csv(BOWLER_FILE)

print("Batter records:", len(batters))
print("Bowler records:", len(bowlers))


# ============================================================
# 2. DEFINE SAMPLE-SIZE SCENARIOS
# ============================================================

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


# ============================================================
# 3. VALIDATE REQUIRED COLUMNS
# ============================================================

batter_required = [
    "striker_id",
    "striker_name",
    "matches_pressure",
    "matches_normal",
    "balls_pressure",
    "balls_normal",
    "runs_pressure",
    "runs_normal",
    "strike_rate_pressure",
    "strike_rate_normal"
]

bowler_required = [
    "bowler_id",
    "bowler_name",
    "matches_pressure",
    "matches_normal",
    "legal_balls_pressure",
    "legal_balls_normal",
    "runs_conceded_pressure",
    "runs_conceded_normal",
    "wickets_pressure",
    "wickets_normal",
    "economy_pressure",
    "economy_normal"
]

missing = [c for c in batter_required if c not in batters.columns]

if missing:
    raise ValueError(
        f"Missing batter exposure columns: {missing}"
    )

missing = [c for c in bowler_required if c not in bowlers.columns]

if missing:
    raise ValueError(
        f"Missing bowler exposure columns: {missing}"
    )


# ============================================================
# 4. CLEAN NUMERIC EXPOSURE COLUMNS
# ============================================================

batter_numeric = [
    "matches_pressure", "matches_normal",
    "balls_pressure", "balls_normal",
    "runs_pressure", "runs_normal"
]

bowler_numeric = [
    "matches_pressure", "matches_normal",
    "legal_balls_pressure", "legal_balls_normal",
    "runs_conceded_pressure", "runs_conceded_normal",
    "wickets_pressure", "wickets_normal"
]

for col in batter_numeric:
    batters[col] = pd.to_numeric(
        batters[col], errors="coerce"
    ).fillna(0)

for col in bowler_numeric:
    bowlers[col] = pd.to_numeric(
        bowlers[col], errors="coerce"
    ).fillna(0)


# ============================================================
# 5. BATTER ELIGIBILITY UNDER EACH SCENARIO
# ============================================================

for scenario, limits in SCENARIOS.items():

    match_limit = limits["matches"]
    ball_limit = limits["batter_balls"]

    pressure_ok = (
        (batters["matches_pressure"] >= match_limit)
        & (batters["balls_pressure"] >= ball_limit)
    )

    normal_ok = (
        (batters["matches_normal"] >= match_limit)
        & (batters["balls_normal"] >= ball_limit)
    )

    batters[f"{scenario}_pressure_eligible"] = pressure_ok
    batters[f"{scenario}_normal_eligible"] = normal_ok

    batters[f"{scenario}_eligible"] = (
        pressure_ok & normal_ok
    )


# ============================================================
# 6. BOWLER ELIGIBILITY UNDER EACH SCENARIO
# ============================================================

for scenario, limits in SCENARIOS.items():

    match_limit = limits["matches"]
    ball_limit = limits["bowler_balls"]

    pressure_ok = (
        (bowlers["matches_pressure"] >= match_limit)
        & (bowlers["legal_balls_pressure"] >= ball_limit)
    )

    normal_ok = (
        (bowlers["matches_normal"] >= match_limit)
        & (bowlers["legal_balls_normal"] >= ball_limit)
    )

    bowlers[f"{scenario}_pressure_eligible"] = pressure_ok
    bowlers[f"{scenario}_normal_eligible"] = normal_ok

    bowlers[f"{scenario}_eligible"] = (
        pressure_ok & normal_ok
    )


# ============================================================
# 7. SAVE PLAYER-LEVEL ELIGIBILITY RESULTS
# ============================================================

batters.to_csv(
    REPORTS / "t20i_batter_eligibility_sensitivity.csv",
    index=False
)

bowlers.to_csv(
    REPORTS / "t20i_bowler_eligibility_sensitivity.csv",
    index=False
)


# ============================================================
# 8. CREATE SCENARIO SUMMARY
# ============================================================

summary_rows = []

for scenario, limits in SCENARIOS.items():

    summary_rows.append({
        "player_type": "Batter",
        "scenario": scenario,
        "minimum_matches": limits["matches"],
        "minimum_pressure_balls": limits["batter_balls"],
        "minimum_normal_balls": limits["batter_balls"],
        "pressure_eligible": int(
            batters[f"{scenario}_pressure_eligible"].sum()
        ),
        "normal_eligible": int(
            batters[f"{scenario}_normal_eligible"].sum()
        ),
        "eligible_both_groups": int(
            batters[f"{scenario}_eligible"].sum()
        )
    })

    summary_rows.append({
        "player_type": "Bowler",
        "scenario": scenario,
        "minimum_matches": limits["matches"],
        "minimum_pressure_balls": limits["bowler_balls"],
        "minimum_normal_balls": limits["bowler_balls"],
        "pressure_eligible": int(
            bowlers[f"{scenario}_pressure_eligible"].sum()
        ),
        "normal_eligible": int(
            bowlers[f"{scenario}_normal_eligible"].sum()
        ),
        "eligible_both_groups": int(
            bowlers[f"{scenario}_eligible"].sum()
        )
    })

summary = pd.DataFrame(summary_rows)

summary.to_csv(
    REPORTS / "t20i_eligibility_scenario_summary.csv",
    index=False
)


# ============================================================
# 9. MEASURE ELIGIBILITY OVERLAP
# ============================================================

overlap_rows = []

for player_type, data, id_col in [
    ("Batter", batters, "striker_id"),
    ("Bowler", bowlers, "bowler_id")
]:

    flexible = set(
        data.loc[data["flexible_eligible"], id_col].dropna()
    )

    primary = set(
        data.loc[data["primary_eligible"], id_col].dropna()
    )

    strict = set(
        data.loc[data["strict_eligible"], id_col].dropna()
    )

    comparisons = [
        ("Flexible vs Primary", flexible, primary),
        ("Primary vs Strict", primary, strict),
        ("Flexible vs Strict", flexible, strict)
    ]

    for label, set_a, set_b in comparisons:

        union = set_a | set_b
        intersection = set_a & set_b

        jaccard = (
            len(intersection) / len(union) * 100
            if union else 0
        )

        overlap_rows.append({
            "player_type": player_type,
            "comparison": label,
            "first_population": len(set_a),
            "second_population": len(set_b),
            "common_players": len(intersection),
            "jaccard_overlap_pct": round(jaccard, 2)
        })

overlap = pd.DataFrame(overlap_rows)

overlap.to_csv(
    REPORTS / "t20i_eligibility_overlap.csv",
    index=False
)


# ============================================================
# 10. IDENTIFY PLAYERS ENTERING OR LEAVING THE PRIMARY POOL
# ============================================================

change_rows = []

for player_type, data, id_col, name_col in [
    ("Batter", batters, "striker_id", "striker_name"),
    ("Bowler", bowlers, "bowler_id", "bowler_name")
]:

    for scenario in ["flexible", "primary", "strict"]:

        eligible = data[data[f"{scenario}_eligible"]].copy()

        for _, row in eligible.iterrows():

            change_rows.append({
                "player_type": player_type,
                "player_id": row[id_col],
                "player_name": row[name_col],
                "scenario": scenario,
                "pressure_matches": row["matches_pressure"],
                "normal_matches": row["matches_normal"],
                "pressure_exposure": (
                    row["balls_pressure"]
                    if player_type == "Batter"
                    else row["legal_balls_pressure"]
                ),
                "normal_exposure": (
                    row["balls_normal"]
                    if player_type == "Batter"
                    else row["legal_balls_normal"]
                )
            })

eligibility_detail = pd.DataFrame(change_rows)

eligibility_detail.to_csv(
    REPORTS / "t20i_eligible_player_details.csv",
    index=False
)


# ============================================================
# 11. EXPOSURE DISTRIBUTION OF PRIMARY ELIGIBLE PLAYERS
# ============================================================

distribution_rows = []

for player_type, data in [
    (
        "Batter",
        batters[batters["primary_eligible"]]
    ),
    (
        "Bowler",
        bowlers[bowlers["primary_eligible"]]
    )
]:

    if player_type == "Batter":
        pressure_col = "balls_pressure"
        normal_col = "balls_normal"
    else:
        pressure_col = "legal_balls_pressure"
        normal_col = "legal_balls_normal"

    for group, col in [
        ("Pressure", pressure_col),
        ("Normal", normal_col)
    ]:

        values = data[col]

        distribution_rows.append({
            "player_type": player_type,
            "group": group,
            "eligible_players": len(values),
            "mean_exposure": round(values.mean(), 2)
            if len(values) else 0,
            "median_exposure": round(values.median(), 2)
            if len(values) else 0,
            "minimum_exposure": int(values.min())
            if len(values) else 0,
            "maximum_exposure": int(values.max())
            if len(values) else 0
        })

distribution = pd.DataFrame(distribution_rows)

distribution.to_csv(
    REPORTS / "t20i_primary_eligible_exposure_distribution.csv",
    index=False
)


# ============================================================
# 12. DISPLAY RESULTS
# ============================================================

print("\n" + "=" * 80)
print("ELIGIBILITY SCENARIO SUMMARY")
print("=" * 80)

print(summary.to_string(index=False))

print("\n" + "=" * 80)
print("ELIGIBILITY POPULATION OVERLAP")
print("=" * 80)

print(overlap.to_string(index=False))

print("\n" + "=" * 80)
print("PRIMARY ELIGIBLE PLAYER EXPOSURE")
print("=" * 80)

print(distribution.to_string(index=False))


# ============================================================
# 13. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 80)
print("STEP 64 COMPLETED")
print("=" * 80)

print("\nGenerated reports:")

for name in [
    "t20i_batter_eligibility_sensitivity.csv",
    "t20i_bowler_eligibility_sensitivity.csv",
    "t20i_eligibility_scenario_summary.csv",
    "t20i_eligibility_overlap.csv",
    "t20i_eligible_player_details.csv",
    "t20i_primary_eligible_exposure_distribution.csv"
]:
    print(" -", REPORTS / name)

print("\nNext: review sample-size sensitivity before reliability scoring.")
