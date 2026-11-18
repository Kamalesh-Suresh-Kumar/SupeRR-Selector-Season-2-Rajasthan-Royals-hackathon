
import os
import pandas as pd

# ==========================================
# 1. PROJECT PATHS
# ==========================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
REPORT_DIR = os.path.join(BASE_DIR, "reports")

INPUT_FILE = os.path.join(
    RAW_DIR,
    "ball_by_ball.csv"
)

os.makedirs(REPORT_DIR, exist_ok=True)

# ==========================================
# 2. LOAD ORIGINAL SOURCE DATA
# ==========================================

print("\nLoading original ball-by-ball dataset...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

print("Total source deliveries:", len(df))

# ==========================================
# 3. NORMALIZE EXTRAS CATEGORY
# ==========================================

df["extras_type_clean"] = (
    df["extras_type"]
    .fillna("No extras")
    .astype(str)
    .str.strip()
    .str.lower()
)

# ==========================================
# 4. IDENTIFY OTHER CATEGORY
# ==========================================

other = df[
    df["extras_type_clean"] == "other"
].copy()

print("\nOTHER CATEGORY ANALYSIS")
print("=" * 70)

print("Total records:", len(other))

# ==========================================
# 5. COMPLETE SOURCE RECORDS
# ==========================================

print("\nORIGINAL SOURCE RECORDS")
print("=" * 70)

print(other.to_string(index=False))

other.to_csv(
    os.path.join(
        REPORT_DIR,
        "original_other_extras_records.csv"
    ),
    index=False
)

# ==========================================
# 6. EXTRAS RUN COMBINATIONS
# ==========================================

print("\nEXTRAS RUN COMBINATIONS")
print("=" * 70)

combinations = (
    other.groupby(
        ["extras1_runs", "extras_2_runs"],
        dropna=False
    )
    .size()
    .reset_index(name="frequency")
    .sort_values("frequency", ascending=False)
)

print(combinations.to_string(index=False))

combinations.to_csv(
    os.path.join(
        REPORT_DIR,
        "original_other_extras_combinations.csv"
    ),
    index=False
)

# ==========================================
# 7. DELIVERY STYLE DISTRIBUTION
# ==========================================

print("\nDELIVERY STYLE DISTRIBUTION")
print("=" * 70)

if "delivery_style" in other.columns:

    style_distribution = (
        other["delivery_style"]
        .value_counts(dropna=False)
    )

    print(style_distribution.to_string())

    style_distribution.to_csv(
        os.path.join(
            REPORT_DIR,
            "original_other_delivery_styles.csv"
        ),
        header=["frequency"]
    )

# ==========================================
# 8. BOWLING TYPE DISTRIBUTION
# ==========================================

print("\nBOWLING TYPE DISTRIBUTION")
print("=" * 70)

if "bowling_type" in other.columns:

    bowling_distribution = (
        other["bowling_type"]
        .value_counts(dropna=False)
    )

    print(bowling_distribution.to_string())

# ==========================================
# 9. DISMISSAL DISTRIBUTION
# ==========================================

print("\nDISMISSAL DISTRIBUTION")
print("=" * 70)

if "dismissal_type" in other.columns:

    dismissal_distribution = (
        other["dismissal_type"]
        .value_counts(dropna=False)
    )

    print(dismissal_distribution.to_string())

# ==========================================
# 10. OVERSTEP VS OTHER COMPARISON
# ==========================================

print("\nOVERSTEP VS OTHER COMPARISON")
print("=" * 70)

comparison_data = df[
    df["extras_type_clean"].isin(
        ["overstep", "other"]
    )
].copy()

comparison = (
    comparison_data.groupby(
        [
            "extras_type_clean",
            "extras1_runs",
            "extras_2_runs"
        ],
        dropna=False
    )
    .size()
    .reset_index(name="frequency")
    .sort_values(
        [
            "extras_type_clean",
            "frequency"
        ],
        ascending=[True, False]
    )
)

print(comparison.to_string(index=False))

comparison.to_csv(
    os.path.join(
        REPORT_DIR,
        "overstep_vs_other_extras_comparison.csv"
    ),
    index=False
)

# ==========================================
# 11. DELIVERY STYLE BY EXTRAS CATEGORY
# ==========================================

print("\nDELIVERY STYLE BY EXTRAS CATEGORY")
print("=" * 70)

if "delivery_style" in df.columns:

    style_comparison = pd.crosstab(
        comparison_data["extras_type_clean"],
        comparison_data["delivery_style"],
        dropna=False
    )

    print(style_comparison.to_string())

    style_comparison.to_csv(
        os.path.join(
            REPORT_DIR,
            "overstep_vs_other_delivery_styles.csv"
        )
    )

# ==========================================
# 12. EXTRAS CATEGORY SUMMARY
# ==========================================

print("\nEXTRAS CATEGORY SUMMARY")
print("=" * 70)

category_summary = (
    df.groupby(
        "extras_type_clean",
        dropna=False
    )
    .agg(
        deliveries=("extras_type_clean", "size"),
        extras1_runs=("extras1_runs", "sum"),
        extras2_runs=("extras_2_runs", "sum")
    )
    .reset_index()
    .sort_values("deliveries", ascending=False)
)

print(category_summary.to_string(index=False))

category_summary.to_csv(
    os.path.join(
        REPORT_DIR,
        "original_extras_category_summary.csv"
    ),
    index=False
)

# ==========================================
# 13. SOURCE COLUMN INSPECTION
# ==========================================

print("\nAVAILABLE SOURCE COLUMNS")
print("=" * 70)

for column in df.columns:
    print(column)

# ==========================================
# 14. FINAL STATUS
# ==========================================

print("\n" + "=" * 70)
print("SOURCE EXTRAS AUDIT COMPLETED!")
print("=" * 70)

print("Total source deliveries:", len(df))
print("Total 'other' deliveries:", len(other))
print("Reports saved to:", REPORT_DIR)

print("\nGenerated reports:")
print("1. original_other_extras_records.csv")
print("2. original_other_extras_combinations.csv")
print("3. original_other_delivery_styles.csv")
print("4. overstep_vs_other_extras_comparison.csv")
print("5. overstep_vs_other_delivery_styles.csv")
print("6. original_extras_category_summary.csv")

print("\nAudit completed successfully.")
