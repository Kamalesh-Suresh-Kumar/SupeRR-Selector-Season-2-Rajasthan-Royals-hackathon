
import pandas as pd
import numpy as np
import os
import json

# ==========================================
# 1. PATHS
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

DATA_DIR = os.path.join(BASE_DIR, "data", "processed")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

os.makedirs(REPORT_DIR, exist_ok=True)

# ==========================================
# 2. LOAD DATA
# ==========================================

print("\nLoading reconstructed dataset...")

df = pd.read_csv(
    os.path.join(DATA_DIR, "reconstructed_deliveries.csv.gz"),
    low_memory=False
)

matches = pd.read_csv(
    os.path.join(RAW_DIR, "matches.csv")
)

print("Deliveries:", len(df))
print("Matches:", len(matches))

# ==========================================
# 3. EXTRAS CATEGORY AUDIT
# ==========================================

print("\nEXTRAS CATEGORY DISTRIBUTION")
print("=" * 60)

extras_audit = (

    df["extras_type"]

    .fillna("No extras")

    .value_counts(dropna=False)

    .rename_axis("extras_type")

    .reset_index(name="delivery_count")

)

print(extras_audit.to_string(index=False))

# ==========================================
# 4. RUN COMPONENT AUDIT
# ==========================================

print("\nRUN COMPONENT AUDIT")
print("=" * 60)

run_audit = {

    "batter_runs": int(df["runs"].fillna(0).sum()),

    "extras1_runs": int(
        df["extras1_runs"].fillna(0).sum()
    ),

    "extras2_runs": int(
        df["extras_2_runs"].fillna(0).sum()
    ),

    "reconstructed_team_runs": int(
        df["team_runs_this_delivery"].sum()
    )

}

for key, value in run_audit.items():
    print(f"{key}: {value}")

# ==========================================
# 5. LEGAL BALL AUDIT
# ==========================================

print("\nLEGAL BALL AUDIT")
print("=" * 60)

legal_audit = (

    df.groupby("extras_type", dropna=False)

    .agg(

        delivery_count=("match_id", "size"),

        legal_balls=("is_legal_ball", "sum"),

        total_runs=("team_runs_this_delivery", "sum")

    )

    .reset_index()

)

print(legal_audit.to_string(index=False))

# ==========================================
# 6. INNINGS SCORE CONSISTENCY
# ==========================================

print("\nINNINGS SCORE VALIDATION")
print("=" * 60)

score_check = (

    df.groupby(
        ["match_id", "innings"]
    )

    .agg(

        reconstructed_runs=(
            "team_runs_this_delivery", "sum"
        ),

        final_cumulative_runs=(
            "cumulative_runs", "last"
        ),

        reconstructed_wickets=(
            "is_wicket", "sum"
        ),

        final_cumulative_wickets=(
            "cumulative_wickets", "last"
        ),

        legal_balls=(
            "is_legal_ball", "sum"
        )

    )

    .reset_index()

)

score_check["runs_match"] = (

    score_check["reconstructed_runs"]

    == score_check["final_cumulative_runs"]

)

score_check["wickets_match"] = (

    score_check["reconstructed_wickets"]

    == score_check["final_cumulative_wickets"]

)

print(
    "Run mismatches:",
    int((~score_check["runs_match"]).sum())
)

print(
    "Wicket mismatches:",
    int((~score_check["wickets_match"]).sum())
)

# ==========================================
# 7. TARGET VALIDATION
# ==========================================

print("\nTARGET VALIDATION")
print("=" * 60)

second_innings = df[
    df["innings"] == 2
]

print(
    "Second innings deliveries:",
    len(second_innings)
)

print(
    "Missing targets:",
    int(second_innings["target"].isna().sum())
)

print(
    "Invalid negative targets:",
    int((second_innings["target"] < 0).sum())
)

# ==========================================
# 8. SUPER OVER AUDIT
# ==========================================

print("\nINNINGS DISTRIBUTION")
print("=" * 60)

innings_distribution = (

    df.groupby("innings")

    .agg(

        deliveries=("match_id", "size"),

        matches=("match_id", "nunique"),

        legal_balls=("is_legal_ball", "sum"),

        runs=("team_runs_this_delivery", "sum")

    )

    .reset_index()

)

print(innings_distribution.to_string(index=False))

# ==========================================
# 9. SAVE REPORTS
# ==========================================

extras_audit.to_csv(
    os.path.join(REPORT_DIR, "extras_audit.csv"),
    index=False
)

score_check.to_csv(
    os.path.join(REPORT_DIR, "innings_score_validation.csv"),
    index=False
)

legal_audit.to_csv(
    os.path.join(REPORT_DIR, "legal_ball_audit.csv"),
    index=False
)

report = {

    "delivery_records": int(len(df)),

    "innings_records": int(len(score_check)),

    "run_mismatches": int(
        (~score_check["runs_match"]).sum()
    ),

    "wicket_mismatches": int(
        (~score_check["wickets_match"]).sum()
    ),

    "missing_second_innings_targets": int(
        second_innings["target"].isna().sum()
    ),

    "total_reconstructed_runs": int(
        df["team_runs_this_delivery"].sum()
    )

}

with open(
    os.path.join(
        REPORT_DIR,
        "reconstruction_validation.json"
    ),
    "w"
) as f:

    json.dump(report, f, indent=4)

print("\nFINAL VALIDATION REPORT")
print("=" * 60)

for key, value in report.items():
    print(f"{key}: {value}")

print("\nValidation reports generated successfully!")
