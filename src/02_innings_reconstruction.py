
import pandas as pd
import numpy as np
import os
import json


# =====================================================
# 1. PROJECT PATHS
# =====================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
REPORT_DIR = os.path.join(BASE_DIR, "reports")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

INPUT_FILE = os.path.join(
    PROCESSED_DIR,
    "integrated_ball_by_ball.csv.gz"
)

OUTPUT_FILE = os.path.join(
    PROCESSED_DIR,
    "reconstructed_deliveries.csv.gz"
)

SUMMARY_FILE = os.path.join(
    PROCESSED_DIR,
    "innings_summary.csv"
)

REPORT_FILE = os.path.join(
    REPORT_DIR,
    "innings_reconstruction_report.json"
)


# =====================================================
# 2. LOAD INTEGRATED DATA
# =====================================================

print("\nLoading integrated delivery dataset...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

print("Loaded deliveries:", len(df))


# =====================================================
# 3. VALIDATE REQUIRED COLUMNS
# =====================================================

required_columns = [
    "match_id",
    "innings",
    "innings_ball_num",
    "batting_team_id",
    "bowling_team_id",
    "striker_id",
    "bowler_id",
    "runs",
    "extras1_runs",
    "extras_2_runs",
    "is_wicket",
    "extras_type",
    "match_format",
    "first_inn_revised_overs",
    "second_inn_revised_overs",
    "revised_target"
]

missing = [
    col for col in required_columns
    if col not in df.columns
]

if missing:
    raise ValueError(
        f"Missing required columns: {missing}"
    )


# =====================================================
# 4. NORMALIZE DATA TYPES
# =====================================================

numeric_columns = [
    "innings",
    "innings_ball_num",
    "runs",
    "extras1_runs",
    "extras_2_runs",
    "first_inn_revised_overs",
    "second_inn_revised_overs",
    "revised_target"
]

for col in numeric_columns:
    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    )

# Preserve missing values as zero for run calculations.

for col in ["runs", "extras1_runs", "extras_2_runs"]:
    df[col] = df[col].fillna(0)

# Normalize wicket indicators.

wicket_values = (
    df["is_wicket"]
    .fillna(0)
    .astype(str)
    .str.strip()
    .str.lower()
)

df["is_wicket"] = wicket_values.isin(
    ["1", "true", "yes", "y"]
).astype(int)


# =====================================================
# 5. NORMALIZE EXTRAS CATEGORIES
# =====================================================

extras = (
    df["extras_type"]
    .fillna("")
    .astype(str)
    .str.strip()
    .str.lower()
)

df["extras_type_clean"] = extras

# Wides, Overstep and Other are treated as
# illegal deliveries for ball-count reconstruction.
#
# Source audit:
# - wide: extra runs recorded
# - overstep: one additional run per delivery
# - other: one additional run per delivery
#
# Keep original extras categories unchanged.

illegal_extras = [
    "wide",
    "overstep",
    "other"
]

df["is_legal_ball"] = ~extras.isin(illegal_extras)

df["is_legal_ball"] = df["is_legal_ball"].astype(bool)

df["is_legal_ball"] = (
    df["is_legal_ball"].astype(int)
)

df["extras_needs_review"] = extras.isin(
    ["other", "penalty"]
)


# =====================================================
# 6. CALCULATE DELIVERY RUNS
# =====================================================

# runs = batter runs
# extras1_runs and extras_2_runs = additional runs

df["team_runs_this_delivery"] = (
    df["runs"]
    + df["extras1_runs"]
    + df["extras_2_runs"]
)


# =====================================================
# 7. IDENTIFY SUPER OVERS
# =====================================================

df["is_super_over"] = (
    df["innings"] >= 3
)


# =====================================================
# 8. SORT DELIVERY RECORDS
# =====================================================

sort_columns = [
    "match_id",
    "innings"
]

# Use available source ordering columns.

for col in [
    "overid",
    "over_ball_num",
    "innings_ball_num"
]:
    if col in df.columns and col not in sort_columns:
        sort_columns.append(col)

df = df.sort_values(
    sort_columns,
    na_position="last"
).reset_index(drop=True)


# =====================================================
# 9. CALCULATE CUMULATIVE INNINGS STATE
# =====================================================

group_columns = [
    "match_id",
    "innings"
]

grouped = df.groupby(
    group_columns,
    sort=False
)

# Runs after the current delivery.

df["cumulative_runs"] = grouped[
    "team_runs_this_delivery"
].cumsum()

# Wickets after the current delivery.

df["cumulative_wickets"] = grouped[
    "is_wicket"
].cumsum()

# Legal balls after the current delivery.

df["legal_balls_completed"] = grouped[
    "is_legal_ball"
].cumsum().astype(int)


# =====================================================
# 10. CALCULATE PRE-DELIVERY STATE
# =====================================================

# These columns represent the match situation
# immediately BEFORE the current delivery.

df["runs_before_delivery"] = (
    df["cumulative_runs"]
    - df["team_runs_this_delivery"]
)

df["wickets_before_delivery"] = (
    df["cumulative_wickets"]
    - df["is_wicket"]
)

df["legal_balls_before"] = (
    df["legal_balls_completed"]
    - df["is_legal_ball"]
)

# Explicitly retain the post-delivery values too.

df["runs_after_delivery"] = (
    df["cumulative_runs"]
)

df["wickets_after_delivery"] = (
    df["cumulative_wickets"]
)

df["legal_balls_after_delivery"] = (
    df["legal_balls_completed"]
)


# =====================================================
# 11. BUILD INNINGS SUMMARY
# =====================================================

# Include optional descriptive columns only when
# they exist in the integrated dataset.

aggregation = {
    "total_runs": ("team_runs_this_delivery", "sum"),
    "total_wickets": ("is_wicket", "sum"),
    "recorded_deliveries": ("innings_ball_num", "count"),
    "legal_balls": ("is_legal_ball", "sum"),
    "batter_runs": ("runs", "sum"),
    "extras_runs": ("extras1_runs", "sum"),
    "additional_extras": ("extras_2_runs", "sum"),
    "revised_target": ("revised_target", "first"),
    "first_inn_revised_overs": (
        "first_inn_revised_overs", "first"
    ),
    "second_inn_revised_overs": (
        "second_inn_revised_overs", "first"
    )
}

optional_columns = [
    "comp_name",
    "match_format",
    "season",
    "batting_team_id",
    "batting_team_name",
    "bowling_team_id",
    "bowling_team_name"
]

for col in optional_columns:
    if col in df.columns:
        aggregation[col] = (col, "first")

innings_summary = (
    df.groupby(
        group_columns,
        as_index=False,
        sort=False
    )
    .agg(**aggregation)
)


# =====================================================
# 12. DETERMINE SCHEDULED OVERS
# =====================================================

# Assumption:
# Revised overs are stored as numeric decimal overs.
# Example: 10.0 means 10 overs.
#
# If the source uses cricket notation such as 10.2
# to mean 10 overs and 2 balls, this conversion must
# be changed after verifying the source convention.

def get_scheduled_overs(row):

    innings = row["innings"]

    if innings >= 3:
        return 1.0

    if innings == 1:
        revised = row["first_inn_revised_overs"]

    elif innings == 2:
        revised = row["second_inn_revised_overs"]

    else:
        revised = np.nan

    if pd.notna(revised) and revised > 0:
        return float(revised)

    return 20.0


innings_summary["scheduled_overs"] = (
    innings_summary.apply(
        get_scheduled_overs,
        axis=1
    )
)

innings_summary["scheduled_balls"] = (
    innings_summary["scheduled_overs"] * 6
).round().astype(int)

innings_summary["balls_remaining"] = (
    innings_summary["scheduled_balls"]
    - innings_summary["legal_balls"]
).clip(lower=0)


# =====================================================
# 13. CALCULATE INNINGS RUN RATE
# =====================================================

innings_summary["overs_completed"] = (
    innings_summary["legal_balls"] / 6
)

innings_summary["run_rate"] = np.where(
    innings_summary["legal_balls"] > 0,
    (
        innings_summary["total_runs"]
        / innings_summary["legal_balls"] * 6
    ),
    0
)


# =====================================================
# 14. BUILD TARGET INFORMATION
# =====================================================

first_innings_scores = (
    innings_summary[
        innings_summary["innings"] == 1
    ][
        ["match_id", "total_runs"]
    ]
    .rename(
        columns={
            "total_runs": "first_innings_total"
        }
    )
)

innings_summary = innings_summary.merge(
    first_innings_scores,
    on="match_id",
    how="left",
    validate="many_to_one"
)

innings_summary["target"] = np.nan

# Regular second innings target.

second_mask = (
    innings_summary["innings"] == 2
)

innings_summary.loc[
    second_mask,
    "target"
] = (
    innings_summary.loc[
        second_mask,
        "first_innings_total"
    ] + 1
)

# Revised target overrides the standard target.

revised_mask = (
    second_mask
    & innings_summary["revised_target"].notna()
)

innings_summary.loc[
    revised_mask,
    "target"
] = innings_summary.loc[
    revised_mask,
    "revised_target"
]

# Super Over target comes from the immediately
# preceding innings in the same match.

for match_id, indexes in innings_summary.groupby(
    "match_id"
).groups.items():

    match_rows = (
        innings_summary.loc[indexes]
        .sort_values("innings")
    )

    previous_score = None

    for idx, row in match_rows.iterrows():

        if row["innings"] >= 3:

            if previous_score is not None:

                innings_summary.loc[
                    idx,
                    "target"
                ] = previous_score + 1

        previous_score = row["total_runs"]


# =====================================================
# 15. ATTACH INNINGS INFORMATION TO DELIVERIES
# =====================================================

target_columns = [
    "match_id",
    "innings",
    "scheduled_overs",
    "scheduled_balls",
    "target"
]

df = df.merge(
    innings_summary[target_columns],
    on=["match_id", "innings"],
    how="left",
    validate="many_to_one"
)


# =====================================================
# 16. CALCULATE PRE- AND POST-DELIVERY BALLS
# =====================================================

# Before the current delivery.

df["balls_remaining_before"] = (
    df["scheduled_balls"]
    - df["legal_balls_before"]
).clip(lower=0)

# After the current delivery.

df["balls_remaining"] = (
    df["scheduled_balls"]
    - df["legal_balls_completed"]
).clip(lower=0)


# =====================================================
# 17. CALCULATE RUNS REQUIRED
# =====================================================

df["runs_required_before"] = np.nan

df["runs_required"] = np.nan

chase_mask = (
    df["innings"].ge(2)
    & df["target"].notna()
)

# Runs required before facing the delivery.

df.loc[
    chase_mask,
    "runs_required_before"
] = (
    df.loc[chase_mask, "target"]
    - df.loc[chase_mask, "runs_before_delivery"]
).clip(lower=0)

# Runs required after the delivery.

df.loc[
    chase_mask,
    "runs_required"
] = (
    df.loc[chase_mask, "target"]
    - df.loc[chase_mask, "cumulative_runs"]
).clip(lower=0)


# =====================================================
# 18. CALCULATE CURRENT RUN RATE
# =====================================================

df["current_run_rate_before"] = np.where(
    df["legal_balls_before"] > 0,
    (
        df["runs_before_delivery"]
        / df["legal_balls_before"] * 6
    ),
    0
)

df["current_run_rate"] = np.where(
    df["legal_balls_completed"] > 0,
    (
        df["cumulative_runs"]
        / df["legal_balls_completed"] * 6
    ),
    0
)


# =====================================================
# 19. CALCULATE REQUIRED RUN RATE
# =====================================================

df["required_run_rate_before"] = np.nan

df["required_run_rate"] = np.nan

rrr_before_mask = (
    chase_mask
    & df["balls_remaining_before"].gt(0)
)

df.loc[
    rrr_before_mask,
    "required_run_rate_before"
] = (
    df.loc[
        rrr_before_mask,
        "runs_required_before"
    ]
    / df.loc[
        rrr_before_mask,
        "balls_remaining_before"
    ]
) * 6

rrr_after_mask = (
    chase_mask
    & df["balls_remaining"].gt(0)
)

df.loc[
    rrr_after_mask,
    "required_run_rate"
] = (
    df.loc[
        rrr_after_mask,
        "runs_required"
    ]
    / df.loc[
        rrr_after_mask,
        "balls_remaining"
    ]
) * 6


# =====================================================
# 20. IDENTIFY INNINGS PHASE
# =====================================================

# Standard T20 boundaries:
# Powerplay: first 6 overs.
# Middle: overs 7 to 15.
# Death: overs 16 to 20.
#
# For shortened innings, these boundaries are
# proportionally adjusted as a descriptive heuristic.
# They are not a replacement for official playing rules.

scheduled_balls = df["scheduled_balls"].fillna(120)

powerplay_limit = np.minimum(
    36,
    np.ceil(scheduled_balls * 0.30)
)

middle_limit = np.minimum(
    90,
    np.ceil(scheduled_balls * 0.75)
)

legal_before = df["legal_balls_before"]

df["innings_phase"] = np.select(
    [
        legal_before < powerplay_limit,
        legal_before < middle_limit,
        legal_before >= middle_limit
    ],
    [
        "Powerplay",
        "Middle",
        "Death"
    ],
    default="Unknown"
)


# =====================================================
# 21. IDENTIFY WICKETS IN HAND
# =====================================================

# Wickets in hand before the current delivery.

df["wickets_in_hand_before"] = (
    10 - df["wickets_before_delivery"]
).clip(lower=0)

# Wickets in hand after the current delivery.

df["wickets_in_hand"] = (
    10 - df["cumulative_wickets"]
).clip(lower=0)


# =====================================================
# 22. IDENTIFY PRESSURE CONTEXT
# =====================================================

# Pressure indicators are based on the situation
# BEFORE the current delivery.
#
# These are descriptive signals, not the final
# player-reliability scoring model.

df["high_required_rate"] = (
    df["required_run_rate_before"] >= 10
)

df["low_wickets_remaining"] = (
    df["wickets_in_hand_before"] <= 3
)

df["death_overs"] = (
    df["innings_phase"] == "Death"
)

df["high_pressure_signals"] = (
    df["high_required_rate"].fillna(False).astype(int)
    + df["low_wickets_remaining"].astype(int)
    + df["death_overs"].astype(int)
)

df["is_high_pressure_delivery"] = (
    df["high_pressure_signals"] >= 2
)


# =====================================================
# 23. SAVE RECONSTRUCTED DATA
# =====================================================

df.to_csv(
    OUTPUT_FILE,
    index=False,
    compression="gzip"
)

innings_summary.to_csv(
    SUMMARY_FILE,
    index=False
)


# =====================================================
# 24. DATA VALIDATION
# =====================================================

duplicate_delivery_mask = df.duplicated(
    subset=[
        "match_id",
        "innings",
        "innings_ball_num"
    ],
    keep=False
)

negative_runs_mask = (
    df["team_runs_this_delivery"] < 0
)

invalid_innings_mask = (
    df["innings"].isna()
    | df["innings"].le(0)
)

legal_balls_exceed_mask = (
    innings_summary["legal_balls"]
    > innings_summary["scheduled_balls"]
)

missing_target_mask = (
    (innings_summary["innings"] == 2)
    & innings_summary["target"].isna()
)

report = {

    "total_delivery_records": int(len(df)),

    "total_innings": int(len(innings_summary)),

    "total_matches": int(df["match_id"].nunique()),

    "total_legal_balls": int(
        df["is_legal_ball"].sum()
    ),

    "total_runs_reconstructed": int(
        df["team_runs_this_delivery"].sum()
    ),

    "total_batter_runs": int(
        df["runs"].sum()
    ),

    "total_extras_runs": int(
        df["extras1_runs"].sum()
        + df["extras_2_runs"].sum()
    ),

    "total_wickets": int(
        df["is_wicket"].sum()
    ),

    "super_over_delivery_records": int(
        df["is_super_over"].sum()
    ),

    "deliveries_needing_extras_review": int(
        df["extras_needs_review"].sum()
    ),

    "duplicate_delivery_records": int(
        duplicate_delivery_mask.sum()
    ),

    "negative_run_deliveries": int(
        negative_runs_mask.sum()
    ),

    "invalid_innings_records": int(
        invalid_innings_mask.sum()
    ),

    "innings_exceeding_scheduled_balls": int(
        legal_balls_exceed_mask.sum()
    ),

    "missing_target_in_second_innings": int(
        missing_target_mask.sum()
    ),

    "negative_balls_remaining": int(
        (df["balls_remaining"] < 0).sum()
    ),

    "missing_cumulative_scores": int(
        df["cumulative_runs"].isna().sum()
    ),

    "missing_pre_delivery_pressure_values": int(
        df.loc[
            chase_mask,
            "runs_required_before"
        ].isna().sum()
    ),

    "high_pressure_delivery_records": int(
        df["is_high_pressure_delivery"].sum()
    ),

    "revised_overs_conversion_assumption": (
        "Numeric revised overs are treated as decimal overs "
        "and multiplied by 6."
    )

}


# Check that reconstructed team runs equal
# batter runs plus both extras columns.

report["run_reconciliation_passed"] = (
    report["total_runs_reconstructed"]
    == (
        report["total_batter_runs"]
        + report["total_extras_runs"]
    )
)

report["has_duplicate_delivery_records"] = (
    report["duplicate_delivery_records"] > 0
)

report["has_innings_exceeding_scheduled_balls"] = (
    report["innings_exceeding_scheduled_balls"] > 0
)


with open(REPORT_FILE, "w") as f:

    json.dump(
        report,
        f,
        indent=4
    )


# =====================================================
# 25. DISPLAY RESULTS
# =====================================================

print("\n" + "=" * 65)

print("INNINGS RECONSTRUCTION REPORT")

print("=" * 65)

for key, value in report.items():

    print(f"{key}: {value}")


print("\nINNINGS SUMMARY SAMPLE")

display_columns = [
    "match_id",
    "innings",
    "total_runs",
    "total_wickets",
    "legal_balls",
    "scheduled_overs",
    "run_rate",
    "target"
]

if "batting_team_name" in innings_summary.columns:
    display_columns.insert(
        2,
        "batting_team_name"
    )

print(
    innings_summary[
        display_columns
    ].head(10).to_string(index=False)
)


print("\nPRESSURE CONTEXT SAMPLE")

pressure_columns = [
    "match_id",
    "innings",
    "striker_id",
    "runs_before_delivery",
    "wickets_before_delivery",
    "legal_balls_before",
    "runs_required_before",
    "balls_remaining_before",
    "required_run_rate_before",
    "innings_phase",
    "high_pressure_signals"
]

print(
    df[
        pressure_columns
    ].head(10).to_string(index=False)
)


print("\n" + "=" * 65)

print("RECONSTRUCTION COMPLETED")

print("=" * 65)

print("\nDelivery output:", OUTPUT_FILE)

print("Innings summary:", SUMMARY_FILE)

print("Validation report:", REPORT_FILE)
