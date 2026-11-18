
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

df = pd.read_csv(
    REPORTS / "bowler_wicket_attribution_audit.csv"
)

print("=" * 70)
print("BOWLER WICKET MISMATCH INVESTIGATION")
print("=" * 70)

# Overall totals
print("\n1. OVERALL COMPARISON")

for col in [
    "wickets_pressure",
    "pressure_credited_wickets",
    "wickets_normal",
    "normal_credited_wickets"
]:
    if col in df.columns:
        print(col, "=", df[col].sum())

# Exact mismatches
pressure = df[
    df["pressure_difference"].fillna(0).abs() > 0
].copy()

normal = df[
    df["normal_difference"].fillna(0).abs() > 0
].copy()

print("\n2. PRESSURE MISMATCHES:", len(pressure))

print(
    pressure[
        [
            "bowler_id",
            "bowler_name_report",
            "wickets_pressure",
            "pressure_credited_wickets",
            "pressure_difference"
        ]
    ].sort_values(
        "pressure_difference",
        key=lambda x: x.abs(),
        ascending=False
    ).to_string(index=False)
)

print("\n3. NORMAL MISMATCHES:", len(normal))

print(
    normal[
        [
            "bowler_id",
            "bowler_name_report",
            "wickets_normal",
            "normal_credited_wickets",
            "normal_difference"
        ]
    ].to_string(index=False)
)

# Check duplicate IDs in both source reports.
print("\n4. DUPLICATE BOWLER IDS")

print(
    "Audit duplicates:",
    df["bowler_id"].duplicated().sum()
)

base = pd.read_csv(
    REPORTS / "bowler_pressure_vs_baseline.csv"
)

print(
    "Original report duplicates:",
    base["bowler_id"].duplicated().sum()
)

# Check whether differences cancel out.
print("\n5. NET DIFFERENCE")

print(
    "Pressure net difference:",
    pressure["pressure_difference"].sum()
)

print(
    "Normal net difference:",
    normal["normal_difference"].sum()
)

df.to_csv(
    REPORTS / "bowler_mismatch_investigation.csv",
    index=False
)

print("\nSaved reports/bowler_mismatch_investigation.csv")
