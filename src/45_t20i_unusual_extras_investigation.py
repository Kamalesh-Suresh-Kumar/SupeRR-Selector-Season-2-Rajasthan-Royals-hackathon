
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
REPORTS.mkdir(exist_ok=True)

DATA = ROOT / "data" / "raw"

balls = pd.read_csv(DATA / "ball_by_ball.csv", low_memory=False)
matches = pd.read_csv(DATA / "matches.csv", low_memory=False)
competitions = pd.read_csv(DATA / "competitions.csv", low_memory=False)

# ---------------------------------------------------------
# 1. FILTER T20I MATCHES
# ---------------------------------------------------------

t20i_comp_ids = set(
    competitions.loc[
        competitions["match_format"].astype(str).str.upper() == "T20I",
        "comp_id"
    ]
)

matches["match_id"] = pd.to_numeric(matches["match_id"], errors="coerce")
balls["match_id"] = pd.to_numeric(balls["match_id"], errors="coerce")

t20i_matches = matches[matches["comp_id"].isin(t20i_comp_ids)].copy()
t20i_ids = set(t20i_matches["match_id"].dropna())

df = balls[balls["match_id"].isin(t20i_ids)].copy()
df["_source_row"] = df.index

# ---------------------------------------------------------
# 2. NORMALIZE TYPES AND ORDER DELIVERIES
# ---------------------------------------------------------

for col in [
    "innings", "overid", "over_ball_num", "innings_ball_num",
    "runs", "extras1_runs", "extras_2_runs", "is_wicket"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["extras_clean"] = (
    df["extras_type"]
    .fillna("none")
    .astype(str)
    .str.strip()
    .str.lower()
)

df = df.sort_values(
    ["match_id", "innings", "innings_ball_num", "overid", "over_ball_num"],
    kind="stable"
).reset_index(drop=True)

df["_sequence"] = df.groupby(
    ["match_id", "innings"], sort=False
).cumcount()

# ---------------------------------------------------------
# 3. IDENTIFY UNUSUAL RECORDS
# ---------------------------------------------------------

null_extras_with_runs = df[
    (df["extras_clean"] == "none")
    & (
        (df["extras1_runs"].fillna(0) != 0)
        | (df["extras_2_runs"].fillna(0) != 0)
    )
].copy()

other_records = df[df["extras_clean"] == "other"].copy()
penalty_records = df[df["extras_clean"] == "penalty"].copy()

targets = pd.concat(
    [null_extras_with_runs, other_records, penalty_records],
    ignore_index=True
).drop_duplicates(subset=["_source_row"])

print("\n" + "=" * 75)
print("STEP 45: UNUSUAL EXTRAS INVESTIGATION")
print("=" * 75)

print("\nUnusual record counts:")
print("Null extras with non-zero extras runs:", len(null_extras_with_runs))
print("Other extras:", len(other_records))
print("Penalty extras:", len(penalty_records))
print("Total unique unusual records:", len(targets))

# ---------------------------------------------------------
# 4. MATCH METADATA FOR UNUSUAL RECORDS
# ---------------------------------------------------------

metadata_columns = [
    "match_id", "comp_id", "match_number", "match_date",
    "stage", "venue_country", "home_team", "away_team", "result"
]

metadata_columns = [
    c for c in metadata_columns if c in t20i_matches.columns
]

targets = targets.merge(
    t20i_matches[metadata_columns].drop_duplicates("match_id"),
    on="match_id",
    how="left",
    suffixes=("", "_match")
)

# ---------------------------------------------------------
# 5. PRINT THE UNUSUAL RECORDS
# ---------------------------------------------------------

display_columns = [
    "match_id", "match_date", "innings", "innings_ball_num",
    "overid", "over_ball_num", "striker_name", "bowler_name",
    "runs", "extras_clean", "extras1_runs", "extras_2_runs",
    "is_wicket", "dismissal_type"
]

display_columns = [c for c in display_columns if c in targets.columns]

print("\n" + "-" * 75)
print("UNUSUAL DELIVERY RECORDS")
print("-" * 75)

if len(targets):
    print(
        targets[display_columns]
        .sort_values(["match_id", "innings", "innings_ball_num"])
        .to_string(index=False)
    )
else:
    print("No unusual extras records found.")

targets.to_csv(
    REPORTS / "t20i_unusual_extras_target_records.csv",
    index=False
)

# ---------------------------------------------------------
# 6. GET PREVIOUS AND NEXT DELIVERY FOR EACH TARGET
# ---------------------------------------------------------

target_keys = targets[
    ["match_id", "innings", "_sequence"]
].drop_duplicates()

neighbors = []

for row in target_keys.itertuples(index=False):
    match_id, innings, sequence = row

    selected = df[
        (df["match_id"] == match_id)
        & (df["innings"] == innings)
        & (df["_sequence"].between(sequence - 1, sequence + 1))
    ].copy()

    selected["target_sequence"] = sequence
    selected["relative_position"] = (
        selected["_sequence"] - sequence
    )

    neighbors.append(selected)

if neighbors:
    neighbor_df = pd.concat(neighbors, ignore_index=True)
else:
    neighbor_df = pd.DataFrame()

neighbor_columns = [
    "match_id", "innings", "_sequence", "relative_position",
    "innings_ball_num", "overid", "over_ball_num",
    "striker_name", "non_striker_name", "bowler_name",
    "runs", "extras_clean", "extras1_runs", "extras_2_runs",
    "is_wicket", "dismissal_type", "dismissed_player_id",
    "bowl_speed", "delivery_ist_time"
]

neighbor_columns = [
    c for c in neighbor_columns if c in neighbor_df.columns
]

if len(neighbor_df):
    neighbor_df = neighbor_df.sort_values(
        ["match_id", "innings", "target_sequence", "_sequence"]
    )

print("\n" + "-" * 75)
print("NEIGHBORING DELIVERY SAMPLE")
print("-" * 75)

if len(neighbor_df):
    print(neighbor_df[neighbor_columns].head(100).to_string(index=False))

neighbor_df.to_csv(
    REPORTS / "t20i_unusual_extras_with_neighbors.csv",
    index=False
)

# ---------------------------------------------------------
# 7. SUMMARIZE UNUSUAL EXTRAS BY MATCH
# ---------------------------------------------------------

print("\n" + "-" * 75)
print("UNUSUAL EXTRAS BY MATCH")
print("-" * 75)

if len(targets):
    match_summary = targets.groupby(
        ["match_id", "extras_clean"],
        dropna=False
    ).size().unstack(fill_value=0)

    print(match_summary.to_string())

    match_summary.to_csv(
        REPORTS / "t20i_unusual_extras_by_match.csv"
    )

# ---------------------------------------------------------
# 8. FIND T20I MATCHES WITHOUT DELIVERY RECORDS
# ---------------------------------------------------------

delivery_match_ids = set(df["match_id"].dropna())

missing_delivery_matches = t20i_matches[
    ~t20i_matches["match_id"].isin(delivery_match_ids)
].copy()

print("\n" + "-" * 75)
print("T20I MATCHES WITHOUT DELIVERY RECORDS")
print("-" * 75)

print("Count:", len(missing_delivery_matches))

missing_columns = [
    c for c in [
        "match_id", "comp_id", "match_number",
        "match_date", "stage", "venue_country",
        "home_team", "away_team", "result"
    ]
    if c in missing_delivery_matches.columns
]

if len(missing_delivery_matches):
    print(
        missing_delivery_matches[missing_columns]
        .sort_values("match_date")
        .to_string(index=False)
    )

missing_delivery_matches.to_csv(
    REPORTS / "t20i_matches_without_delivery_records.csv",
    index=False
)

# ---------------------------------------------------------
# 9. FINAL SUMMARY
# ---------------------------------------------------------

print("\n" + "=" * 75)
print("STEP 45 COMPLETED")
print("=" * 75)

print("Null extras with non-zero extras:", len(null_extras_with_runs))
print("Other extras:", len(other_records))
print("Penalty extras:", len(penalty_records))
print("Neighboring rows saved:", len(neighbor_df))
print("T20I matches without delivery data:", len(missing_delivery_matches))
print("\nReports saved in:", REPORTS)
