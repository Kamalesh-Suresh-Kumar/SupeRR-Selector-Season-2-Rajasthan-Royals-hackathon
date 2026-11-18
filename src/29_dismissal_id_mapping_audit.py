
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT = BASE_DIR / "reports" / "unified_pressure_deliveries.csv.gz"

print("Loading IPL data...")
df = pd.read_csv(INPUT, low_memory=False)

# ------------------------------------------------------------
# 1. COLUMN TYPES
# ------------------------------------------------------------

print("\nCOLUMN TYPES")

columns = [
    "striker_id",
    "striker_name",
    "non_striker_id",
    "non_striker_name",
    "dismissed_player_id",
    "dismissal_type",
    "is_wicket"
]

for col in columns:
    print(f"{col}: {df[col].dtype}")

# ------------------------------------------------------------
# 2. NORMALIZE PLAYER IDS
# ------------------------------------------------------------

def normalize_id(series):
    return pd.to_numeric(series, errors="coerce").astype("Int64")


df["striker_id_clean"] = normalize_id(df["striker_id"])
df["non_striker_id_clean"] = normalize_id(df["non_striker_id"])
df["dismissed_player_id_clean"] = normalize_id(
    df["dismissed_player_id"]
)

# ------------------------------------------------------------
# 3. EXTRACT DISMISSAL RECORDS
# ------------------------------------------------------------

d = df[
    pd.to_numeric(df["is_wicket"], errors="coerce").fillna(0) == 1
].copy()

print("\nTOTAL DISMISSAL RECORDS:", len(d))

print("\nSAMPLE DISMISSAL RECORDS")

print(
    d[
        [
            "striker_id",
            "striker_name",
            "non_striker_id",
            "non_striker_name",
            "dismissed_player_id",
            "dismissal_type"
        ]
    ].head(20).to_string(index=False)
)

# ------------------------------------------------------------
# 4. BUILD PLAYER ID-TO-NAME MAPPING
# ------------------------------------------------------------

player_mapping = {}

for _, row in df.iterrows():

    striker_id = row["striker_id_clean"]
    striker_name = row["striker_name"]

    non_striker_id = row["non_striker_id_clean"]
    non_striker_name = row["non_striker_name"]

    if pd.notna(striker_id) and pd.notna(striker_name):
        player_mapping[int(striker_id)] = striker_name

    if pd.notna(non_striker_id) and pd.notna(non_striker_name):
        player_mapping[int(non_striker_id)] = non_striker_name

# ------------------------------------------------------------
# 5. CHECK DISMISSED PLAYER MAPPING
# ------------------------------------------------------------

d["dismissed_player_id_clean"] = normalize_id(
    d["dismissed_player_id"]
)

d["dismissed_player_name"] = (
    d["dismissed_player_id_clean"]
    .map(player_mapping)
)

print("\nDISMISSED PLAYER MAPPING AUDIT")

print("Dismissal records:", len(d))

print(
    "Records with dismissed player ID:",
    int(d["dismissed_player_id_clean"].notna().sum())
)

print(
    "Records with mapped player name:",
    int(d["dismissed_player_name"].notna().sum())
)

print(
    "Records with unmapped player name:",
    int(d["dismissed_player_name"].isna().sum())
)

# ------------------------------------------------------------
# 6. UNIQUE ID AUDIT
# ------------------------------------------------------------

known_ids = set(
    df["striker_id_clean"].dropna().astype(int)
)

known_ids.update(
    df["non_striker_id_clean"].dropna().astype(int)
)

dismissed_ids = set(
    d["dismissed_player_id_clean"].dropna().astype(int)
)

missing_ids = dismissed_ids - known_ids

print("\nUNIQUE PLAYER ID AUDIT")

print("Known player IDs:", len(known_ids))
print("Unique dismissed player IDs:", len(dismissed_ids))
print("Unmapped unique IDs:", len(missing_ids))

print("Unmapped IDs:", sorted(missing_ids)[:30])

# ------------------------------------------------------------
# 7. DISPLAY UNMAPPED RECORDS
# ------------------------------------------------------------

if d["dismissed_player_name"].isna().any():

    print("\nUNMAPPED DISMISSAL SAMPLES")

    print(
        d[d["dismissed_player_name"].isna()][
            [
                "striker_id",
                "striker_name",
                "non_striker_id",
                "non_striker_name",
                "dismissed_player_id",
                "dismissal_type"
            ]
        ].head(20).to_string(index=False)
    )

# ------------------------------------------------------------
# 8. SAVE AUDIT
# ------------------------------------------------------------

output = BASE_DIR / "reports" / "dismissal_id_mapping_audit.csv"

d.to_csv(output, index=False)

print("\nOUTPUT:", output)
print("\nSCRIPT 29 COMPLETED")
