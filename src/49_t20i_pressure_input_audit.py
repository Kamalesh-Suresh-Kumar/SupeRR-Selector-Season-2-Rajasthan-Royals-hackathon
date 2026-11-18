
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

deliveries_path = REPORTS / "t20i_reconstructed_deliveries.csv.gz"
innings_path = REPORTS / "t20i_reconstructed_innings_summary.csv"

print("\n" + "=" * 75)
print("STEP 49: T20I PRESSURE-MODEL INPUT AUDIT")
print("=" * 75)

# ---------------------------------------------------------
# 1. LOAD RECONSTRUCTED DATA
# ---------------------------------------------------------

df = pd.read_csv(deliveries_path, low_memory=False)
innings = pd.read_csv(innings_path, low_memory=False)

print("\nDelivery dimensions:", df.shape)
print("Innings dimensions:", innings.shape)

# ---------------------------------------------------------
# 2. INSPECT DELIVERY COLUMNS
# ---------------------------------------------------------

print("\n" + "-" * 75)
print("DELIVERY DATA COLUMNS")
print("-" * 75)

for col in df.columns:
    print(f"{col}: {df[col].dtype}")

# ---------------------------------------------------------
# 3. CHECK IMPORTANT PRESSURE FIELDS
# ---------------------------------------------------------

candidate_fields = [
    "match_id",
    "innings",
    "overid",
    "over_ball_num",
    "innings_ball_num",
    "striker_id",
    "striker_name",
    "non_striker_id",
    "non_striker_name",
    "bowler_id",
    "bowler_name",
    "runs",
    "is_four",
    "is_six",
    "is_wicket",
    "dismissal_type",
    "dismissed_player_id",
    "extras_type",
    "extras1_runs",
    "extras_2_runs",
    "is_legal_ball",
    "legal_ball_number",
    "cumulative_runs",
    "cumulative_wickets",
    "team_runs_this_delivery",
    "target",
    "revised_target",
    "balls_remaining",
    "innings_ball_number",
]

print("\n" + "-" * 75)
print("IMPORTANT FIELD AVAILABILITY")
print("-" * 75)

field_audit = []

for col in candidate_fields:
    exists = col in df.columns

    field_audit.append({
        "field": col,
        "exists": exists,
        "missing_values": (
            int(df[col].isna().sum()) if exists else None
        ),
        "unique_values": (
            int(df[col].nunique()) if exists else None
        ),
    })

print(pd.DataFrame(field_audit).to_string(index=False))

# ---------------------------------------------------------
# 4. INSPECT INNINGS SUMMARY COLUMNS
# ---------------------------------------------------------

print("\n" + "-" * 75)
print("INNINGS SUMMARY COLUMNS")
print("-" * 75)

for col in innings.columns:
    print(f"{col}: {innings[col].dtype}")

# ---------------------------------------------------------
# 5. CHECK DELIVERY ORDER AND LEGAL-BALL FIELDS
# ---------------------------------------------------------

sort_candidates = [
    "match_id",
    "innings",
    "overid",
    "over_ball_num",
]

available_sort = [
    col for col in sort_candidates if col in df.columns
]

if available_sort:
    ordered = df.sort_values(available_sort).copy()

    print("\n" + "-" * 75)
    print("SAMPLE DELIVERY SEQUENCES")
    print("-" * 75)

    sample_matches = ordered["match_id"].drop_duplicates().head(3)

    for match_id in sample_matches:
        print(f"\nMatch ID: {match_id}")

        sample = ordered[
            (ordered["match_id"] == match_id) &
            (ordered["innings"].isin([1, 2]))
        ]

        print(sample.head(12).to_string(index=False))

# ---------------------------------------------------------
# 6. CHECK MATCHES WITH REVISED TARGETS
# ---------------------------------------------------------

raw_matches = pd.read_csv(
    ROOT / "data" / "raw" / "matches.csv"
)

revised_target_matches = raw_matches[
    raw_matches["revised_target"].notna()
].copy()

delivery_match_ids = set(df["match_id"].unique())

revised_target_matches["has_delivery_data"] = (
    revised_target_matches["match_id"].isin(delivery_match_ids)
)

print("\n" + "-" * 75)
print("REVISED TARGET COVERAGE")
print("-" * 75)

print(
    "Matches with revised target:",
    len(revised_target_matches)
)

print(
    "With delivery data:",
    int(revised_target_matches["has_delivery_data"].sum())
)

print(
    "Without delivery data:",
    int((~revised_target_matches["has_delivery_data"]).sum())
)

print(
    revised_target_matches[
        [
            "match_id",
            "match_date",
            "first_inn_revised_overs",
            "second_inn_revised_overs",
            "revised_target",
            "result",
            "has_delivery_data",
        ]
    ].to_string(index=False)
)

# ---------------------------------------------------------
# 7. SAVE AUDIT
# ---------------------------------------------------------

summary = {
    "delivery_rows": int(len(df)),
    "innings_rows": int(len(innings)),
    "delivery_columns": df.columns.tolist(),
    "innings_columns": innings.columns.tolist(),
    "important_fields": field_audit,
    "revised_target_matches": int(len(revised_target_matches)),
    "revised_target_matches_with_delivery_data": int(
        revised_target_matches["has_delivery_data"].sum()
    ),
}

with open(
    REPORTS / "t20i_pressure_input_audit.json",
    "w",
    encoding="utf-8"
) as f:
    json.dump(summary, f, indent=4, default=str)

print("\n" + "=" * 75)
print("STEP 49 COMPLETED")
print("=" * 75)

print("Saved:", REPORTS / "t20i_pressure_input_audit.json")
