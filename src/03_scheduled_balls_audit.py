
import pandas as pd
import os


# =====================================================
# 1. PROJECT PATHS
# =====================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(REPORT_DIR, exist_ok=True)

DELIVERY_FILE = os.path.join(
    PROCESSED_DIR,
    "reconstructed_deliveries.csv.gz"
)

SUMMARY_FILE = os.path.join(
    PROCESSED_DIR,
    "innings_summary.csv"
)

OUTPUT_FILE = os.path.join(
    REPORT_DIR,
    "innings_exceeding_scheduled_balls.csv"
)

DETAIL_FILE = os.path.join(
    REPORT_DIR,
    "excess_delivery_details.csv"
)

EXTRAS_FILE = os.path.join(
    REPORT_DIR,
    "excess_delivery_extras_summary.csv"
)


# =====================================================
# 2. LOAD DATA
# =====================================================

print("\nLoading reconstructed data...")

df = pd.read_csv(
    DELIVERY_FILE,
    low_memory=False
)

summary = pd.read_csv(
    SUMMARY_FILE,
    low_memory=False
)

print("Deliveries:", len(df))
print("Innings:", len(summary))


# =====================================================
# 3. IDENTIFY INNINGS EXCEEDING SCHEDULE
# =====================================================

summary["excess_legal_balls"] = (
    summary["legal_balls"]
    - summary["scheduled_balls"]
)

problem_innings = summary[
    summary["excess_legal_balls"] > 0
].copy()

problem_innings = problem_innings.sort_values(
    "excess_legal_balls",
    ascending=False
)

print("\n" + "=" * 65)
print("SCHEDULED BALLS AUDIT")
print("=" * 65)

print(
    "Innings exceeding scheduled balls:",
    len(problem_innings)
)

print(
    "Total excess legal balls:",
    int(problem_innings["excess_legal_balls"].sum())
)


# =====================================================
# 4. DISPLAY PROBLEM INNINGS
# =====================================================

columns = [
    "match_id",
    "innings",
    "legal_balls",
    "scheduled_overs",
    "scheduled_balls",
    "excess_legal_balls"
]

for col in [
    "comp_name",
    "season",
    "match_format",
    "batting_team_name"
]:
    if col in problem_innings.columns:
        columns.append(col)

print("\nPROBLEM INNINGS SAMPLE")

print(
    problem_innings[columns]
    .head(30)
    .to_string(index=False)
)


# =====================================================
# 5. SAVE PROBLEM INNINGS
# =====================================================

problem_innings.to_csv(
    OUTPUT_FILE,
    index=False
)


# =====================================================
# 6. GET DELIVERY DETAILS
# =====================================================

problem_keys = problem_innings[
    ["match_id", "innings"]
].drop_duplicates()

details = df.merge(
    problem_keys,
    on=["match_id", "innings"],
    how="inner"
)

details = details[
    details["is_legal_ball"] == 1
].copy()

# Keep the final few legal deliveries of each
# affected innings to inspect where the excess occurs.

details["legal_delivery_position"] = (
    details["legal_balls_completed"]
)

details = details.merge(
    problem_innings[
        [
            "match_id",
            "innings",
            "excess_legal_balls"
        ]
    ],
    on=["match_id", "innings"],
    how="left"
)

details["near_innings_end"] = (
    details["legal_delivery_position"]
    >= details["scheduled_balls"] - 5
)

detail_columns = [
    "match_id",
    "innings",
    "overid",
    "over_ball_num",
    "innings_ball_num",
    "legal_delivery_position",
    "extras_type",
    "extras_type_clean",
    "extras1_runs",
    "extras_2_runs",
    "runs",
    "is_wicket",
    "delivery_style",
    "scheduled_balls",
    "legal_balls",
    "excess_legal_balls"
]

detail_columns = [
    col for col in detail_columns
    if col in details.columns
]

details = details[
    details["near_innings_end"]
]

details.to_csv(
    DETAIL_FILE,
    index=False
)


# =====================================================
# 7. EXTRAS CATEGORY SUMMARY
# =====================================================

extras_summary = (
    df[
        df["match_id"].isin(
            problem_innings["match_id"]
        )
    ]
    .groupby(
        "extras_type_clean",
        dropna=False
    )
    .agg(
        deliveries=("match_id", "size"),
        legal_deliveries=("is_legal_ball", "sum"),
        total_runs=("team_runs_this_delivery", "sum")
    )
    .reset_index()
)

extras_summary.to_csv(
    EXTRAS_FILE,
    index=False
)


# =====================================================
# 8. DISPLAY EXTRAS SUMMARY
# =====================================================

print("\nEXTRAS CATEGORY SUMMARY")

print(
    extras_summary.to_string(index=False)
)


# =====================================================
# 9. DISPLAY FINAL DELIVERY DETAILS
# =====================================================

print("\nFINAL LEGAL DELIVERIES OF AFFECTED INNINGS")

print(
    details[detail_columns]
    .head(60)
    .to_string(index=False)
)


# =====================================================
# 10. SAVE REPORT
# =====================================================

print("\n" + "=" * 65)
print("AUDIT COMPLETED")
print("=" * 65)

print("\nProblem innings:", OUTPUT_FILE)
print("Delivery details:", DETAIL_FILE)
print("Extras summary:", EXTRAS_FILE)
