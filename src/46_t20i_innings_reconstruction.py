
from pathlib import Path
import pandas as pd
import numpy as np
import json

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

# ---------------------------------------------------------
# 1. LOAD SOURCE FILES
# ---------------------------------------------------------

balls = pd.read_csv(DATA / "ball_by_ball.csv", low_memory=False)
matches = pd.read_csv(DATA / "matches.csv", low_memory=False)
competitions = pd.read_csv(DATA / "competitions.csv", low_memory=False)

# ---------------------------------------------------------
# 2. FILTER T20I MATCHES
# ---------------------------------------------------------

t20i_comp_ids = set(
    competitions.loc[
        competitions["match_format"].astype(str).str.upper() == "T20I",
        "comp_id"
    ]
)

matches["match_id"] = pd.to_numeric(
    matches["match_id"], errors="coerce"
)

balls["match_id"] = pd.to_numeric(
    balls["match_id"], errors="coerce"
)

t20i_matches = matches[
    matches["comp_id"].isin(t20i_comp_ids)
].copy()

t20i_ids = set(t20i_matches["match_id"].dropna())

df = balls[
    balls["match_id"].isin(t20i_ids)
].copy()

# Main analysis uses only the first two innings.
for col in [
    "innings", "overid", "over_ball_num",
    "innings_ball_num", "runs", "extras1_runs",
    "extras_2_runs"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df[df["innings"].isin([1, 2])].copy()

# ---------------------------------------------------------
# 3. NORMALIZE EXTRAS AND WICKETS
# ---------------------------------------------------------

df["extras_clean"] = (
    df["extras_type"]
    .fillna("none")
    .astype(str)
    .str.strip()
    .str.lower()
)

def parse_bool(series):
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin(["true", "1", "1.0", "yes"])
    )

df["is_wicket_clean"] = parse_bool(df["is_wicket"])

df["batter_runs"] = df["runs"].fillna(0)
df["extras1"] = df["extras1_runs"].fillna(0)
df["extras2"] = df["extras_2_runs"].fillna(0)

df["team_runs"] = (
    df["batter_runs"] + df["extras1"] + df["extras2"]
)

# ---------------------------------------------------------
# 4. IDENTIFY UNRESOLVED RECORDS
# ---------------------------------------------------------

df["is_other"] = df["extras_clean"].eq("other")

df["is_penalty"] = df["extras_clean"].eq("penalty")

df["is_unclassified_extras"] = (
    df["extras_clean"].eq("none")
    & (
        df["extras1"].ne(0)
        | df["extras2"].ne(0)
    )
)

print("\n" + "=" * 75)
print("STEP 46: T20I INNINGS RECONSTRUCTION")
print("=" * 75)

print("T20I delivery records, innings 1 and 2:", len(df))
print("Other records:", int(df["is_other"].sum()))
print("Penalty records:", int(df["is_penalty"].sum()))
print(
    "Unclassified extras records:",
    int(df["is_unclassified_extras"].sum())
)

# ---------------------------------------------------------
# 5. SCENARIO RECONSTRUCTION FUNCTION
# ---------------------------------------------------------

def reconstruct(other_is_legal, unknown_none_is_legal, scenario_name):

    x = df.copy()

    # Ordinary delivery is legal unless explicitly classified
    # as an illegal delivery or non-delivery event.
    x["is_legal_ball"] = True

    x.loc[
        x["extras_clean"].isin(["wide", "overstep"]),
        "is_legal_ball"
    ] = False

    # Test the unresolved "other" category.
    x.loc[
        x["is_other"],
        "is_legal_ball"
    ] = bool(other_is_legal)

    # Test the two records whose extras type is "none"
    # despite a non-zero extras value.
    x.loc[
        x["is_unclassified_extras"],
        "is_legal_ball"
    ] = bool(unknown_none_is_legal)

    # A penalty event is not a delivery.
    x.loc[
        x["is_penalty"],
        "is_legal_ball"
    ] = False

    x["is_counted_delivery"] = ~x["is_penalty"]

    x["legal_ball_count"] = (
        x["is_legal_ball"] & x["is_counted_delivery"]
    ).astype(int)

    x["illegal_delivery_count"] = (
        (~x["is_legal_ball"]) & x["is_counted_delivery"]
    ).astype(int)

    # Penalty runs remain part of the team score.
    # The penalty event is excluded from batter/bowler delivery counts.
    x["team_runs_for_innings"] = x["team_runs"]

    # Sort by recorded sequence, not over_ball_num as a legal-ball count.
    x = x.sort_values(
        [
            "match_id", "innings",
            "innings_ball_num", "overid", "over_ball_num"
        ],
        kind="stable"
    ).copy()

    group_keys = ["match_id", "innings"]

    x["legal_balls_before"] = (
        x.groupby(group_keys)["legal_ball_count"].cumsum()
        - x["legal_ball_count"]
    )

    x["cumulative_legal_balls"] = (
        x.groupby(group_keys)["legal_ball_count"].cumsum()
    )

    x["cumulative_team_runs"] = (
        x.groupby(group_keys)["team_runs_for_innings"].cumsum()
    )

    x["cumulative_wickets"] = (
        x.groupby(group_keys)["is_wicket_clean"].cumsum()
    )

    summary = x.groupby(
        ["match_id", "innings"],
        as_index=False
    ).agg(
        delivery_records=("is_counted_delivery", "sum"),
        legal_balls=("legal_ball_count", "sum"),
        illegal_deliveries=("illegal_delivery_count", "sum"),
        team_runs=("team_runs_for_innings", "sum"),
        batter_runs=("batter_runs", "sum"),
        extras1_runs=("extras1", "sum"),
        extras2_runs=("extras2", "sum"),
        wickets=("is_wicket_clean", "sum"),
        penalty_records=("is_penalty", "sum"),
        other_records=("is_other", "sum"),
        unclassified_extras_records=("is_unclassified_extras", "sum"),
    )

    summary["scenario"] = scenario_name

    # Add match metadata.
    metadata_columns = [
        "match_id",
        "match_date",
        "stage",
        "venue_country",
        "home_team",
        "away_team",
        "result",
        "first_inn_revised_overs",
        "second_inn_revised_overs",
        "revised_target",
    ]

    metadata_columns = [
        c for c in metadata_columns if c in t20i_matches.columns
    ]

    summary = summary.merge(
        t20i_matches[metadata_columns].drop_duplicates("match_id"),
        on="match_id",
        how="left"
    )

    return x, summary


# ---------------------------------------------------------
# 6. RUN FOUR SCENARIOS
# ---------------------------------------------------------

scenarios = [
    {
        "name": "A_primary_other_illegal_unknown_legal",
        "other_is_legal": False,
        "unknown_none_is_legal": True,
    },
    {
        "name": "B_other_legal_unknown_legal",
        "other_is_legal": True,
        "unknown_none_is_legal": True,
    },
    {
        "name": "C_other_illegal_unknown_illegal",
        "other_is_legal": False,
        "unknown_none_is_legal": False,
    },
    {
        "name": "D_other_legal_unknown_illegal",
        "other_is_legal": True,
        "unknown_none_is_legal": False,
    },
]

all_summaries = []
primary_deliveries = None
primary_summary = None

for scenario in scenarios:
    reconstructed, summary = reconstruct(
        scenario["other_is_legal"],
        scenario["unknown_none_is_legal"],
        scenario["name"]
    )

    all_summaries.append(summary)

    if scenario["name"].startswith("A_"):
        primary_deliveries = reconstructed
        primary_summary = summary

    print("\nScenario:", scenario["name"])
    print("Innings reconstructed:", len(summary))
    print("Total team runs:", int(summary["team_runs"].sum()))
    print("Total legal balls:", int(summary["legal_balls"].sum()))
    print("Total illegal deliveries:", int(summary["illegal_deliveries"].sum()))

# ---------------------------------------------------------
# 7. COMBINE SCENARIO RESULTS
# ---------------------------------------------------------

scenario_summary = pd.concat(
    all_summaries,
    ignore_index=True
)

scenario_summary.to_csv(
    REPORTS / "t20i_reconstruction_scenario_summary.csv",
    index=False
)

# Compare totals across scenarios.
scenario_comparison = scenario_summary.groupby(
    "scenario",
    as_index=False
).agg(
    innings=("match_id", "size"),
    matches=("match_id", "nunique"),
    legal_balls=("legal_balls", "sum"),
    illegal_deliveries=("illegal_deliveries", "sum"),
    team_runs=("team_runs", "sum"),
    wickets=("wickets", "sum"),
)

print("\n" + "=" * 75)
print("SCENARIO COMPARISON")
print("=" * 75)

print(scenario_comparison.to_string(index=False))

scenario_comparison.to_csv(
    REPORTS / "t20i_reconstruction_scenario_comparison.csv",
    index=False
)

# ---------------------------------------------------------
# 8. SAVE PRIMARY RECONSTRUCTION
# ---------------------------------------------------------

primary_deliveries.to_csv(
    REPORTS / "t20i_reconstructed_deliveries.csv.gz",
    index=False,
    compression="gzip"
)

primary_summary.to_csv(
    REPORTS / "t20i_reconstructed_innings_summary.csv",
    index=False
)

# ---------------------------------------------------------
# 9. INNINGS VALIDATION
# ---------------------------------------------------------

print("\n" + "=" * 75)
print("PRIMARY SCENARIO VALIDATION")
print("=" * 75)

print("Delivery rows:", len(primary_deliveries))
print("Innings summaries:", len(primary_summary))

print(
    "Run reconciliation:",
    int(primary_deliveries["team_runs"].sum()),
    "==",
    int(primary_summary["team_runs"].sum())
)

print(
    "Legal + illegal delivery reconciliation:",
    int(
        primary_deliveries["legal_ball_count"].sum()
        + primary_deliveries["illegal_delivery_count"].sum()
    ),
    "==",
    int(primary_deliveries["is_counted_delivery"].sum())
)

print(
    "Penalty events retained:",
    int(primary_deliveries["is_penalty"].sum())
)

print(
    "Penalty runs retained:",
    int(
        primary_deliveries.loc[
            primary_deliveries["is_penalty"],
            "team_runs_for_innings"
        ].sum()
    )
)

# ---------------------------------------------------------
# 10. INNINGS WITH MORE THAN 120 LEGAL BALLS
# ---------------------------------------------------------

long_innings = primary_summary[
    primary_summary["legal_balls"] > 120
].copy()

print("\nInnings with more than 120 legal balls:")
print(len(long_innings))

if len(long_innings):
    print(
        long_innings[
            [
                "match_id", "innings",
                "legal_balls", "team_runs", "wickets"
            ]
        ].to_string(index=False)
    )

long_innings.to_csv(
    REPORTS / "t20i_innings_over_120_legal_balls.csv",
    index=False
)

# ---------------------------------------------------------
# 11. MATCHES WITH NO DELIVERY DATA
# ---------------------------------------------------------

available_match_ids = set(primary_summary["match_id"].dropna())

matches_without_deliveries = t20i_matches[
    ~t20i_matches["match_id"].isin(available_match_ids)
].copy()

print("\nMatches without innings delivery data:",
      len(matches_without_deliveries))

# ---------------------------------------------------------
# 12. FINAL SUMMARY
# ---------------------------------------------------------

final_summary = {
    "primary_scenario": scenarios[0]["name"],
    "matches_with_delivery_data": int(
        primary_summary["match_id"].nunique()
    ),
    "innings_reconstructed": int(len(primary_summary)),
    "delivery_records": int(
        primary_deliveries["is_counted_delivery"].sum()
    ),
    "penalty_events": int(
        primary_deliveries["is_penalty"].sum()
    ),
    "legal_balls": int(
        primary_deliveries["legal_ball_count"].sum()
    ),
    "illegal_deliveries": int(
        primary_deliveries["illegal_delivery_count"].sum()
    ),
    "team_runs": int(
        primary_deliveries["team_runs_for_innings"].sum()
    ),
    "wickets": int(
        primary_deliveries["is_wicket_clean"].sum()
    ),
    "matches_without_delivery_data": int(
        len(matches_without_deliveries)
    ),
    "innings_over_120_legal_balls": int(len(long_innings)),
}

with open(
    REPORTS / "t20i_reconstruction_summary.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(final_summary, f, indent=4)

print("\n" + "=" * 75)
print("STEP 46 COMPLETED")
print("=" * 75)
print(json.dumps(final_summary, indent=4))

print("\nFiles saved in:", REPORTS)
