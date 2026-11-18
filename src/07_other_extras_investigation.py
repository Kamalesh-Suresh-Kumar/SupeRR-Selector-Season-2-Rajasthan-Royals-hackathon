
import pandas as pd
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

INPUT = BASE / "data" / "processed" / "reconstructed_deliveries.csv.gz"
AFFECTED = BASE / "reports" / "ipl_legal_balls_per_over_summary.csv"

OUTPUT = BASE / "reports" / "ipl_other_extras_investigation.csv"

print("Loading reconstructed deliveries...")

df = pd.read_csv(INPUT, compression="gzip", low_memory=False)
affected = pd.read_csv(AFFECTED)

# Restrict to the 74 affected IPL innings.
innings = affected[["match_id", "innings"]].drop_duplicates()

df = df.merge(
    innings,
    on=["match_id", "innings"],
    how="inner"
)

# Inspect every delivery classified as "other".
other = df[
    df["extras_type_clean"].astype(str).str.lower() == "other"
].copy()

# Preserve available source and reconstructed fields.
preferred_columns = [
    "match_id",
    "innings",
    "comp_name",
    "season",
    "innings_ball_num",
    "overid",
    "over_ball_num",
    "extras_type",
    "extras_type_clean",
    "extras1_runs",
    "extras_2_runs",
    "runs",
    "total_runs",
    "is_legal_ball",
    "legal_balls_completed",
    "wicket",
    "dismissal_type",
    "delivery_style",
    "batter_name",
    "bowler_name",
    "batting_team_name",
    "bowling_team_name"
]

columns = [c for c in preferred_columns if c in other.columns]
other = other[columns]

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
other.to_csv(OUTPUT, index=False)

print("\n" + "=" * 65)
print("OTHER EXTRAS INVESTIGATION")
print("=" * 65)

print("Affected IPL innings:", len(innings))
print("Other extras records:", len(other))

for col in ["extras_type", "extras_type_clean",
            "extras1_runs", "extras_2_runs",
            "is_legal_ball", "delivery_style",
            "dismissal_type"]:

    if col in other.columns:
        print(f"\n{col} distribution:")
        print(other[col].value_counts(dropna=False).to_string())

if "extras1_runs" in other.columns and "extras_2_runs" in other.columns:
    print("\nExtras run combinations:")
    print(
        other.groupby(
            ["extras1_runs", "extras_2_runs"],
            dropna=False
        ).size().to_string()
    )

print("\nAll inspected records:")
print(other.to_string(index=False))

print("\nSaved report:", OUTPUT)
