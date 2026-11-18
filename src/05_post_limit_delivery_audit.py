
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

INPUT = BASE / "data" / "processed" / "reconstructed_deliveries.csv.gz"
OUTPUT = BASE / "reports" / "post_limit_legal_deliveries.csv"

print("Loading reconstructed data...")
df = pd.read_csv(INPUT, compression="gzip", low_memory=False)

required = [
    "match_id",
    "innings",
    "innings_ball_num",
    "legal_balls_completed",
    "is_legal_ball",
    "extras_type_clean"
]

missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

# Restrict this audit to IPL innings identified in our report.
affected = pd.read_csv(
    BASE / "reports" / "ipl_affected_innings_over_summary.csv"
)

innings = affected[["match_id", "innings"]].drop_duplicates()

df = df.merge(
    innings,
    on=["match_id", "innings"],
    how="inner"
)

# Keep deliveries counted as legal after the 120-ball limit.
df["is_legal_ball"] = (
    pd.to_numeric(df["is_legal_ball"], errors="coerce")
    .fillna(0)
    .astype(int)
)

df["legal_balls_completed"] = pd.to_numeric(
    df["legal_balls_completed"],
    errors="coerce"
)

audit = df[
    (df["is_legal_ball"] == 1) &
    (df["legal_balls_completed"] > 120)
].copy()

# Keep available source fields for manual inspection.
preferred = [
    "match_id",
    "innings",
    "innings_ball_num",
    "overid",
    "over_ball_num",
    "legal_balls_completed",
    "is_legal_ball",
    "extras_type",
    "extras_type_clean",
    "extras1_runs",
    "extras_2_runs",
    "runs",
    "total_runs",
    "wicket",
    "dismissal_type",
    "delivery_style",
    "batter_name",
    "bowler_name",
    "batting_team_name",
    "bowling_team_name"
]

columns = [c for c in preferred if c in audit.columns]
audit = audit[columns]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
audit.to_csv(OUTPUT, index=False)

print("\n" + "=" * 60)
print("POST-LIMIT DELIVERY AUDIT")
print("=" * 60)

print("Affected IPL innings:", len(innings))
print("Post-limit legal delivery records:", len(audit))

if "extras_type_clean" in audit.columns:
    print("\nExtras category:")
    print(audit["extras_type_clean"].value_counts(dropna=False))

print("\nSample records:")
print(audit.head(30).to_string(index=False))

print("\nSaved to:", OUTPUT)
