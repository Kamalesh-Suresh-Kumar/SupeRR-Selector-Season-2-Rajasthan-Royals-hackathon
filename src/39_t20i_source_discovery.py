
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
REPORTS = ROOT / "reports"

REPORTS.mkdir(exist_ok=True)

FILES = {
    "competitions": RAW / "competitions.csv",
    "matches": RAW / "matches.csv",
    "teams": RAW / "teams.csv",
    "players_mapping": RAW / "competition_team_player_mapping.csv",
}

data = {}

print("=" * 70)
print("T20I SOURCE DISCOVERY")
print("=" * 70)

# --------------------------------------------------
# 1. INSPECT FILE STRUCTURES
# --------------------------------------------------

for name, path in FILES.items():

    print(f"\n{'=' * 70}")
    print(f"FILE: {name}")
    print(f"PATH: {path}")

    if not path.exists():
        print("FILE NOT FOUND")
        continue

    df = pd.read_csv(path, low_memory=False)
    data[name] = df

    print("\nShape:", df.shape)

    print("\nColumns:")
    for col in df.columns:
        print(" -", col)

    print("\nFirst 3 rows:")
    print(df.head(3).to_string(index=False))

# --------------------------------------------------
# 2. COMPETITION DETAILS
# --------------------------------------------------

if "competitions" in data:

    df = data["competitions"]

    print("\n" + "=" * 70)
    print("COMPETITION METADATA")
    print("=" * 70)

    for col in df.columns:

        if df[col].nunique(dropna=True) <= 100:
            print(f"\nCOLUMN: {col}")
            print(df[col].value_counts(dropna=False).to_string())

# --------------------------------------------------
# 3. MATCH DETAILS
# --------------------------------------------------

if "matches" in data:

    df = data["matches"]

    print("\n" + "=" * 70)
    print("MATCH METADATA")
    print("=" * 70)

    print("Total matches:", len(df))

    for col in df.columns:

        if any(word in col.lower() for word in [
            "competition", "format", "gender", "season",
            "date", "match_type", "type"
        ]):

            print(f"\nCOLUMN: {col}")

            if df[col].nunique(dropna=True) <= 100:
                print(df[col].value_counts(dropna=False).to_string())
            else:
                print("Unique values:", df[col].nunique())
                print("Sample values:")
                print(df[col].dropna().head(10).tolist())

# --------------------------------------------------
# 4. SAVE METADATA SNAPSHOTS
# --------------------------------------------------

for name, df in data.items():

    output = REPORTS / f"t20i_discovery_{name}.csv"

    if name == "competitions":
        df.to_csv(output, index=False)

    elif name == "matches":
        df.to_csv(output, index=False)

print("\n" + "=" * 70)
print("DISCOVERY COMPLETED")
print("=" * 70)
print("Metadata snapshots saved in reports/")
