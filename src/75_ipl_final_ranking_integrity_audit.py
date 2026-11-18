
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"

TOP_N = 10
TOLERANCE = 0.000001

WEIGHTS = {
    "performance": 0.30,
    "risk": 0.25,
    "consistency": 0.30,
    "sample": 0.15
}


def check_file(filename):
    path = REPORTS / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Required file not found: {path}"
        )

    return path


def require_columns(df, columns, filename):
    missing = [c for c in columns if c not in df.columns]

    if missing:
        raise ValueError(
            f"{filename} is missing columns: {missing}"
        )


def numeric(df, columns):
    for col in columns:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )


def percentile(series):
    return (
        pd.to_numeric(series, errors="coerce")
        .rank(
            pct=True,
            ascending=True,
            method="average"
        ) * 100
    )


def sample_strength(matches, balls):
    matches = pd.to_numeric(
        matches, errors="coerce"
    ).fillna(0)

    balls = pd.to_numeric(
        balls, errors="coerce"
    ).fillna(0)

    match_score = (matches / 20).clip(upper=1)
    ball_score = (balls / 300).clip(upper=1)

    return (
        0.60 * match_score
        + 0.40 * ball_score
    ) * 100


def compare_scores(expected, actual):
    expected = pd.to_numeric(
        expected, errors="coerce"
    )

    actual = pd.to_numeric(
        actual, errors="coerce"
    )

    return (
        expected.notna()
        & actual.notna()
        & ((expected - actual).abs() <= TOLERANCE)
    )


def audit_batters():
    print("\n" + "=" * 80)
    print("BATTER INDEPENDENT VERIFICATION")
    print("=" * 80)

    source_file = "batter_final_metric_dataset.csv"
    rating_file = "batter_reliability_ratings_revised.csv"
    top_file = "batter_ipl_top10_revised.csv"

    df = pd.read_csv(check_file(source_file))
    saved = pd.read_csv(check_file(rating_file))
    top = pd.read_csv(check_file(top_file))

    required = [
        "striker_id",
        "striker_name",
        "qualifying_matches",
        "consistency_pressure_balls",
        "matches_normal",
        "balls_normal",
        "strike_rate_difference",
        "dismissal_rate_difference_y",
        "consistency_percentage"
    ]

    require_columns(df, required, source_file)

    numeric_columns = [
        "qualifying_matches",
        "consistency_pressure_balls",
        "matches_normal",
        "balls_normal",
        "strike_rate_difference",
        "dismissal_rate_difference_y",
        "consistency_percentage"
    ]

    numeric(df, numeric_columns)

    df["eligible_check"] = (
        (df["qualifying_matches"] >= 8)
        & (df["consistency_pressure_balls"] >= 100)
        & (df["matches_normal"] >= 8)
        & (df["balls_normal"] >= 100)
    )

    eligible = df[df["eligible_check"]].copy()

    eligible["performance_metric"] = (
        eligible["strike_rate_difference"]
    )

    eligible["risk_metric"] = (
        -eligible["dismissal_rate_difference_y"]
    )

    eligible["performance_score"] = percentile(
        eligible["performance_metric"]
    )

    eligible["risk_score"] = percentile(
        eligible["risk_metric"]
    )

    eligible["consistency_score"] = percentile(
        eligible["consistency_percentage"]
    )

    eligible["sample_score"] = sample_strength(
        eligible["qualifying_matches"],
        eligible["consistency_pressure_balls"]
    )

    eligible["expected_rating"] = (
        eligible["performance_score"] * WEIGHTS["performance"]
        + eligible["risk_score"] * WEIGHTS["risk"]
        + eligible["consistency_score"] * WEIGHTS["consistency"]
        + eligible["sample_score"] * WEIGHTS["sample"]
    )

    eligible = eligible.sort_values(
        "expected_rating",
        ascending=False
    ).reset_index(drop=True)

    eligible["expected_rank"] = (
        np.arange(1, len(eligible) + 1)
    )

    saved_columns = [
        "striker_id",
        "final_rank",
        "rating_primary"
    ]

    require_columns(saved, saved_columns, rating_file)

    check = eligible.merge(
        saved[saved_columns],
        on="striker_id",
        how="left",
        validate="one_to_one"
    )

    check["rating_matches"] = compare_scores(
        check["expected_rating"],
        check["rating_primary"]
    )

    check["rank_matches"] = (
        check["expected_rank"] == check["final_rank"]
    )

    check["integrity_status"] = np.where(
        check["rating_matches"] & check["rank_matches"],
        "PASS",
        "FAIL"
    )

    check.to_csv(
        REPORTS / "ipl_batter_independent_audit.csv",
        index=False
    )

    top_check = check.nsmallest(
        TOP_N,
        "expected_rank"
    )

    print("Source population:", len(df))
    print("Recalculated eligible batters:", len(eligible))
    print("Saved eligible batters:", len(saved))

    print(
        "Rating matches:",
        int(check["rating_matches"].sum()),
        "/",
        len(check)
    )

    print(
        "Rank matches:",
        int(check["rank_matches"].sum()),
        "/",
        len(check)
    )

    print("\nINDEPENDENTLY VERIFIED BATTER TOP 10")

    print(
        top_check[
            [
                "expected_rank",
                "striker_name",
                "expected_rating",
                "rating_primary",
                "qualifying_matches",
                "consistency_pressure_balls",
                "matches_normal",
                "balls_normal",
                "strike_rate_difference",
                "dismissal_rate_difference_y",
                "consistency_percentage",
                "integrity_status"
            ]
        ].to_string(index=False)
    )

    top_ids = set(top["striker_id"])
    recalculated_ids = set(
        top_check["striker_id"]
    )

    print(
        "\nSaved top 10 matches recalculated top 10:",
        top_ids == recalculated_ids
    )

    return {
        "player_type": "Batter",
        "source_population": len(df),
        "eligible_population": len(eligible),
        "rating_failures": int(
            (~check["rating_matches"]).sum()
        ),
        "rank_failures": int(
            (~check["rank_matches"]).sum()
        ),
        "top10_match": top_ids == recalculated_ids
    }


def audit_bowlers():
    print("\n" + "=" * 80)
    print("BOWLER INDEPENDENT VERIFICATION")
    print("=" * 80)

    source_file = "bowler_final_metric_dataset.csv"
    rating_file = "bowler_reliability_ratings_revised.csv"
    top_file = "bowler_ipl_top10_revised.csv"

    df = pd.read_csv(check_file(source_file))
    saved = pd.read_csv(check_file(rating_file))
    top = pd.read_csv(check_file(top_file))

    required = [
        "bowler_id",
        "bowler_name",
        "qualifying_matches",
        "pressure_legal_balls",
        "matches_normal",
        "legal_balls_normal",
        "economy_difference",
        "wickets_pressure",
        "legal_balls_pressure",
        "consistency_percentage"
    ]

    require_columns(df, required, source_file)

    numeric_columns = [
        "qualifying_matches",
        "pressure_legal_balls",
        "matches_normal",
        "legal_balls_normal",
        "economy_difference",
        "wickets_pressure",
        "legal_balls_pressure",
        "consistency_percentage"
    ]

    numeric(df, numeric_columns)

    df["eligible_check"] = (
        (df["qualifying_matches"] >= 8)
        & (df["pressure_legal_balls"] >= 120)
        & (df["matches_normal"] >= 8)
        & (df["legal_balls_normal"] >= 180)
    )

    eligible = df[df["eligible_check"]].copy()

    eligible["performance_metric"] = (
        -eligible["economy_difference"]
    )

    eligible["risk_metric"] = (
        eligible["wickets_pressure"]
        / eligible["legal_balls_pressure"]
        * 100
    )

    eligible["performance_score"] = percentile(
        eligible["performance_metric"]
    )

    eligible["risk_score"] = percentile(
        eligible["risk_metric"]
    )

    eligible["consistency_score"] = percentile(
        eligible["consistency_percentage"]
    )

    eligible["sample_score"] = sample_strength(
        eligible["qualifying_matches"],
        eligible["pressure_legal_balls"]
    )

    eligible["expected_rating"] = (
        eligible["performance_score"] * WEIGHTS["performance"]
        + eligible["risk_score"] * WEIGHTS["risk"]
        + eligible["consistency_score"] * WEIGHTS["consistency"]
        + eligible["sample_score"] * WEIGHTS["sample"]
    )

    eligible = eligible.sort_values(
        "expected_rating",
        ascending=False
    ).reset_index(drop=True)

    eligible["expected_rank"] = (
        np.arange(1, len(eligible) + 1)
    )

    saved_columns = [
        "bowler_id",
        "final_rank",
        "rating_primary"
    ]

    require_columns(saved, saved_columns, rating_file)

    check = eligible.merge(
        saved[saved_columns],
        on="bowler_id",
        how="left",
        validate="one_to_one"
    )

    check["rating_matches"] = compare_scores(
        check["expected_rating"],
        check["rating_primary"]
    )

    check["rank_matches"] = (
        check["expected_rank"] == check["final_rank"]
    )

    check["integrity_status"] = np.where(
        check["rating_matches"] & check["rank_matches"],
        "PASS",
        "FAIL"
    )

    check.to_csv(
        REPORTS / "ipl_bowler_independent_audit.csv",
        index=False
    )

    top_check = check.nsmallest(
        TOP_N,
        "expected_rank"
    )

    print("Source population:", len(df))
    print("Recalculated eligible bowlers:", len(eligible))
    print("Saved eligible bowlers:", len(saved))

    print(
        "Rating matches:",
        int(check["rating_matches"].sum()),
        "/",
        len(check)
    )

    print(
        "Rank matches:",
        int(check["rank_matches"].sum()),
        "/",
        len(check)
    )

    print("\nINDEPENDENTLY VERIFIED BOWLER TOP 10")

    print(
        top_check[
            [
                "expected_rank",
                "bowler_name",
                "expected_rating",
                "rating_primary",
                "qualifying_matches",
                "pressure_legal_balls",
                "matches_normal",
                "legal_balls_normal",
                "economy_difference",
                "wickets_pressure",
                "legal_balls_pressure",
                "consistency_percentage",
                "integrity_status"
            ]
        ].to_string(index=False)
    )

    top_ids = set(top["bowler_id"])
    recalculated_ids = set(
        top_check["bowler_id"]
    )

    print(
        "\nSaved top 10 matches recalculated top 10:",
        top_ids == recalculated_ids
    )

    return {
        "player_type": "Bowler",
        "source_population": len(df),
        "eligible_population": len(eligible),
        "rating_failures": int(
            (~check["rating_matches"]).sum()
        ),
        "rank_failures": int(
            (~check["rank_matches"]).sum()
        ),
        "top10_match": top_ids == recalculated_ids
    }


def main():
    print("=" * 80)
    print("STEP 75: IPL FINAL RANKING INTEGRITY AUDIT")
    print("=" * 80)

    results = []

    results.append(audit_batters())
    results.append(audit_bowlers())

    summary = pd.DataFrame(results)

    summary["overall_status"] = np.where(
        (summary["rating_failures"] == 0)
        & (summary["rank_failures"] == 0)
        & summary["top10_match"],
        "PASS",
        "REVIEW REQUIRED"
    )

    summary.to_csv(
        REPORTS / "ipl_final_ranking_integrity_summary.csv",
        index=False
    )

    print("\n" + "=" * 80)
    print("FINAL AUDIT SUMMARY")
    print("=" * 80)

    print(summary.to_string(index=False))

    if (summary["overall_status"] == "PASS").all():
        print("\nALL IPL RANKING CHECKS PASSED.")
    else:
        print("\nWARNING: INVESTIGATE THE FAILED CHECKS.")

    print("\nGenerated files:")
    print("reports/ipl_batter_independent_audit.csv")
    print("reports/ipl_bowler_independent_audit.csv")
    print("reports/ipl_final_ranking_integrity_summary.csv")


if __name__ == "__main__":
    main()
