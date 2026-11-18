import pandas as pd
from pathlib import Path

folder = Path("reports")
player_id = 4722
player_name = "Rashid Khan"

print("=" * 80)
print("RASHID KHAN — IPL BATTER RANKING AUDIT")
print("=" * 80)

files = [
    "batter_reliability_ratings.csv",
    "batter_pressure_vs_normal.csv",
    "batter_pressure_group_metrics.csv",
    "batter_pressure_consistency.csv",
]

for filename in files:
    path = folder / filename

    if not path.exists():
        print(f"\nNOT FOUND: {filename}")
        continue

    df = pd.read_csv(path)

    id_cols = [
        c for c in df.columns
        if c.lower() in ["striker_id", "batter_id", "player_id"]
    ]

    name_cols = [
        c for c in df.columns
        if c.lower() in ["striker_name", "batter_name", "player_name"]
    ]

    mask = pd.Series(False, index=df.index)

    for col in id_cols:
        mask |= pd.to_numeric(df[col], errors="coerce").eq(player_id)

    for col in name_cols:
        mask |= df[col].astype(str).str.contains(
            player_name, case=False, na=False
        )

    print(f"\n{'-' * 80}")
    print(f"FILE: {filename}")

    if mask.any():
        print(df.loc[mask].to_string(index=False))
    else:
        print("No matching player record found.")
        print("Available columns:", df.columns.tolist())

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
