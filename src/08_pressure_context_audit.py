
import pandas as pd
from pathlib import Path

# =====================================================
# 1. PROJECT PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "reconstructed_deliveries.csv.gz"
)

REPORT_DIR = BASE_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# =====================================================
# 2. LOAD DATA
# =====================================================

print("\nLoading reconstructed delivery data...")

df = pd.read_csv(INPUT_FILE, low_memory=False)

print("Total deliveries:", len(df))

# =====================================================
# 3. FILTER IPL DATA
# =====================================================

df["comp_name"] = df["comp_name"].fillna("").astype(str)

ipl = df[
    df["comp_name"].str.contains("IPL", case=False, na=False)
].copy()

print("IPL deliveries:", len(ipl))

# Exclude Super Overs from the main pressure audit.

ipl["is_super_over"] = (
    pd.to_numeric(ipl["innings"], errors="coerce") >= 3
)

regular = ipl[~ipl["is_super_over"]].copy()

print("Regular IPL deliveries:", len(regular))
print("Super Over deliveries excluded:", int(ipl["is_super_over"].sum()))

# =====================================================
# 4. CHECK REQUIRED COLUMNS
# =====================================================

required = [
    "match_id",
    "innings",
    "striker_id",
    "striker_name",
    "innings_phase",
    "is_high_pressure_delivery",
    "high_pressure_signals",
    "high_required_rate",
    "low_wickets_remaining",
    "death_overs",
    "required_run_rate_before",
    "runs_required_before",
    "balls_remaining_before",
    "wickets_in_hand_before"
]

missing = [col for col in required if col not in regular.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}")

# =====================================================
# 5. PRESSURE BY INNINGS
# =====================================================

print("\n" + "=" * 65)
print("PRESSURE DISTRIBUTION BY INNINGS")
print("=" * 65)

innings_pressure = (
    regular.groupby("innings")
    .agg(
        total_deliveries=("match_id", "size"),
        high_pressure_deliveries=("is_high_pressure_delivery", "sum"),
        average_pressure_signals=("high_pressure_signals", "mean")
    )
    .reset_index()
)

innings_pressure["pressure_percentage"] = (
    innings_pressure["high_pressure_deliveries"]
    / innings_pressure["total_deliveries"] * 100
)

print(innings_pressure.to_string(index=False))

# =====================================================
# 6. PRESSURE BY INNINGS PHASE
# =====================================================

print("\n" + "=" * 65)
print("PRESSURE DISTRIBUTION BY PHASE")
print("=" * 65)

phase_pressure = (
    regular.groupby(["innings", "innings_phase"])
    .agg(
        total_deliveries=("match_id", "size"),
        high_pressure_deliveries=("is_high_pressure_delivery", "sum"),
        average_pressure_signals=("high_pressure_signals", "mean")
    )
    .reset_index()
)

phase_pressure["pressure_percentage"] = (
    phase_pressure["high_pressure_deliveries"]
    / phase_pressure["total_deliveries"] * 100
)

print(phase_pressure.to_string(index=False))

# =====================================================
# 7. REQUIRED RUN RATE DISTRIBUTION
# =====================================================

print("\n" + "=" * 65)
print("SECOND INNINGS REQUIRED RUN RATE DISTRIBUTION")
print("=" * 65)

chase = regular[
    regular["innings"] == 2
].copy()

rrr = chase["required_run_rate_before"].dropna()

if not rrr.empty:
    print("Valid chase deliveries:", len(rrr))
    print("Minimum RRR:", round(rrr.min(), 2))
    print("Median RRR:", round(rrr.median(), 2))
    print("75th percentile RRR:", round(rrr.quantile(0.75), 2))
    print("90th percentile RRR:", round(rrr.quantile(0.90), 2))
    print("Maximum RRR:", round(rrr.max(), 2))

    for threshold in [8, 10, 12, 15]:
        count = (rrr >= threshold).sum()
        percentage = count / len(rrr) * 100

        print(
            f"RRR >= {threshold}: "
            f"{count} deliveries ({percentage:.2f}%)"
        )
else:
    print("No valid required run-rate values found.")

# =====================================================
# 8. INDIVIDUAL PRESSURE INDICATORS
# =====================================================

print("\n" + "=" * 65)
print("INDIVIDUAL PRESSURE INDICATORS")
print("=" * 65)

indicator_summary = pd.DataFrame([
    {
        "indicator": "High required run rate",
        "deliveries": int(regular["high_required_rate"].sum())
    },
    {
        "indicator": "Low wickets remaining",
        "deliveries": int(regular["low_wickets_remaining"].sum())
    },
    {
        "indicator": "Death overs",
        "deliveries": int(regular["death_overs"].sum())
    },
    {
        "indicator": "At least two pressure signals",
        "deliveries": int(regular["is_high_pressure_delivery"].sum())
    }
])

indicator_summary["percentage"] = (
    indicator_summary["deliveries"]
    / len(regular) * 100
)

print(indicator_summary.to_string(index=False))

# =====================================================
# 9. BATTER PRESSURE SAMPLE SIZES
# =====================================================

print("\n" + "=" * 65)
print("BATTER PRESSURE SAMPLE SIZE")
print("=" * 65)

batter_pressure = (
    regular.groupby(
        ["striker_id", "striker_name"],
        dropna=False
    )
    .agg(
        total_deliveries=("match_id", "size"),
        pressure_deliveries=("is_high_pressure_delivery", "sum"),
        matches_played=("match_id", "nunique")
    )
    .reset_index()
)

batter_pressure["pressure_percentage"] = (
    batter_pressure["pressure_deliveries"]
    / batter_pressure["total_deliveries"] * 100
)

batter_pressure = batter_pressure.sort_values(
    ["pressure_deliveries", "total_deliveries"],
    ascending=False
)

print("\nTop 15 batters by pressure delivery opportunities:")

print(
    batter_pressure.head(15).to_string(index=False)
)

# =====================================================
# 10. SAVE REPORTS
# =====================================================

innings_pressure.to_csv(
    REPORT_DIR / "pressure_by_innings.csv",
    index=False
)

phase_pressure.to_csv(
    REPORT_DIR / "pressure_by_phase.csv",
    index=False
)

indicator_summary.to_csv(
    REPORT_DIR / "pressure_indicator_summary.csv",
    index=False
)

batter_pressure.to_csv(
    REPORT_DIR / "batter_pressure_sample_sizes.csv",
    index=False
)

# =====================================================
# 11. FINAL SUMMARY
# =====================================================

print("\n" + "=" * 65)
print("PRESSURE AUDIT COMPLETED")
print("=" * 65)

print("Regular IPL deliveries:", len(regular))
print(
    "High-pressure deliveries:",
    int(regular["is_high_pressure_delivery"].sum())
)

print("\nReports saved in:", REPORT_DIR)
