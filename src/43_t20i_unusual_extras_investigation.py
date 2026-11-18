
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"

INPUT = REPORTS / "t20i_raw_deliveries.csv.gz"
MATCH_FILE = REPORTS / "t20i_match_list.csv"

df = pd.read_csv(INPUT, low_memory=False)
matches = pd.read_csv(MATCH_FILE, low_memory=False)

# Normalize fields
df["extras_clean"] = (
    df["extras_type"].fillna("").astype(str).str.strip().str.lower()
)

df["dismissal_clean"] = (
    df["dismissal_type"].fillna("").astype(str).str.strip().str.lower()
)

for col in [
    "innings", "overid", "over_ball_num", "innings_ball_num",
    "runs", "extras1_runs", "extras_2_runs", "is_wicket"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# --------------------------------------------------
# 1. ALL UNUSUAL EXTRAS RECORDS
# --------------------------------------------------

unusual = df[df["extras_clean"].isin(["other", "penalty"])].copy()

unusual = unusual.merge(
    matches[
        ["match_id", "match_date", "comp_name",
         "home_team", "away_team", "result"]
    ],
    on="match_id",
    how="left"
)

columns = [
    "match_id", "match_date", "comp_name",
    "home_team", "away_team", "result",
    "innings", "overid", "over_ball_num",
    "innings_ball_num", "striker_name", "bowler_name",
    "runs", "extras_clean", "extras1_runs",
    "extras_2_runs", "is_wicket", "dismissal_clean"
]

print("=" * 75)
print("ALL OTHER AND PENALTY RECORDS")
print("=" * 75)

print(unusual[columns].to_string(index=False))

unusual[columns].to_csv(
    REPORTS / "t20i_unusual_extras_all_records.csv",
    index=False
)

# --------------------------------------------------
# 2. SHOW NEIGHBOURING DELIVERIES
# --------------------------------------------------

print("\n" + "=" * 75)
print("NEIGHBOURING DELIVERY CONTEXT")
print("=" * 75)

df = df.sort_values(
    ["match_id", "innings", "overid", "over_ball_num"]
).reset_index(drop=True)

unusual_indices = set(unusual.index)

# Use stable source-row identifiers instead of relying on sorted index
df["_source_row"] = range(len(df))

target_keys = unusual[
    ["match_id", "innings", "overid", "over_ball_num", "extras_clean"]
].copy()

context_rows = []

for _, target in target_keys.iterrows():

    mask = (
        (df["match_id"] == target["match_id"]) &
        (df["innings"] == target["innings"]) &
        (df["overid"] == target["overid"]) &
        (df["over_ball_num"] == target["over_ball_num"])
    )

    positions = df.index[mask].tolist()

    if not positions:
        continue

    pos = positions[0]

    start = max(0, pos - 2)
    end = min(len(df), pos + 3)

    context = df.iloc[start:end].copy()

    context["target_extra"] = (
        context["match_id"].eq(target["match_id"]) &
        context["innings"].eq(target["innings"]) &
        context["overid"].eq(target["overid"]) &
        context["over_ball_num"].eq(target["over_ball_num"])
    )

    context_rows.append(context)

if context_rows:

    context_df = pd.concat(context_rows, ignore_index=True)

    context_columns = [
        "match_id", "innings", "overid",
        "over_ball_num", "innings_ball_num",
        "striker_name", "bowler_name",
        "runs", "extras_clean", "extras1_runs",
        "extras_2_runs", "is_wicket", "target_extra"
    ]

    print(
        context_df[context_columns]
        .to_string(index=False)
    )

    context_df[context_columns].to_csv(
        REPORTS / "t20i_unusual_extras_context.csv",
        index=False
    )

# --------------------------------------------------
# 3. CHECK UNUSUAL EXTRAS BY MATCH
# --------------------------------------------------

print("\n" + "=" * 75)
print("UNUSUAL EXTRAS BY MATCH")
print("=" * 75)

summary = (
    unusual.groupby(
        ["match_id", "comp_name", "extras_clean"],
        dropna=False
    )
    .agg(
        records=("runs", "size"),
        batter_runs=("runs", "sum"),
        extras1=("extras1_runs", "sum"),
        extras2=("extras_2_runs", "sum")
    )
    .reset_index()
)

print(summary.to_string(index=False))

summary.to_csv(
    REPORTS / "t20i_unusual_extras_match_summary.csv",
    index=False
)

# --------------------------------------------------
# 4. CHECK OVER-SEQUENCE CONSISTENCY
# --------------------------------------------------

print("\n" + "=" * 75)
print("OVER-SEQUENCE CHECKS")
print("=" * 75)

over_stats = (
    df.groupby(["match_id", "innings", "overid"])
    .agg(
        records=("over_ball_num", "size"),
        min_seq=("over_ball_num", "min"),
        max_seq=("over_ball_num", "max"),
        unique_seq=("over_ball_num", "nunique")
    )
    .reset_index()
)

invalid = over_stats[
    (over_stats["unique_seq"] != over_stats["records"]) |
    (over_stats["min_seq"] < 1) |
    (over_stats["max_seq"] > over_stats["records"])
]

print("Overs with duplicate or inconsistent sequence:", len(invalid))

if len(invalid):
    print(invalid.head(30).to_string(index=False))

print("\nSaved:")
print(" - t20i_unusual_extras_all_records.csv")
print(" - t20i_unusual_extras_context.csv")
print(" - t20i_unusual_extras_match_summary.csv")

print("\nUnusual extras investigation completed.")
