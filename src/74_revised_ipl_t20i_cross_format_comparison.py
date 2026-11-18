
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# STEP 74: REVISED IPL - T20I CROSS-FORMAT COMPARISON
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"
REPORTS.mkdir(exist_ok=True)

FILES = {
    "ipl_batters": REPORTS / "batter_reliability_ratings_revised.csv",
    "ipl_bowlers": REPORTS / "bowler_reliability_ratings_revised.csv",
    "t20i_batters": REPORTS / "t20i_batter_ratings_primary.csv",
    "t20i_bowlers": REPORTS / "t20i_bowler_ratings_primary.csv"
}

EXPECTED_POPULATIONS = {
    "ipl_batters": 32,
    "ipl_bowlers": 49,
    "t20i_batters": 41,
    "t20i_bowlers": 62
}

TOP_N = 10

print("=" * 85)
print("STEP 74: REVISED IPL - T20I CROSS-FORMAT COMPARISON")
print("=" * 85)


# ============================================================
# 1. INPUT VALIDATION
# ============================================================

for key, path in FILES.items():

    if not path.exists():
        raise FileNotFoundError(
            f"Required input file not found: {path}"
        )

    print(f"FOUND: {path.name}")

print("\nAll four input files found.")


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def find_column(df, candidates, description):

    for column in candidates:

        if column in df.columns:
            return column

    raise ValueError(
        f"Missing {description}.\n"
        f"Expected one of: {candidates}\n"
        f"Available columns: {df.columns.tolist()}"
    )


def clean_id(series):

    values = series.astype("string").str.strip()

    numeric = pd.to_numeric(values, errors="coerce")

    valid = numeric.notna()

    values.loc[valid] = (
        numeric.loc[valid]
        .astype("Int64")
        .astype("string")
    )

    return values.replace("", pd.NA)


def normalize_name(series):

    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )


def convert_boolean(series):

    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .isin(["true", "1", "yes", "y"])
    )


def numeric_column(df, candidates, description):

    column = find_column(
        df,
        candidates,
        description
    )

    return column


# ============================================================
# 3. STANDARDIZE PLAYER DATA
# ============================================================

def prepare_data(df, player_type, format_name):

    df = df.copy()

    print(
        f"\nPreparing {format_name} {player_type} data..."
    )

    # --------------------------------------------------------
    # BATTER
    # --------------------------------------------------------

    if player_type == "Batter":

        id_col = find_column(
            df,
            ["striker_id", "batter_id", "player_id"],
            f"{format_name} batter ID"
        )

        name_col = find_column(
            df,
            ["player_name", "striker_name", "batter_name"],
            f"{format_name} batter name"
        )

        if format_name == "IPL":

            rank_col = "final_rank"
            rating_col = "rating_primary"

            performance_col = numeric_column(
                df,
                [
                    "performance_metric",
                    "strike_rate_difference",
                    "strike_rate_improvement"
                ],
                "IPL batter performance metric"
            )

            secondary_col = numeric_column(
                df,
                [
                    "risk_metric",
                    "dismissal_rate_difference_y",
                    "dismissal_improvement"
                ],
                "IPL batter dismissal metric"
            )

            if "eligible_revised" not in df.columns:

                raise ValueError(
                    "IPL revised batter file is missing "
                    "'eligible_revised'. Run Step 73 again."
                )

            df = df[
                convert_boolean(df["eligible_revised"])
            ].copy()

        else:

            rank_col = find_column(
                df,
                ["rank", "final_rank"],
                "T20I batter rank"
            )

            rating_col = find_column(
                df,
                ["rating", "rating_primary"],
                "T20I batter rating"
            )

            performance_col = numeric_column(
                df,
                [
                    "strike_rate_improvement",
                    "strike_rate_difference",
                    "performance_metric"
                ],
                "T20I batter performance metric"
            )

            secondary_col = numeric_column(
                df,
                [
                    "dismissal_improvement",
                    "dismissal_rate_improvement",
                    "dismissal_rate_difference",
                    "risk_metric"
                ],
                "T20I batter dismissal metric"
            )

    # --------------------------------------------------------
    # BOWLER
    # --------------------------------------------------------

    else:

        id_col = find_column(
            df,
            ["bowler_id", "player_id"],
            f"{format_name} bowler ID"
        )

        name_col = find_column(
            df,
            ["player_name", "bowler_name"],
            f"{format_name} bowler name"
        )

        if format_name == "IPL":

            rank_col = "final_rank"
            rating_col = "rating_primary"

            # Step 73 already calculates these two metrics.
            performance_col = numeric_column(
                df,
                [
                    "performance_metric",
                    "economy_improvement",
                    "economy_difference"
                ],
                "IPL bowler performance metric"
            )

            secondary_col = numeric_column(
                df,
                [
                    "risk_metric",
                    "pressure_wickets_per_100_balls",
                    "wickets_per_100_difference"
                ],
                "IPL bowler wicket metric"
            )

            if "eligible_revised" not in df.columns:

                raise ValueError(
                    "IPL revised bowler file is missing "
                    "'eligible_revised'. Run Step 73 again."
                )

            df = df[
                convert_boolean(df["eligible_revised"])
            ].copy()

        else:

            rank_col = find_column(
                df,
                ["rank", "final_rank"],
                "T20I bowler rank"
            )

            rating_col = find_column(
                df,
                ["rating", "rating_primary"],
                "T20I bowler rating"
            )

            performance_col = numeric_column(
                df,
                [
                    "economy_improvement",
                    "economy_difference",
                    "performance_metric"
                ],
                "T20I bowler performance metric"
            )

            secondary_col = numeric_column(
                df,
                [
                    "pressure_wickets_per_100_balls",
                    "wickets_per_100_difference",
                    "risk_metric"
                ],
                "T20I bowler wicket metric"
            )

    # --------------------------------------------------------
    # REQUIRED COLUMN VALIDATION
    # --------------------------------------------------------

    required = [
        id_col,
        name_col,
        rank_col,
        rating_col,
        performance_col,
        secondary_col
    ]

    missing = [
        column
        for column in required
        if column not in df.columns
    ]

    if missing:

        raise ValueError(
            f"{format_name} {player_type} missing columns: "
            f"{missing}"
        )

    # --------------------------------------------------------
    # STANDARDIZED DATAFRAME
    # --------------------------------------------------------

    result = pd.DataFrame({

        "player_id": clean_id(df[id_col]),

        "player_name": (
            df[name_col]
            .astype("string")
            .str.strip()
        ),

        "rank": pd.to_numeric(
            df[rank_col],
            errors="coerce"
        ),

        "rating": pd.to_numeric(
            df[rating_col],
            errors="coerce"
        ),

        "pressure_performance_improvement": pd.to_numeric(
            df[performance_col],
            errors="coerce"
        ),

        "secondary_pressure_metric": pd.to_numeric(
            df[secondary_col],
            errors="coerce"
        )
    })

    # --------------------------------------------------------
    # EXPOSURE FIELDS
    # --------------------------------------------------------

    if player_type == "Batter":

        exposure_columns = [
            "matches_pressure",
            "matches_normal",
            "balls_pressure",
            "balls_normal"
        ]

    else:

        exposure_columns = [
            "matches_pressure",
            "matches_normal",
            "legal_balls_pressure",
            "legal_balls_normal"
        ]

    for column in exposure_columns:

        if column in df.columns:

            result[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    # --------------------------------------------------------
    # CLEAN AND VALIDATE
    # --------------------------------------------------------

    result = result.dropna(
        subset=[
            "player_id",
            "player_name",
            "rank",
            "rating"
        ]
    ).copy()

    result["player_id"] = (
        result["player_id"].astype("string")
    )

    result["rank"] = result["rank"].astype(int)

    result["name_normalized"] = normalize_name(
        result["player_name"]
    )

    if result["player_id"].duplicated().any():

        duplicates = result[
            result["player_id"].duplicated(keep=False)
        ]

        raise ValueError(
            f"Duplicate player IDs found in "
            f"{format_name} {player_type}:\n"
            f"{duplicates.to_string(index=False)}"
        )

    if result["player_id"].isna().any():

        raise ValueError(
            f"Missing player IDs in {format_name} {player_type}."
        )

    result["format"] = format_name

    print(
        f"Prepared {len(result)} eligible "
        f"{format_name} {player_type.lower()}s."
    )

    return result.reset_index(drop=True)


# ============================================================
# 4. LOAD DATA
# ============================================================

raw = {}

for key, path in FILES.items():

    raw[key] = pd.read_csv(path)

    print(
        f"Loaded {key}: {len(raw[key])} rows"
    )


# ============================================================
# 5. STANDARDIZE ALL FOUR DATASETS
# ============================================================

ipl_batters = prepare_data(
    raw["ipl_batters"],
    "Batter",
    "IPL"
)

ipl_bowlers = prepare_data(
    raw["ipl_bowlers"],
    "Bowler",
    "IPL"
)

t20i_batters = prepare_data(
    raw["t20i_batters"],
    "Batter",
    "T20I"
)

t20i_bowlers = prepare_data(
    raw["t20i_bowlers"],
    "Bowler",
    "T20I"
)


# ============================================================
# 6. ELIGIBLE POPULATION VALIDATION
# ============================================================

actual_populations = {

    "ipl_batters": len(ipl_batters),

    "ipl_bowlers": len(ipl_bowlers),

    "t20i_batters": len(t20i_batters),

    "t20i_bowlers": len(t20i_bowlers)
}

print("\n" + "=" * 85)
print("ELIGIBLE POPULATION VALIDATION")
print("=" * 85)

for key, actual in actual_populations.items():

    expected = EXPECTED_POPULATIONS[key]

    print(
        f"{key}: {actual} "
        f"(expected {expected})"
    )

    if actual != expected:

        raise ValueError(
            f"Population mismatch for {key}: "
            f"expected {expected}, got {actual}"
        )

print("\nAll eligible population checks passed.")


# ============================================================
# 7. CROSS-FORMAT COMPARISON
# ============================================================

def compare_formats(ipl, t20i, player_type):

    print("\n" + "=" * 85)
    print(f"COMPARING {player_type.upper()}S")
    print("=" * 85)

    ipl = ipl.copy()
    t20i = t20i.copy()

    n_ipl = len(ipl)
    n_t20i = len(t20i)

    # Convert ranks to relative position within each format.
    # These percentiles are for rank-position comparison only.

    ipl["rank_percentile"] = (
        (n_ipl - ipl["rank"]) / (n_ipl - 1) * 100
        if n_ipl > 1 else 100
    )

    t20i["rank_percentile"] = (
        (n_t20i - t20i["rank"]) / (n_t20i - 1) * 100
        if n_t20i > 1 else 100
    )

    # Prefix format-specific columns.

    ipl = ipl.rename(
        columns={
            column: "ipl_" + column
            for column in ipl.columns
            if column != "player_id"
        }
    )

    t20i = t20i.rename(
        columns={
            column: "t20i_" + column
            for column in t20i.columns
            if column != "player_id"
        }
    )

    # Match using player IDs.

    comparison = ipl.merge(
        t20i,
        on="player_id",
        how="outer",
        indicator=True,
        validate="one_to_one"
    )

    comparison["available_in_ipl"] = (
        comparison["_merge"].isin(
            ["both", "left_only"]
        )
    )

    comparison["available_in_t20i"] = (
        comparison["_merge"].isin(
            ["both", "right_only"]
        )
    )

    matched = comparison["_merge"] == "both"

    # --------------------------------------------------------
    # ID AND NAME VALIDATION
    # --------------------------------------------------------

    comparison["identity_name_match"] = False

    comparison.loc[matched, "identity_name_match"] = (
        comparison.loc[
            matched,
            "ipl_name_normalized"
        ].fillna("")
        ==
        comparison.loc[
            matched,
            "t20i_name_normalized"
        ].fillna("")
    )

    comparison["identity_status"] = np.select(
        [
            comparison["_merge"] == "left_only",

            comparison["_merge"] == "right_only",

            comparison["identity_name_match"]
        ],

        [
            "IPL_ONLY",

            "T20I_ONLY",

            "ID_AND_NAME_MATCH"
        ],

        default="ID_MATCH_NAME_CONFLICT"
    )

    # --------------------------------------------------------
    # TOP 10 FLAGS
    # --------------------------------------------------------

    comparison["ipl_top10"] = (
        comparison["ipl_rank"].le(TOP_N)
    ).fillna(False)

    comparison["t20i_top10"] = (
        comparison["t20i_rank"].le(TOP_N)
    ).fillna(False)

    # --------------------------------------------------------
    # CROSS-FORMAT EVIDENCE CLASSIFICATION
    # --------------------------------------------------------

    comparison["cross_format_evidence"] = np.select(
        [
            comparison["identity_status"]
            == "ID_MATCH_NAME_CONFLICT",

            comparison["ipl_top10"]
            & comparison["t20i_top10"],

            comparison["ipl_top10"]
            & ~comparison["t20i_top10"]
            & comparison["available_in_t20i"],

            ~comparison["ipl_top10"]
            & comparison["t20i_top10"]
            & comparison["available_in_ipl"],

            comparison["available_in_ipl"]
            & comparison["available_in_t20i"],

            comparison["available_in_ipl"],

            comparison["available_in_t20i"]
        ],

        [
            "IDENTITY_CONFLICT_REVIEW",

            "TOP10_BOTH_FORMATS",

            "TOP10_IPL_ONLY",

            "TOP10_T20I_ONLY",

            "ELIGIBLE_BOTH_OUTSIDE_TOP10",

            "IPL_ONLY_NO_T20I_ELIGIBILITY",

            "T20I_ONLY_NO_IPL_ELIGIBILITY"
        ],

        default="REVIEW"
    )

    # Rank percentile difference is not a rating difference.

    comparison["ipl_minus_t20i_rank_percentile"] = (
        comparison["ipl_rank_percentile"]
        - comparison["t20i_rank_percentile"]
    )

    # --------------------------------------------------------
    # EXPORT COMPARISON FILES
    # --------------------------------------------------------

    prefix = (
        f"cross_format_revised_{player_type.lower()}"
    )

    comparison.to_csv(
        REPORTS / f"{prefix}_comparison.csv",
        index=False
    )

    comparison[
        comparison["_merge"] == "both"
    ].to_csv(
        REPORTS / f"{prefix}_matched.csv",
        index=False
    )

    comparison[
        comparison["_merge"] != "both"
    ].to_csv(
        REPORTS / f"{prefix}_unmatched.csv",
        index=False
    )

    comparison[
        comparison["identity_status"]
        == "ID_MATCH_NAME_CONFLICT"
    ].to_csv(
        REPORTS / f"{prefix}_identity_conflicts.csv",
        index=False
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    top10_both = int(
        (
            comparison["cross_format_evidence"]
            == "TOP10_BOTH_FORMATS"
        ).sum()
    )

    top10_ipl_only = int(
        (
            comparison["cross_format_evidence"]
            == "TOP10_IPL_ONLY"
        ).sum()
    )

    top10_t20i_only = int(
        (
            comparison["cross_format_evidence"]
            == "TOP10_T20I_ONLY"
        ).sum()
    )

    summary = {

        "player_type": player_type,

        "ipl_eligible_players": n_ipl,

        "t20i_eligible_players": n_t20i,

        "matched_player_ids": int(matched.sum()),

        "unmatched_ipl_players": int(
            (comparison["_merge"] == "left_only").sum()
        ),

        "unmatched_t20i_players": int(
            (comparison["_merge"] == "right_only").sum()
        ),

        "confirmed_id_and_name_matches": int(
            (
                comparison["identity_status"]
                == "ID_AND_NAME_MATCH"
            ).sum()
        ),

        "identity_conflicts": int(
            (
                comparison["identity_status"]
                == "ID_MATCH_NAME_CONFLICT"
            ).sum()
        ),

        "top10_both_formats": top10_both,

        "top10_ipl_only": top10_ipl_only,

        "top10_t20i_only": top10_t20i_only
    }

    print("\nCROSS-FORMAT SUMMARY")

    for key, value in summary.items():

        print(f"{key}: {value}")

    if summary["identity_conflicts"] > 0:

        print(
            "\nWARNING: Identity conflicts require manual review."
        )

    return comparison, summary


# ============================================================
# 8. RUN BATTER AND BOWLER COMPARISONS
# ============================================================

batter_comparison, batter_summary = compare_formats(
    ipl_batters,
    t20i_batters,
    "Batter"
)

bowler_comparison, bowler_summary = compare_formats(
    ipl_bowlers,
    t20i_bowlers,
    "Bowler"
)


# ============================================================
# 9. EXPORT COMBINED SUMMARY
# ============================================================

summary_df = pd.DataFrame(
    [
        batter_summary,
        bowler_summary
    ]
)

summary_df.to_csv(
    REPORTS / "cross_format_revised_comparison_summary.csv",
    index=False
)


# ============================================================
# 10. EXPORT CROSS-FORMAT TOP-10 EVIDENCE
# ============================================================

evidence_rows = []

for player_type, comparison in [

    ("Batter", batter_comparison),

    ("Bowler", bowler_comparison)

]:

    selected = comparison[
        (
            comparison["ipl_top10"]
            | comparison["t20i_top10"]
        )
        & (
            comparison["identity_status"]
            == "ID_AND_NAME_MATCH"
        )
    ]

    for _, row in selected.iterrows():

        evidence_rows.append({

            "player_type": player_type,

            "player_id": row["player_id"],

            "player_name": row["ipl_player_name"],

            "ipl_rank": row["ipl_rank"],

            "ipl_rating": row["ipl_rating"],

            "t20i_rank": row["t20i_rank"],

            "t20i_rating": row["t20i_rating"],

            "ipl_top10": row["ipl_top10"],

            "t20i_top10": row["t20i_top10"],

            "cross_format_evidence": row[
                "cross_format_evidence"
            ],

            "ipl_pressure_improvement": row[
                "ipl_pressure_performance_improvement"
            ],

            "t20i_pressure_improvement": row[
                "t20i_pressure_performance_improvement"
            ]

        })


evidence_columns = [
    "player_type",
    "player_id",
    "player_name",
    "ipl_rank",
    "ipl_rating",
    "t20i_rank",
    "t20i_rating",
    "ipl_top10",
    "t20i_top10",
    "cross_format_evidence",
    "ipl_pressure_improvement",
    "t20i_pressure_improvement"
]

evidence_df = pd.DataFrame(
    evidence_rows,
    columns=evidence_columns
)

evidence_df.to_csv(
    REPORTS / "cross_format_revised_top10_evidence.csv",
    index=False
)


# ============================================================
# 11. FINAL EVIDENCE DISPLAY
# ============================================================

print("\n" + "=" * 85)
print("REVISED CROSS-FORMAT TOP-10 EVIDENCE")
print("=" * 85)

if evidence_df.empty:

    print(
        "No confirmed matched top-10 evidence found."
    )

else:

    print(
        evidence_df.sort_values(
            ["player_type", "ipl_rank", "t20i_rank"],
            na_position="last"
        ).round(2).to_string(index=False)
    )


# ============================================================
# 12. IDENTITY VALIDATION
# ============================================================

total_conflicts = (
    batter_summary["identity_conflicts"]
    + bowler_summary["identity_conflicts"]
)

if total_conflicts > 0:

    raise ValueError(
        f"{total_conflicts} identity conflict(s) found. "
        "Review the identity conflict CSV files before submission."
    )


# ============================================================
# 13. COMPLETION
# ============================================================

print("\n" + "=" * 85)
print("STEP 74 COMPLETED SUCCESSFULLY")
print("=" * 85)

print("\nGENERATED FILES:")

generated_files = [

    "cross_format_revised_comparison_summary.csv",

    "cross_format_revised_top10_evidence.csv",

    "cross_format_revised_batter_comparison.csv",

    "cross_format_revised_batter_matched.csv",

    "cross_format_revised_batter_unmatched.csv",

    "cross_format_revised_batter_identity_conflicts.csv",

    "cross_format_revised_bowler_comparison.csv",

    "cross_format_revised_bowler_matched.csv",

    "cross_format_revised_bowler_unmatched.csv",

    "cross_format_revised_bowler_identity_conflicts.csv"

]

for filename in generated_files:

    print(f"reports/{filename}")


print("\nVALIDATION COMPLETE")

print("- Revised IPL ratings used.")
print("- T20I primary ratings retained.")
print("- Player matching performed using IDs.")
print("- Player names checked for identity conflicts.")
print("- Original Step 67 outputs preserved.")
print("- IPL and T20I ratings remain separate.")
print("- Cross-format rank percentiles are not treated as raw rating comparisons.")

print("\nSTEP 74 FINISHED.")
