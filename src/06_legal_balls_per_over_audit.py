
import pandas as pd
from pathlib import Path

# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "reconstructed_deliveries.csv.gz"
REPORT_DIR = BASE_DIR / "reports"

REPORT_DIR.mkdir(parents=True, exist_ok=True)

OVER_REPORT = REPORT_DIR / "ipl_legal_balls_per_over_audit.csv"
INNINGS_REPORT = REPORT_DIR / "ipl_innings_legal_balls_summary.csv"

# ============================================================
# LOAD DATA
# ============================================================

print("Loading reconstructed data...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

print(f"Total deliveries: {len(df)}")

# ============================================================
# FILTER IPL DATA
# ============================================================

df["comp_name"] = df["comp_name"].fillna("").astype(str)

ipl = df[
    df["comp_name"].str.contains("IPL", case=False, na=False)
].copy()

print(f"IPL deliveries: {len(ipl)}")

if ipl.empty:
    raise ValueError("No IPL records found. Check the comp_name column.")

# ============================================================
# PREPARE COLUMNS
# ============================================================

ipl["is_legal_ball"] = (
    ipl["is_legal_ball"]
    .fillna(False)
    .astype(bool)
)

ipl["overid"] = pd.to_numeric(
    ipl["overid"], errors="coerce"
)

ipl["innings_ball_num"] = pd.to_numeric(
    ipl["innings_ball_num"], errors="coerce"
)

ipl["over_ball_num"] = pd.to_numeric(
    ipl["over_ball_num"], errors="coerce"
)

# ============================================================
# AUDIT EVERY IPL OVER
# ============================================================

print("\nAuditing every IPL over...")

metadata_columns = [
    col for col in [
        "comp_name",
        "season",
        "batting_team_name",
        "bowling_team_name"
    ]
    if col in ipl.columns
]

aggregation = {
    "recorded_deliveries": ("is_legal_ball", "size"),
    "legal_deliveries": ("is_legal_ball", "sum"),
    "first_innings_ball": ("innings_ball_num", "min"),
    "last_innings_ball": ("innings_ball_num", "max"),
    "first_over_ball": ("over_ball_num", "min"),
    "last_over_ball": ("over_ball_num", "max")
}

for col in metadata_columns:
    aggregation[col] = (col, "first")

over_audit = (
    ipl.groupby(
        ["match_id", "innings", "overid"],
        dropna=False
    )
    .agg(**aggregation)
    .reset_index()
)

over_audit["more_than_six_legal"] = (
    over_audit["legal_deliveries"] > 6
)

over_audit = over_audit.sort_values(
    ["match_id", "innings", "overid"]
)

# ============================================================
# INNINGS-LEVEL SUMMARY
# ============================================================

innings_aggregation = {
    "total_legal_deliveries": ("legal_deliveries", "sum"),
    "number_of_overs": ("overid", "nunique"),
    "overs_with_more_than_six_legal": (
        "more_than_six_legal", "sum"
    ),
    "maximum_legal_deliveries_in_one_over": (
        "legal_deliveries", "max"
    )
}

for col in metadata_columns:
    innings_aggregation[col] = (col, "first")

innings_summary = (
    over_audit.groupby(
        ["match_id", "innings"],
        dropna=False
    )
    .agg(**innings_aggregation)
    .reset_index()
)

# ============================================================
# IDENTIFY PROBLEM OVERS
# ============================================================

problem_overs = over_audit[
    over_audit["more_than_six_legal"]
].copy()

# ============================================================
# SAVE REPORTS
# ============================================================

over_audit.to_csv(OVER_REPORT, index=False)

innings_summary.to_csv(
    INNINGS_REPORT,
    index=False
)

# ============================================================
# DISPLAY RESULTS
# ============================================================

print("\n" + "=" * 65)
print("ALL IPL LEGAL BALLS PER OVER AUDIT")
print("=" * 65)

print(f"IPL innings inspected: {len(innings_summary)}")
print(f"Total overs inspected: {len(over_audit)}")

print("\nOvers with more than six legal deliveries:")

if problem_overs.empty:
    print("None found.")
else:
    print(
        problem_overs[
            [
                "match_id",
                "innings",
                "overid",
                "recorded_deliveries",
                "legal_deliveries",
                "first_innings_ball",
                "last_innings_ball"
            ]
        ].to_string(index=False)
    )

print("\nINNINGS-LEVEL SUMMARY")

print(
    innings_summary[
        [
            "match_id",
            "innings",
            "total_legal_deliveries",
            "number_of_overs",
            "overs_with_more_than_six_legal",
            "maximum_legal_deliveries_in_one_over"
        ]
    ].head(10).to_string(index=False)
)

print("\n" + "=" * 65)
print("FINAL AUDIT RESULTS")
print("=" * 65)

print(f"Overs inspected: {len(over_audit)}")
print(f"Overs exceeding six legal deliveries: {len(problem_overs)}")

if over_audit.empty:
    print("WARNING: No overs were available for validation.")
else:
    print(
        "Maximum legal deliveries in one over:",
        int(over_audit["legal_deliveries"].max())
    )

print("\nREPORTS GENERATED")
print(OVER_REPORT)
print(INNINGS_REPORT)

print("\nAUDIT COMPLETED")
