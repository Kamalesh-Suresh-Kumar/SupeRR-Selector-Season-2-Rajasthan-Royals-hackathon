
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

print("=" * 70)
print("DISMISSAL RECONCILIATION AUDIT")
print("=" * 70)

summary = pd.read_csv(
    REPORTS / "batter_corrected_dismissal_analysis.csv"
)

events = pd.read_csv(
    REPORTS / "batter_identified_dismissal_events.csv"
)

print("\n1. DISMISSAL SUMMARY COLUMNS")
print(summary.columns.tolist())

print("\n2. DISMISSAL EVENT COLUMNS")
print(events.columns.tolist())

# Normalize player IDs for comparison.
summary["striker_id_clean"] = pd.to_numeric(
    summary["striker_id_clean"],
    errors="coerce"
)

events["dismissed_player_id"] = pd.to_numeric(
    events["dismissed_player_id"],
    errors="coerce"
)

rashid_id = 4722

rashid_summary = summary[
    summary["striker_id_clean"] == rashid_id
]

rashid_events = events[
    events["dismissed_player_id"] == rashid_id
].copy()

print("\n3. RASHID KHAN SUMMARY")
print(rashid_summary.to_string(index=False))

print("\n4. RASHID KHAN EVENT COUNTS")
print("Total identified events:", len(rashid_events))

if "is_pressure_delivery" in rashid_events.columns:
    print("\nEvent pressure classification:")
    print(
        rashid_events["is_pressure_delivery"]
        .value_counts(dropna=False)
    )

if "dismissal_type" in rashid_events.columns:
    print("\nDismissal type breakdown:")
    print(
        rashid_events["dismissal_type"]
        .value_counts(dropna=False)
    )

print("\n5. EVENT-LEVEL MATCH AND INNINGS BREAKDOWN")

for col in ["match_id", "innings"]:
    if col in rashid_events.columns:
        print(f"\n{col}:")
        print(rashid_events[col].value_counts(dropna=False).to_string())

print("\n6. PLAYER-LEVEL RECONCILIATION")

if not rashid_summary.empty:
    row = rashid_summary.iloc[0]

    print(
        "Summary pressure dismissals:",
        row["pressure_dismissals"]
    )
    print(
        "Summary normal dismissals:",
        row["normal_dismissals"]
    )
    print(
        "Event total:",
        len(rashid_events)
    )

print("\nAudit completed.")
