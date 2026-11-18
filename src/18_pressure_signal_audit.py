
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "reports" / "unified_pressure_deliveries.csv.gz"
REPORT_DIR = ROOT / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("Loading unified pressure data...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

# ---------------------------------------------------------
# 1. FIRST INNINGS SIGNAL CONTRIBUTION
# ---------------------------------------------------------

first = df[df["innings"] == 1].copy()

first_signals = [
    "below_par_5_signal",
    "low_wickets_signal",
    "early_collapse_signal"
]

for col in first_signals:
    first[col] = first[col].fillna(False).astype(bool)

first["signal_count"] = first[first_signals].sum(axis=1)

first["signal_combination"] = (
    first[first_signals]
    .astype(int)
    .astype(str)
    .agg("".join, axis=1)
)

print("\nFIRST INNINGS SIGNAL CONTRIBUTION")
print("=" * 75)

first_contribution = (
    first.groupby(["innings_phase", "signal_combination"])
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=("is_pressure_delivery", "sum")
    )
    .reset_index()
)

first_contribution["percentage_of_phase"] = (
    first_contribution["deliveries"]
    / first_contribution.groupby("innings_phase")["deliveries"]
        .transform("sum") * 100
)

print(first_contribution.to_string(index=False))

# ---------------------------------------------------------
# 2. SECOND INNINGS SIGNAL CONTRIBUTION
# ---------------------------------------------------------

second = df[df["innings"] == 2].copy()

second_signals = [
    "high_rrr_signal",
    "low_wickets_signal",
    "low_balls_signal"
]

for col in second_signals:
    second[col] = second[col].fillna(False).astype(bool)

second["signal_count"] = second[second_signals].sum(axis=1)

second["signal_combination"] = (
    second[second_signals]
    .astype(int)
    .astype(str)
    .agg("".join, axis=1)
)

print("\nSECOND INNINGS SIGNAL CONTRIBUTION")
print("=" * 75)

second_contribution = (
    second.groupby(["innings_phase", "signal_combination"])
    .agg(
        deliveries=("match_id", "size"),
        pressure_deliveries=("is_pressure_delivery", "sum")
    )
    .reset_index()
)

second_contribution["percentage_of_phase"] = (
    second_contribution["deliveries"]
    / second_contribution.groupby("innings_phase")["deliveries"]
        .transform("sum") * 100
)

print(second_contribution.to_string(index=False))

# ---------------------------------------------------------
# 3. PRESSURE SIGNAL COUNTS BY PHASE
# ---------------------------------------------------------

print("\nFIRST INNINGS INDIVIDUAL SIGNAL RATES")
print("=" * 75)

first_rates = (
    first.groupby("innings_phase")
    .agg(
        deliveries=("match_id", "size"),
        below_par_5=("below_par_5_signal", "sum"),
        low_wickets=("low_wickets_signal", "sum"),
        early_collapse=("early_collapse_signal", "sum"),
        pressure=("is_pressure_delivery", "sum")
    )
    .reset_index()
)

print(first_rates.to_string(index=False))

print("\nSECOND INNINGS INDIVIDUAL SIGNAL RATES")
print("=" * 75)

second_rates = (
    second.groupby("innings_phase")
    .agg(
        deliveries=("match_id", "size"),
        high_rrr=("high_rrr_signal", "sum"),
        low_wickets=("low_wickets_signal", "sum"),
        low_balls=("low_balls_signal", "sum"),
        pressure=("is_pressure_delivery", "sum")
    )
    .reset_index()

)

print(second_rates.to_string(index=False))

# ---------------------------------------------------------
# 4. PRESSURE DISTRIBUTION BY MATCH INNINGS
# ---------------------------------------------------------

print("\nPRESSURE DISTRIBUTION BY MATCH INNINGS")
print("=" * 75)

match_summary = (
    df.groupby(["match_id", "season", "innings"])
    .agg(
        deliveries=("is_pressure_delivery", "size"),
        pressure_deliveries=("is_pressure_delivery", "sum")
    )
    .reset_index()
)

match_summary["pressure_percentage"] = (
    match_summary["pressure_deliveries"]
    / match_summary["deliveries"] * 100
)

match_distribution = (
    match_summary.groupby("innings")
    .agg(
        innings_count=("match_id", "size"),
        average_pressure_percentage=("pressure_percentage", "mean"),
        median_pressure_percentage=("pressure_percentage", "median"),
        p25_pressure_percentage=(
            "pressure_percentage",
            lambda x: x.quantile(0.25)
        ),
        p75_pressure_percentage=(
            "pressure_percentage",
            lambda x: x.quantile(0.75)
        ),
        maximum_pressure_percentage=("pressure_percentage", "max")
    )
    .reset_index()
)

print(match_distribution.to_string(index=False))

# ---------------------------------------------------------
# 5. SAVE REPORTS
# ---------------------------------------------------------

first_contribution.to_csv(
    REPORT_DIR / "first_innings_signal_combinations.csv",
    index=False
)

second_contribution.to_csv(
    REPORT_DIR / "second_innings_signal_combinations.csv",
    index=False
)

first_rates.to_csv(
    REPORT_DIR / "first_innings_signal_rates.csv",
    index=False
)

second_rates.to_csv(
    REPORT_DIR / "second_innings_signal_rates.csv",
    index=False
)

match_summary.to_csv(
    REPORT_DIR / "pressure_by_match_innings.csv",
    index=False
)

match_distribution.to_csv(
    REPORT_DIR / "pressure_match_distribution_summary.csv",
    index=False
)

print("\nPRESSURE SIGNAL AUDIT COMPLETED")
print("Reports saved in:", REPORT_DIR)
