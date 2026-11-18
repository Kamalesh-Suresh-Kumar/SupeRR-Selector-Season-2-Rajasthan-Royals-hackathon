from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = ROOT / "reports" / "unified_pressure_deliveries.csv.gz"
OUTPUT_FILE = ROOT / "reports" / "player_data_schema_audit.csv"

print("Loading unified pressure data...")
df = pd.read_csv(INPUT_FILE, low_memory=False)

print("\nTOTAL RECORDS:", len(df))
print("TOTAL COLUMNS:", len(df.columns))

print("\nALL COLUMN NAMES")
print("=" * 90)

for i, col in enumerate(df.columns, 1):
    print(f"{i:03}. {col} | dtype={df[col].dtype}")

keywords = [
    "batter", "striker", "bowler", "player",
    "run", "extra", "wicket", "dismiss",
    "team", "legal", "pressure", "phase",
    "match", "season", "over", "ball"
]

selected = []

for col in df.columns:
    if any(word in col.lower() for word in keywords):
        selected.append(col)

print("\nPLAYER AND PERFORMANCE RELATED COLUMNS")
print("=" * 90)

for col in selected:
    print(
        f"\nCOLUMN: {col}"
        f"\nTYPE: {df[col].dtype}"
        f"\nMISSING: {df[col].isna().sum()}"
        f"\nUNIQUE VALUES: {df[col].nunique(dropna=True)}"
    )

    print("SAMPLE VALUES:")
    print(df[col].dropna().head(5).tolist())

summary = []

for col in df.columns:
    summary.append({
        "column": col,
        "dtype": str(df[col].dtype),
        "missing_values": int(df[col].isna().sum()),
        "unique_values": int(df[col].nunique(dropna=True)),
        "sample_values": str(df[col].dropna().head(5).tolist())
    })

pd.DataFrame(summary).to_csv(OUTPUT_FILE, index=False)

print("\n" + "=" * 90)
print("PLAYER DATA SCHEMA AUDIT COMPLETED")
print("Saved:", OUTPUT_FILE)