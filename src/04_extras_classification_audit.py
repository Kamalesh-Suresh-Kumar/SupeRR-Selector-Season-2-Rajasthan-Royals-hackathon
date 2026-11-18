
import pandas as pd
import os

# ==========================================
# 1. PATHS
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

INPUT_FILE = os.path.join(
    DATA_DIR,
    "reconstructed_deliveries.csv.gz"
)

os.makedirs(REPORT_DIR, exist_ok=True)

# ==========================================
# 2. LOAD DATA
# ==========================================

print("\nLoading reconstructed deliveries...")

df = pd.read_csv(
    INPUT_FILE,
    low_memory=False
)

# ==========================================
# 3. NORMALIZE EXTRAS
# ==========================================

df["extras_type_clean"] = (
    df["extras_type"]
    .fillna("No extras")
    .astype(str)
    .str.strip()
)

# ==========================================
# 4. EXTRAS CATEGORY SUMMARY
# ==========================================

print("\nEXTRAS CATEGORY SUMMARY")
print("=" * 75)

summary = (

    df.groupby(
        "extras_type_clean",
        dropna=False
    )

    .agg(

        deliveries=("match_id", "size"),

        batter_runs=("runs", "sum"),

        extras1_runs=("extras1_runs", "sum"),

        extras2_runs=("extras_2_runs", "sum"),

        total_runs=("team_runs_this_delivery", "sum"),

        legal_balls=("is_legal_ball", "sum"),

        wickets=("is_wicket", "sum")

    )

    .reset_index()

)

print(summary.to_string(index=False))

summary.to_csv(
    os.path.join(REPORT_DIR, "extras_category_summary.csv"),
    index=False
)

# ==========================================
# 5. DETAILED EXTRAS COMBINATIONS
# ==========================================

print("\nDETAILED EXTRAS COMBINATIONS")
print("=" * 75)

combinations = (

    df.groupby(
        [
            "extras_type_clean",
            "runs",
            "extras1_runs",
            "extras_2_runs",
            "is_wicket"
        ],
        dropna=False
    )

    .size()

    .reset_index(name="frequency")

    .sort_values(
        ["extras_type_clean", "frequency"],
        ascending=[True, False]
    )

)

print(combinations.to_string(index=False))

combinations.to_csv(
    os.path.join(REPORT_DIR, "extras_combinations.csv"),
    index=False
)

# ==========================================
# 6. INSPECT OTHER AND PENALTY
# ==========================================

print("\nOTHER AND PENALTY RECORDS")
print("=" * 75)

review = df[
    df["extras_type_clean"].str.lower().isin(
        ["other", "penalty"]
    )
]

columns = [
    "match_id",
    "innings",
    "overid",
    "over_ball_num",
    "innings_ball_num",
    "striker_name",
    "bowler_name",
    "runs",
    "extras1_runs",
    "extras_2_runs",
    "extras_type",
    "is_legal_ball",
    "is_wicket",
    "dismissal_type"
]

print(
    review[columns].to_string(index=False)
)

review[columns].to_csv(
    os.path.join(REPORT_DIR, "extras_records_for_review.csv"),
    index=False
)

# ==========================================
# 7. DELIVERY NUMBER SEQUENCE AUDIT
# ==========================================

print("\nDELIVERY NUMBER SEQUENCE AUDIT")
print("=" * 75)

sequence = (

    df.groupby(
        ["match_id", "innings", "overid"]
    )

    .agg(

        delivery_records=("innings_ball_num", "count"),

        legal_balls=("is_legal_ball", "sum"),

        unique_ball_numbers=("over_ball_num", "nunique")

    )

    .reset_index()

)

print("Total over records:", len(sequence))

print(
    "Overs with more than 6 legal balls:",
    int((sequence["legal_balls"] > 6).sum())
)

print(
    "Overs with zero legal balls:",
    int((sequence["legal_balls"] == 0).sum())
)

sequence.to_csv(
    os.path.join(REPORT_DIR, "over_sequence_audit.csv"),
    index=False
)

print("\nEXTRAS AUDIT COMPLETED!")

print(
    "\nReports saved inside:",
    REPORT_DIR
)
