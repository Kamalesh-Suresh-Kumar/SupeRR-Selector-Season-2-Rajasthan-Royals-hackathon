
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

OVER_REPORT = os.path.join(
    REPORT_DIR,
    "affected_innings_over_summary.csv"
)

IPL_REPORT = os.path.join(
    REPORT_DIR,
    "ipl_affected_innings_over_summary.csv"
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


# =====================================================
# 3. IDENTIFY AFFECTED INNINGS
# =====================================================

summary["excess_legal_balls"] = (
    summary["legal_balls"]
    - summary["scheduled_balls"]
)

problem = summary[
    summary["excess_legal_balls"] > 0
].copy()

keys = problem[
    ["match_id", "innings"]
].drop_duplicates()


# =====================================================
# 4. FILTER ALL DELIVERIES OF AFFECTED INNINGS
# =====================================================

affected = df.merge(
    keys,
    on=["match_id", "innings"],
    how="inner",
    validate="many_to_one"
)

print("Affected delivery records:", len(affected))


# =====================================================
# 5. BUILD OVER-BY-OVER SUMMARY
# =====================================================

over_summary = (
    affected.groupby(
        ["match_id", "innings", "overid"],
        dropna=False
    )
    .agg(
        recorded_deliveries=("overid", "size"),
        legal_deliveries=("is_legal_ball", "sum"),
        first_innings_ball=("innings_ball_num", "min"),
        last_innings_ball=("innings_ball_num", "max"),
        first_over_ball=("over_ball_num", "min"),
        last_over_ball=("over_ball_num", "max"),
        batter_runs=("runs", "sum"),
        extras1=("extras1_runs", "sum"),
        extras2=("extras_2_runs", "sum"),
        wickets=("is_wicket", "sum"),
        first_legal_position=("legal_balls_completed", "min"),
        last_legal_position=("legal_balls_completed", "max")
    )
    .reset_index()
)

metadata_columns = [
    "match_id",
    "innings",
    "comp_name",
    "match_format",
    "season",
    "batting_team_name",
    "scheduled_balls",
    "legal_balls",
    "excess_legal_balls"
]

metadata = problem[
    [
        col for col in metadata_columns
        if col in problem.columns
    ]
].drop_duplicates(
    ["match_id", "innings"]
)

over_summary = over_summary.merge(
    metadata,
    on=["match_id", "innings"],
    how="left",
    validate="many_to_one"
)

over_summary = over_summary.sort_values(
    ["match_id", "innings", "overid"]
)

over_summary.to_csv(
    OVER_REPORT,
    index=False
)


# =====================================================
# 6. BUILD IPL-ONLY REPORT
# =====================================================

ipl_over_summary = over_summary[
    over_summary["comp_name"].astype(str).str.contains(
        "IPL",
        case=False,
        na=False
    )
].copy()

ipl_over_summary.to_csv(
    IPL_REPORT,
    index=False
)


# =====================================================
# 7. DISPLAY OVER NUMBERING PATTERN
# =====================================================

print("\n" + "=" * 65)
print("OVER NUMBERING AUDIT")
print("=" * 65)

print("\nMaximum overid distribution:")

max_over = (
    over_summary.groupby(
        ["match_id", "innings"]
    )["overid"]
    .max()
    .value_counts()
    .sort_index()
)

print(max_over.to_string())


print("\nAffected innings with overid 20:")

print(
    over_summary[
        over_summary["overid"] == 20
    ][
        [
            "match_id",
            "innings",
            "overid",
            "recorded_deliveries",
            "legal_deliveries",
            "first_innings_ball",
            "last_innings_ball",
            "first_over_ball",
            "last_over_ball",
            "match_format",
            "comp_name"
        ]
    ].to_string(index=False)
)


# =====================================================
# 8. DISPLAY IPL SAMPLE
# =====================================================

print("\nIPL OVER SUMMARY SAMPLE")

print(
    ipl_over_summary[
        [
            "match_id",
            "innings",
            "overid",
            "recorded_deliveries",
            "legal_deliveries",
            "first_innings_ball",
            "last_innings_ball",
            "first_over_ball",
            "last_over_ball",
            "excess_legal_balls"
        ]
    ].head(60).to_string(index=False)
)


# =====================================================
# 9. FINAL OUTPUT
# =====================================================

print("\n" + "=" * 65)
print("OVER NUMBERING AUDIT COMPLETED")
print("=" * 65)

print("\nAll affected innings:", OVER_REPORT)
print("IPL affected innings:", IPL_REPORT)
