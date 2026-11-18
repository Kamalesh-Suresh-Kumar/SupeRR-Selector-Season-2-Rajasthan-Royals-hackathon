
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "reports" / "unified_pressure_deliveries.csv.gz"
REPORT_DIR = ROOT / "reports"

print("Loading data...")
df = pd.read_csv(INPUT_FILE, low_memory=False)

# --------------------------------------------------
# 1. RUN RECONCILIATION
# --------------------------------------------------

print("\n1. RUN RECONCILIATION")
print("=" * 85)

df["calculated_total"] = (
    df["runs"] +
    df["extras1_runs"] +
    df["extras_2_runs"]
)

df["run_difference"] = (
    df["team_runs_this_delivery"] -
    df["calculated_total"]
)

print("Total delivery records:", len(df))
print("Rows where runs do not reconcile:", (df["run_difference"] != 0).sum())

print("\nRun difference distribution:")
print(df["run_difference"].value_counts().sort_index())

print("\nSample mismatches:")
print(
    df.loc[
        df["run_difference"] != 0,
        [
            "runs", "extras1_runs", "extras_2_runs",
            "team_runs_this_delivery", "extras_type_clean"
        ]
    ].head(15).to_string(index=False)
)

# --------------------------------------------------
# 2. DISMISSAL TYPE AUDIT
# --------------------------------------------------

print("\n\n2. DISMISSAL TYPE AUDIT")
print("=" * 85)

dismissals = df[df["is_wicket"] == 1].copy()

dismissal_summary = (
    dismissals.groupby(
        ["dismissal_type_id", "dismissal_type"],
        dropna=False
    )
    .size()
    .reset_index(name="records")
    .sort_values("records", ascending=False)
)

print(dismissal_summary.to_string(index=False))

# --------------------------------------------------
# 3. EXTRAS AUDIT
# --------------------------------------------------

print("\n\n3. EXTRAS AUDIT")
print("=" * 85)

extras_summary = (
    df.groupby("extras_type_clean", dropna=False)
    .agg(
        records=("match_id", "size"),
        batter_runs=("runs", "sum"),
        extras1=("extras1_runs", "sum"),
        extras2=("extras_2_runs", "sum"),
        team_runs=("team_runs_this_delivery", "sum"),
        illegal_deliveries=("is_legal_ball", lambda x: (x == 0).sum())
    )
    .reset_index()
    .sort_values("records", ascending=False)
)

print(extras_summary.to_string(index=False))

# --------------------------------------------------
# 4. PRESSURE FLAG VALIDATION
# --------------------------------------------------

print("\n\n4. PRESSURE FLAG VALIDATION")
print("=" * 85)

# First innings: retain benchmark-based pressure definition.
first = df[df["innings"] == 1].copy()

first["analysis_pressure_delivery"] = (
    first["is_pressure_delivery"].fillna(False).astype(bool)
)

# Second innings: apply Rule B explicitly.
second = df[df["innings"] == 2].copy()

second["analysis_pressure_delivery"] = (
    (second["required_run_rate_before"] >= 10) &
    (
        (second["wickets_in_hand_before"] <= 6) |
        (second["balls_remaining_before"] <= 30)
    )
)

print(
    "First innings pressure deliveries:",
    int(first["analysis_pressure_delivery"].sum())
)

print(
    "Second innings Rule B pressure deliveries:",
    int(second["analysis_pressure_delivery"].sum())
)

print("\nSecond innings Rule B by phase:")

print(
    second.groupby("innings_phase")["analysis_pressure_delivery"]
    .agg(["count", "sum", "mean"])
    .to_string()
)

# --------------------------------------------------
# 5. SAVE REPORTS
# --------------------------------------------------

dismissal_summary.to_csv(
    REPORT_DIR / "dismissal_type_validation.csv",
    index=False
)

extras_summary.to_csv(
    REPORT_DIR / "extras_type_validation.csv",
    index=False
)

pressure_summary = pd.DataFrame([
    {
        "innings": 1,
        "pressure_definition": "First innings benchmark-based",
        "deliveries": len(first),
        "pressure_deliveries": int(
            first["analysis_pressure_delivery"].sum()
        )
    },
    {
        "innings": 2,
        "pressure_definition": "Rule B chase-dependent",
        "deliveries": len(second),
        "pressure_deliveries": int(
            second["analysis_pressure_delivery"].sum()
        )
    }
])

pressure_summary.to_csv(
    REPORT_DIR / "player_pressure_definition.csv",
    index=False
)

print("\n\nVALIDATION COMPLETED")
print("Reports saved in:", REPORT_DIR)
