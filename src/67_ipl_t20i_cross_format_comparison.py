
from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# STEP 67: IPL - T20I CROSS-FORMAT EVIDENCE COMPARISON
# ============================================================

REPORTS = Path("reports")
REPORTS.mkdir(exist_ok=True)

FILES = {
    "ipl_batters": REPORTS / "batter_reliability_ratings.csv",
    "ipl_bowlers": REPORTS / "bowler_reliability_ratings.csv",
    "t20i_batters": REPORTS / "t20i_batter_ratings_primary.csv",
    "t20i_bowlers": REPORTS / "t20i_bowler_ratings_primary.csv"
}

print("\n" + "=" * 85)
print("STEP 67: IPL - T20I CROSS-FORMAT EVIDENCE COMPARISON")
print("=" * 85)


# ============================================================
# 1. CHECK INPUT FILES
# ============================================================

for name, path in FILES.items():
    if not path.exists():
        raise FileNotFoundError(
            f"Required input file not found: {path}"
        )

print("\nAll four input files found.")


# ============================================================
# 2. HELPER FUNCTIONS
# ============================================================

def first_available_column(data, candidates, description):
    for column in candidates:
        if column in data.columns:
            return column

    raise ValueError(
        f"Could not find {description}. "
        f"Expected one of: {candidates}"
    )


def clean_player_id(series):
    """
    Normalize player IDs without matching players by name.
    """

    values = series.astype("string").str.strip()

    numeric = pd.to_numeric(values, errors="coerce")

    # Convert numeric IDs into a consistent string representation.
    result = values.copy()

    valid_numeric = numeric.notna()

    result.loc[valid_numeric] = (
        numeric.loc[valid_numeric]
        .astype("Int64")
        .astype("string")
    )

    result = result.replace("", pd.NA)

    return result


def normalize_name(series):
    return (
        series.astype("string")
        .str.strip()
        .str.lower()
        .str.replace(r"\s+", " ", regex=True)
    )


def convert_eligible(series):
    """
    Convert common CSV boolean representations to True/False.
    """

    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False)

    values = series.astype("string").str.strip().str.lower()

    return values.isin([
        "true", "1", "yes", "y"
    ])


def validate_unique_ids(data, id_col, description):
    if data[id_col].isna().any():
        raise ValueError(
            f"Missing player IDs in {description}."
        )

    duplicates = data[data[id_col].duplicated(keep=False)]

    if not duplicates.empty:
        raise ValueError(
            f"Duplicate player IDs found in {description}.\n"
            f"{duplicates[[id_col]].head(10)}"
        )


def prepare_format_data(
    data,
    player_type,
    format_name
):
    """
    Standardize the different IPL and T20I schemas.
    """

    data = data.copy()

    if player_type == "Batter":

        id_col = "striker_id"

        if format_name == "IPL":
            name_col = first_available_column(
                data,
                ["player_name", "striker_name"],
                "IPL batter name"
            )

            rank_col = "final_rank"
            rating_col = "rating_primary"

            improvement_col = first_available_column(
                data,
                ["strike_rate_difference",
                 "strike_rate_improvement"],
                "IPL batter strike-rate improvement"
            )

            dismissal_col = first_available_column(
                data,
                ["dismissal_rate_difference_y",
                 "dismissal_improvement",
                 "dismissal_rate_difference_x"],
                "IPL batter dismissal-rate improvement"
            )

            eligible_col = "eligible"

        else:
            name_col = "striker_name"
            rank_col = "rank"
            rating_col = "rating"

            improvement_col = "strike_rate_improvement"
            dismissal_col = "dismissal_rate_improvement"

            eligible_col = None

    else:

        id_col = "bowler_id"

        if format_name == "IPL":
            name_col = first_available_column(
                data,
                ["bowler_name", "player_name"],
                "IPL bowler name"
            )

            rank_col = "final_rank"
            rating_col = "rating_primary"

            improvement_col = "economy_improvement"

            dismissal_col = first_available_column(
                data,
                ["pressure_wickets_per_100_balls",
                 "wickets_per_100_pressure_balls"],
                "IPL bowler pressure wickets per 100 balls"
            )

            eligible_col = "eligible"

        else:
            name_col = "bowler_name"
            rank_col = "rank"
            rating_col = "rating"

            improvement_col = "economy_improvement"

            dismissal_col = "pressure_wickets_per_100_balls"

            eligible_col = None

    required = [
        id_col,
        name_col,
        rank_col,
        rating_col,
        improvement_col,
        dismissal_col
    ]

    for column in required:
        if column not in data.columns:
            raise ValueError(
                f"{format_name} {player_type}: "
                f"missing required column '{column}'"
            )

    if eligible_col is not None:
        if eligible_col not in data.columns:
            raise ValueError(
                f"{format_name} {player_type}: "
                f"missing eligibility column '{eligible_col}'"
            )

        data = data[
            convert_eligible(data[eligible_col])
        ].copy()

    result = pd.DataFrame()

    result["player_id"] = clean_player_id(
        data[id_col]
    )

    result["player_name"] = data[name_col].astype("string")

    result["rank"] = pd.to_numeric(
        data[rank_col], errors="coerce"
    )

    result["rating"] = pd.to_numeric(
        data[rating_col], errors="coerce"
    )

    result["pressure_performance_improvement"] = pd.to_numeric(
        data[improvement_col], errors="coerce"
    )

    result["secondary_pressure_metric"] = pd.to_numeric(
        data[dismissal_col], errors="coerce"
    )

    # Preserve available exposure information.

    exposure_columns = (
        [
            "matches_pressure",
            "matches_normal",
            "balls_pressure",
            "balls_normal"
        ]
        if player_type == "Batter"
        else [
            "matches_pressure",
            "matches_normal",
            "legal_balls_pressure",
            "legal_balls_normal"
        ]
    )

    for column in exposure_columns:
        if column in data.columns:
            result[column] = pd.to_numeric(
                data[column], errors="coerce"
            )

    result["format"] = format_name

    result = result.dropna(
        subset=["player_id", "rank", "rating"]
    ).copy()

    result["player_id"] = result["player_id"].astype("string")

    validate_unique_ids(
        result,
        "player_id",
        f"{format_name} {player_type} rankings"
    )

    result["rank"] = result["rank"].astype(int)

    result["name_normalized"] = normalize_name(
        result["player_name"]
    )

    return result.reset_index(drop=True)


# ============================================================
# 3. LOAD ORIGINAL DATA
# ============================================================

ipl_batters_raw = pd.read_csv(FILES["ipl_batters"])
ipl_bowlers_raw = pd.read_csv(FILES["ipl_bowlers"])

t20i_batters_raw = pd.read_csv(FILES["t20i_batters"])
t20i_bowlers_raw = pd.read_csv(FILES["t20i_bowlers"])

print("\nRaw records:")
print("IPL batters:", len(ipl_batters_raw))
print("IPL bowlers:", len(ipl_bowlers_raw))
print("T20I batters:", len(t20i_batters_raw))
print("T20I bowlers:", len(t20i_bowlers_raw))


# ============================================================
# 4. STANDARDIZE THE FOUR DATASETS
# ============================================================

ipl_batters = prepare_format_data(
    ipl_batters_raw,
    "Batter",
    "IPL"
)

ipl_bowlers = prepare_format_data(
    ipl_bowlers_raw,
    "Bowler",
    "IPL"
)

t20i_batters = prepare_format_data(
    t20i_batters_raw,
    "Batter",
    "T20I"
)

t20i_bowlers = prepare_format_data(
    t20i_bowlers_raw,
    "Bowler",
    "T20I"
)

print("\nEligible records after standardization:")
print("IPL batters:", len(ipl_batters))
print("IPL bowlers:", len(ipl_bowlers))
print("T20I batters:", len(t20i_batters))
print("T20I bowlers:", len(t20i_bowlers))


# ============================================================
# 5. CROSS-FORMAT COMPARISON FUNCTION
# ============================================================

def compare_formats(
    ipl_data,
    t20i_data,
    player_type
):

    print("\n" + "-" * 85)
    print(f"COMPARING {player_type.upper()}S")
    print("-" * 85)

    ipl_data = ipl_data.copy()
    t20i_data = t20i_data.copy()

    ipl_population = len(ipl_data)
    t20i_population = len(t20i_data)

    # --------------------------------------------------------
    # Calculate relative ranking position within each format.
    # These are not combined ratings.
    # --------------------------------------------------------

    if ipl_population > 1:
        ipl_data["rank_percentile"] = (
            (ipl_population - ipl_data["rank"])
            / (ipl_population - 1)
        ) * 100
    else:
        ipl_data["rank_percentile"] = 100.0

    if t20i_population > 1:
        t20i_data["rank_percentile"] = (
            (t20i_population - t20i_data["rank"])
            / (t20i_population - 1)
        ) * 100
    else:
        t20i_data["rank_percentile"] = 100.0

    # --------------------------------------------------------
    # Prefix columns to preserve the format distinction.
    # --------------------------------------------------------

    ipl_rename = {
        column: "ipl_" + column
        for column in ipl_data.columns
        if column not in ["player_id"]
    }

    t20i_rename = {
        column: "t20i_" + column
        for column in t20i_data.columns
        if column not in ["player_id"]
    }

    ipl_data = ipl_data.rename(columns=ipl_rename)
    t20i_data = t20i_data.rename(columns=t20i_rename)

    # --------------------------------------------------------
    # Match using player ID only.
    # --------------------------------------------------------

    comparison = ipl_data.merge(
        t20i_data,
        on="player_id",
        how="outer",
        indicator=True,
        validate="one_to_one"
    )

    comparison["available_in_ipl"] = (
        comparison["_merge"].isin(["both", "left_only"])
    )

    comparison["available_in_t20i"] = (
        comparison["_merge"].isin(["both", "right_only"])
    )

    comparison["identity_name_match"] = pd.NA

    matched_mask = comparison["_merge"] == "both"

    comparison.loc[
        matched_mask,
        "identity_name_match"
    ] = (
        comparison.loc[
            matched_mask,
            "ipl_name_normalized"
        ]
        ==
        comparison.loc[
            matched_mask,
            "t20i_name_normalized"
        ]
    )

    # --------------------------------------------------------
    # Identity verification.
    # --------------------------------------------------------

    comparison["identity_status"] = np.select(
        [
            comparison["_merge"] == "left_only",
            comparison["_merge"] == "right_only",
            comparison["identity_name_match"] == True,
            comparison["identity_name_match"] == False
        ],
        [
            "IPL_ONLY",
            "T20I_ONLY",
            "ID_AND_NAME_MATCH",
            "ID_MATCH_NAME_CONFLICT"
        ],
        default="REVIEW"
    )

    # --------------------------------------------------------
    # Top 10 evidence.
    # --------------------------------------------------------

    comparison["ipl_top10"] = (
        comparison["ipl_rank"] <= 10
    ).fillna(False)

    comparison["t20i_top10"] = (
        comparison["t20i_rank"] <= 10
    ).fillna(False)

    comparison["cross_format_evidence"] = np.select(
        [
            (
                comparison["ipl_top10"]
                & comparison["t20i_top10"]
            ),
            (
                comparison["ipl_top10"]
                & ~comparison["t20i_top10"]
                & comparison["available_in_t20i"]
            ),
            (
                ~comparison["ipl_top10"]
                & comparison["t20i_top10"]
                & comparison["available_in_ipl"]
            ),
            (
                comparison["available_in_ipl"]
                & comparison["available_in_t20i"]
            ),
            comparison["available_in_ipl"],
            comparison["available_in_t20i"]
        ],
        [
            "TOP10_BOTH_FORMATS",
            "TOP10_IPL_ONLY",
            "TOP10_T20I_ONLY",
            "ELIGIBLE_BOTH_OUTSIDE_TOP10",
            "IPL_ONLY_NO_T20I_ELIGIBILITY",
            "T20I_ONLY_NO_IPL_ELIGIBILITY"
        ],
        default="REVIEW"
    )

    # A name conflict must not be presented as confirmed
    # cross-format evidence, even if the numeric IDs match.

    conflict_mask = (
        comparison["identity_status"]
        == "ID_MATCH_NAME_CONFLICT"
    )

    comparison.loc[
        conflict_mask,
        "cross_format_evidence"
    ] = "IDENTITY_CONFLICT_REVIEW"

    # --------------------------------------------------------
    # Rank percentile difference.
    # Positive = relatively higher IPL position.
    # Negative = relatively higher T20I position.
    # --------------------------------------------------------

    comparison["ipl_minus_t20i_rank_percentile"] = (
        comparison["ipl_rank_percentile"]
        - comparison["t20i_rank_percentile"]
    )

    # --------------------------------------------------------
    # Export detailed comparison.
    # --------------------------------------------------------

    output_file = (
        REPORTS
        / f"cross_format_{player_type.lower()}_comparison.csv"
    )

    comparison.to_csv(output_file, index=False)

    # --------------------------------------------------------
    # Export matched players.
    # --------------------------------------------------------

    matched = comparison[
        comparison["_merge"] == "both"
    ].copy()

    matched_file = (
        REPORTS
        / f"cross_format_{player_type.lower()}_matched.csv"
    )

    matched.to_csv(matched_file, index=False)

    # --------------------------------------------------------
    # Export unmatched players.
    # --------------------------------------------------------

    unmatched = comparison[
        comparison["_merge"] != "both"
    ].copy()

    unmatched_file = (
        REPORTS
        / f"cross_format_{player_type.lower()}_unmatched.csv"
    )

    unmatched.to_csv(unmatched_file, index=False)

    # --------------------------------------------------------
    # Export identity conflicts.
    # --------------------------------------------------------

    conflicts = comparison[
        comparison["identity_status"]
        == "ID_MATCH_NAME_CONFLICT"
    ].copy()

    conflict_file = (
        REPORTS
        / f"cross_format_{player_type.lower()}_identity_conflicts.csv"
    )

    conflicts.to_csv(conflict_file, index=False)

    # --------------------------------------------------------
    # Summary.
    # --------------------------------------------------------

    summary = {
        "player_type": player_type,
        "ipl_eligible_players": ipl_population,
        "t20i_eligible_players": t20i_population,
        "matched_player_ids": len(matched),
        "unmatched_ipl_players": int(
            (comparison["_merge"] == "left_only").sum()
        ),
        "unmatched_t20i_players": int(
            (comparison["_merge"] == "right_only").sum()
        ),
        "confirmed_id_and_name_matches": int(
            (comparison["identity_status"]
             == "ID_AND_NAME_MATCH").sum()
        ),
        "identity_conflicts": len(conflicts),
        "top10_both_formats": int(
            (
                comparison["cross_format_evidence"]
                == "TOP10_BOTH_FORMATS"
            ).sum()
        ),
        "top10_ipl_only": int(
            (
                comparison["cross_format_evidence"]
                == "TOP10_IPL_ONLY"
            ).sum()
        ),
        "top10_t20i_only": int(
            (
                comparison["cross_format_evidence"]
                == "TOP10_T20I_ONLY"
            ).sum()
        )
    }

    print("\nComparison summary:")
    for key, value in summary.items():
        print(f"{key}: {value}")

    print("\nCross-format evidence categories:")
    print(
        comparison["cross_format_evidence"]
        .value_counts(dropna=False)
        .to_string()
    )

    if not conflicts.empty:
        print("\nWARNING: Identity conflicts found.")
        print(
            conflicts[
                [
                    "player_id",
                    "ipl_player_name",
                    "t20i_player_name"
                ]
            ].to_string(index=False)
        )

    return comparison, summary


# ============================================================
# 6. COMPARE BATTERS
# ============================================================

batter_comparison, batter_summary = compare_formats(
    ipl_batters,
    t20i_batters,
    "Batter"
)


# ============================================================
# 7. COMPARE BOWLERS
# ============================================================

bowler_comparison, bowler_summary = compare_formats(
    ipl_bowlers,
    t20i_bowlers,
    "Bowler"
)


# ============================================================
# 8. CREATE COMBINED SUMMARY
# ============================================================

summary = pd.DataFrame([
    batter_summary,
    bowler_summary
])

summary.to_csv(
    REPORTS / "cross_format_comparison_summary.csv",
    index=False
)


# ============================================================
# 9. CREATE CROSS-FORMAT TOP-10 EVIDENCE REPORT
# ============================================================

top10_evidence = []

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
    ].copy()

    for _, row in selected.iterrows():

        top10_evidence.append({
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

top10_evidence_df = pd.DataFrame(top10_evidence)

top10_evidence_df.to_csv(
    REPORTS / "cross_format_top10_evidence.csv",
    index=False
)


# ============================================================
# 10. DISPLAY TOP CROSS-FORMAT EVIDENCE
# ============================================================

print("\n" + "=" * 85)
print("PLAYERS WITH TOP-10 EVIDENCE IN EITHER FORMAT")
print("=" * 85)

if top10_evidence_df.empty:
    print("No confirmed cross-format top-10 matches found.")
else:
    print(
        top10_evidence_df.sort_values(
            ["player_type", "ipl_rank", "t20i_rank"],
            na_position="last"
        ).round(2).to_string(index=False)
    )


# ============================================================
# 11. FINAL SUMMARY
# ============================================================

print("\n" + "=" * 85)
print("STEP 67 COMPLETED")
print("=" * 85)

print("\nGenerated reports:")

output_files = [
    "cross_format_comparison_summary.csv",
    "cross_format_top10_evidence.csv",
    "cross_format_batter_comparison.csv",
    "cross_format_batter_matched.csv",
    "cross_format_batter_unmatched.csv",
    "cross_format_batter_identity_conflicts.csv",
    "cross_format_bowler_comparison.csv",
    "cross_format_bowler_matched.csv",
    "cross_format_bowler_unmatched.csv",
    "cross_format_bowler_identity_conflicts.csv"
]

for filename in output_files:
    print(" -", filename)

print("\nIMPORTANT:")
print("IPL and T20I ratings remain separate.")
print("No combined rating has been calculated.")
print("Player matching uses IDs, with name verification.")
print("Missing T20I eligibility is not treated as poor performance.")

print("\nSTEP 67 FINISHED.")
