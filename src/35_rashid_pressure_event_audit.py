
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

events = pd.read_csv(
    REPORTS / "batter_identified_dismissal_events.csv"
)

rashid = events[
    pd.to_numeric(events["dismissed_player_id"], errors="coerce") == 4722
].copy()

print("=" * 75)
print("RASHID KHAN PRESSURE DISMISSAL EVENT AUDIT")
print("=" * 75)

# Inspect all dismissal events individually.
columns = [
    "match_id",
    "season",
    "match_date",
    "innings",
    "striker_name",
    "dismissed_player_name",
    "dismissal_type",
    "is_pressure_delivery",
    "is_pressure",
    "pressure_model",
    "pressure_severity",
    "innings_phase",
    "required_run_rate_before",
    "runs_below_par",
    "wickets_in_hand_before",
    "balls_remaining_before"
]

available = [c for c in columns if c in rashid.columns]

print("\nALL RASHID KHAN DISMISSAL EVENTS")
print(
    rashid[available]
    .sort_values(["match_date", "match_id"])
    .to_string(index=False)
)

print("\nPRESSURE FLAG CROSS-CHECK")

if "is_pressure_delivery" in rashid.columns and "is_pressure" in rashid.columns:
    print(
        pd.crosstab(
            rashid["is_pressure_delivery"],
            rashid["is_pressure"],
            dropna=False
        )
    )

print("\nPRESSURE MODEL BREAKDOWN")

if "pressure_model" in rashid.columns:
    print(
        rashid["pressure_model"]
        .value_counts(dropna=False)
    )

print("\nDISMISSAL TYPE BY PRESSURE FLAG")

if "is_pressure_delivery" in rashid.columns:
    print(
        pd.crosstab(
            rashid["dismissal_type"],
            rashid["is_pressure_delivery"],
            dropna=False
        )
    )

print("\nAudit complete.")
