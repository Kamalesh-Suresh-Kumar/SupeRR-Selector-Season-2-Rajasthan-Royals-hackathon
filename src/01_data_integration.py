
import pandas as pd
import numpy as np
import json
import os


# ==========================================
# 1. PROJECT PATHS
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Support both root-level and src-level Python scripts
if os.path.basename(BASE_DIR).lower() == "src":
    BASE_DIR = os.path.dirname(BASE_DIR)

RAW_DIR = os.path.join(BASE_DIR, "data", "raw")

PROCESSED_DIR = os.path.join(
    BASE_DIR, "data", "processed"
)

REPORT_DIR = os.path.join(
    BASE_DIR, "reports"
)

os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

print("PROJECT ROOT:", BASE_DIR)
print("RAW DATA PATH:", RAW_DIR)
print("PROCESSED PATH:", PROCESSED_DIR)


# ==========================================
# 2. LOAD DATASETS
# ==========================================

print("\nLoading Rajasthan Royals datasets...\n")

competitions = pd.read_csv(
    os.path.join(RAW_DIR, "competitions.csv")
)

teams = pd.read_csv(
    os.path.join(RAW_DIR, "teams.csv")
)

matches = pd.read_csv(
    os.path.join(RAW_DIR, "matches.csv")
)

balls = pd.read_csv(
    os.path.join(RAW_DIR, "ball_by_ball.csv")
)

player_mapping = pd.read_csv(
    os.path.join(RAW_DIR, "competition_team_player_mapping.csv")
)

playing_eleven = pd.read_csv(
    os.path.join(RAW_DIR, "playing_eleven.csv")
)


# ==========================================
# 3. DISPLAY DATASET INFORMATION
# ==========================================

datasets = {
    "Competitions": competitions,
    "Teams": teams,
    "Matches": matches,
    "Ball By Ball": balls,
    "Player Mapping": player_mapping,
    "Playing Eleven": playing_eleven
}

print("DATASET OVERVIEW")
print("=" * 65)

for name, df in datasets.items():

    print(f"\n{name}")

    print("Rows:", len(df))
    print("Columns:", len(df.columns))

    print("Column Names:")
    print(list(df.columns))


# ==========================================
# 4. VALIDATE PRIMARY KEYS
# ==========================================

key_checks = {

    "Competition ID unique":
        competitions["comp_id"].is_unique,

    "Match ID unique":
        matches["match_id"].is_unique,

    "Competition-Team pair unique":
        not teams.duplicated(
            ["comp_id", "team_id"]
        ).any(),

    "Competition-Team-Player unique":
        not player_mapping.duplicated(
            ["comp_id", "team_id", "player_id"]
        ).any(),

    "Delivery key unique":
        not balls.duplicated(
            ["match_id", "innings", "innings_ball_num"]
        ).any()

}

print("\nPRIMARY KEY VALIDATION")
print("=" * 65)

for key, value in key_checks.items():

    print(key, ":", value)


# ==========================================
# 5. CONNECT COMPETITIONS AND MATCHES
# ==========================================

competition_columns = [

    "comp_id",
    "comp_name",
    "match_format",
    "season"

]

match_data = matches.merge(

    competitions[competition_columns],

    on="comp_id",

    how="left",

    validate="many_to_one"

)

match_data["match_date_parsed"] = pd.to_datetime(
    match_data["match_date"],
    errors="coerce"
)


# ==========================================
# 6. CONNECT MATCHES AND BALL DATA
# ==========================================

integrated = balls.merge(

    match_data,

    on="match_id",

    how="left",

    validate="many_to_one",

    suffixes=("", "_match")

)

print("\nINTEGRATED DATASET")
print("=" * 65)

print("Rows:", len(integrated))
print("Columns:", len(integrated.columns))


# ==========================================
# 7. ADD TEAM NAMES
# ==========================================

# Initialize columns with object dtype
integrated["batting_team_name"] = pd.Series(
    index=integrated.index,
    dtype="object"
)

integrated["bowling_team_name"] = pd.Series(
    index=integrated.index,
    dtype="object"
)


# Assign batting team names
home_batting = (
    integrated["batting_team_id"]
    == integrated["home_team_id"]
)

away_batting = (
    integrated["batting_team_id"]
    == integrated["away_team_id"]
)

integrated.loc[home_batting, "batting_team_name"] = (
    integrated.loc[home_batting, "home_team"]
)

integrated.loc[away_batting, "batting_team_name"] = (
    integrated.loc[away_batting, "away_team"]
)


# Assign bowling team names
home_bowling = (
    integrated["bowling_team_id"]
    == integrated["home_team_id"]
)

away_bowling = (
    integrated["bowling_team_id"]
    == integrated["away_team_id"]
)

integrated.loc[home_bowling, "bowling_team_name"] = (
    integrated.loc[home_bowling, "home_team"]
)

integrated.loc[away_bowling, "bowling_team_name"] = (
    integrated.loc[away_bowling, "away_team"]
)


# ==========================================
# 8. VALIDATE PLAYER MAPPINGS
# ==========================================

striker_mapping = (

    player_mapping[
        ["comp_id", "player_id"]
    ]

    .drop_duplicates()

    .rename(
        columns={"player_id": "striker_id"}
    )

)

bowler_mapping = (

    player_mapping[
        ["comp_id", "player_id"]
    ]

    .drop_duplicates()

    .rename(
        columns={"player_id": "bowler_id"}
    )

)


integrated = integrated.merge(

    striker_mapping.assign(
        striker_in_comp_mapping=True
    ),

    on=["comp_id", "striker_id"],

    how="left",

    validate="many_to_one"

)

integrated = integrated.merge(

    bowler_mapping.assign(
        bowler_in_comp_mapping=True
    ),

    on=["comp_id", "bowler_id"],

    how="left",

    validate="many_to_one"

)

integrated["striker_in_comp_mapping"] = (
    integrated["striker_in_comp_mapping"].fillna(False)
)

integrated["bowler_in_comp_mapping"] = (
    integrated["bowler_in_comp_mapping"].fillna(False)
)


# ==========================================
# 9. VALIDATE PLAYING XI MEMBERSHIP
# ==========================================

xi_keys = playing_eleven[
    ["match_id", "team_id", "player_id"]
].drop_duplicates()


striker_xi = (

    xi_keys

    .rename(
        columns={
            "team_id": "batting_team_id",
            "player_id": "striker_id"
        }
    )

    .assign(striker_in_match_xi=True)

)


bowler_xi = (

    xi_keys

    .rename(
        columns={
            "team_id": "bowling_team_id",
            "player_id": "bowler_id"
        }
    )

    .assign(bowler_in_match_xi=True)

)


integrated = integrated.merge(

    striker_xi,

    on=["match_id", "batting_team_id", "striker_id"],

    how="left",

    validate="many_to_one"

)

integrated = integrated.merge(

    bowler_xi,

    on=["match_id", "bowling_team_id", "bowler_id"],

    how="left",

    validate="many_to_one"

)



integrated["striker_in_match_xi"] = (
    integrated["striker_in_match_xi"]
    .fillna(False)
    .astype(bool)
)

integrated["bowler_in_match_xi"] = (
    integrated["bowler_in_match_xi"]
    .fillna(False)
    .astype(bool)
)



# ==========================================
# 10. DATA QUALITY REPORT
# ==========================================

report = {

    "total_deliveries": int(len(integrated)),

    "total_matches": int(matches["match_id"].nunique()),

    "total_competitions": int(competitions["comp_id"].nunique()),

    "unmatched_match_records": int(
        integrated["comp_id"].isna().sum()
    ),

    "unmapped_striker_deliveries": int(
        (~integrated["striker_in_comp_mapping"]).sum()
    ),

    "unmapped_bowler_deliveries": int(
        (~integrated["bowler_in_comp_mapping"]).sum()
    ),

    "striker_not_in_xi": int(
        integrated["striker_in_match_xi"].eq(False).sum()
    ),

    "bowler_not_in_xi": int(
        integrated["bowler_in_match_xi"].eq(False).sum()
    ),

    "duplicate_delivery_keys": int(
        balls.duplicated(
            ["match_id", "innings", "innings_ball_num"]
        ).sum()
    ),

    "matches_without_deliveries": int(
        (~matches["match_id"].isin(
            balls["match_id"].unique()
        )).sum()
    )

}


# ==========================================
# 11. SAVE OUTPUTS
# ==========================================

integrated.to_csv(

    os.path.join(
        PROCESSED_DIR,
        "integrated_ball_by_ball.csv.gz"
    ),

    index=False,

    compression="gzip"

)


match_data.to_csv(

    os.path.join(
        PROCESSED_DIR,
        "integrated_matches.csv"
    ),

    index=False

)


with open(

    os.path.join(
        REPORT_DIR,
        "data_quality_report.json"
    ),

    "w"

) as f:

    json.dump(
        report,
        f,
        indent=4
    )


# ==========================================
# 12. DISPLAY FINAL RESULTS
# ==========================================

print("\nFINAL DATA QUALITY REPORT")
print("=" * 65)

for key, value in report.items():

    print(f"{key}: {value}")


print("\nIntegrated dataset successfully generated!")

print(
    "\nOutput:",
    os.path.join(
        PROCESSED_DIR,
        "integrated_ball_by_ball.csv.gz"
    )
)
