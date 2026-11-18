
import os
import pandas as pd

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

print("\nLoading reconstructed dataset...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

print("Total records:", len(df))

# ==========================================
# 3. INSPECT AVAILABLE COLUMNS
# ==========================================

print("\nAVAILABLE INVESTIGATION COLUMNS")
print("=" * 70)

candidates = [
    "match_id",
    "innings",
    "overid",
    "over_ball_num",
    "innings_ball_num",
    "runs",
    "extras1_runs",
    "extras_2_runs",
    "extras_type",
    "is_legal_ball",
    "is_wicket",
    "dismissal_type",
    "batting_type",
    "bowling_type",
    "delivery_style",
    "pace_or_spin"
]

available = [c for c in candidates if c in df.columns]

print(available)

# ==========================================
# 4. IDENTIFY OVERS WITH MORE THAN 6 LEGAL BALLS
# ==========================================

print("\nOVERS WITH MORE THAN 6 LEGAL BALLS")
print("=" * 70)

overs = (
    df.groupby(["match_id", "innings", "overid"])
    .agg(
        delivery_count=("match_id", "size"),
        legal_balls=("is_legal_ball", "sum")
    )
    .reset_index()
)

suspicious = overs[overs["legal_balls"] > 6].copy()

print("Suspicious overs:", len(suspicious))

suspicious.to_csv(
    os.path.join(REPORT_DIR, "suspicious_overs.csv"),
    index=False
)

# ==========================================
# 5. INSPECT DELIVERIES IN SUSPICIOUS OVERS
# ==========================================

details = df.merge(
    suspicious[["match_id", "innings", "overid"]],
    on=["match_id", "innings", "overid"],
    how="inner"
)

details = details.sort_values(
    ["match_id", "innings", "overid", "innings_ball_num"]
)

print("\nSUSPICIOUS DELIVERY DETAILS")
print("=" * 70)

print(
    details[available].head(150).to_string(index=False)
)

details[available].to_csv(
    os.path.join(REPORT_DIR, "suspicious_delivery_details.csv"),
    index=False
)

# ==========================================
# 6. INVESTIGATE OTHER AND OVERSTEP
# ==========================================

print("\nOTHER AND OVERSTEP COMPARISON")
print("=" * 70)

comparison = df[
    df["extras_type"].astype(str).str.lower().isin(
        ["other", "overstep", "wide"]
    )
]

group_summary = (
    comparison.groupby("extras_type")
    .agg(
        deliveries=("match_id", "size"),
        batter_runs=("runs", "sum"),
        extras=("extras1_runs", "sum"),
        legal_balls=("is_legal_ball", "sum"),
        wickets=("is_wicket", "sum")
    )
    .reset_index()
)

print(group_summary.to_string(index=False))

# ==========================================
# 7. CHECK OTHER DELIVERY SEQUENCES
# ==========================================

print("\nOTHER DELIVERY BALL POSITIONS")
print("=" * 70)

other = df[
    df["extras_type"].astype(str).str.lower() == "other"
]

position_summary = (
    other.groupby("over_ball_num")
    .size()
    .reset_index(name="frequency")
    .sort_values("over_ball_num")
)

print(position_summary.to_string(index=False))

# ==========================================
# 8. SAVE INVESTIGATION RESULTS
# ==========================================

group_summary.to_csv(
    os.path.join(REPORT_DIR, "legal_ball_category_comparison.csv"),
    index=False
)

position_summary.to_csv(
    os.path.join(REPORT_DIR, "other_ball_position_summary.csv"),
    index=False
)

print("\nINVESTIGATION COMPLETED")

print("Reports saved to:", REPORT_DIR)
