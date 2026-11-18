from pathlib import Path
from datetime import datetime

import pandas as pd


# ============================================================
# STEP 75: FINAL RR HACKATHON SUBMISSION REPORT (REVISED)
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"
REPORTS.mkdir(exist_ok=True)

FILES = {
    # Revised IPL top-10 rankings from Step 73
    "ipl_batters": REPORTS / "batter_ipl_top10_revised.csv",
    "ipl_bowlers": REPORTS / "bowler_ipl_top10_revised.csv",

    # Primary T20I top-10 rankings
    "t20i_batters": REPORTS / "t20i_batter_top10.csv",
    "t20i_bowlers": REPORTS / "t20i_bowler_top10.csv",

    # Revised cross-format results from Step 74
    "cross_summary": REPORTS / "cross_format_revised_comparison_summary.csv",
    "cross_evidence": REPORTS / "cross_format_revised_top10_evidence.csv",

    # T20I eligibility sensitivity from Step 64
    "threshold_summary": REPORTS / "t20i_eligibility_scenario_summary.csv",
    "threshold_overlap": REPORTS / "t20i_eligibility_overlap.csv",

    # Revised IPL eligible rating populations from Step 73
    "ipl_batter_ratings": REPORTS / "batter_reliability_ratings_revised.csv",
    "ipl_bowler_ratings": REPORTS / "bowler_reliability_ratings_revised.csv",

    # Primary T20I eligible rating populations
    "t20i_batter_ratings": REPORTS / "t20i_batter_ratings_primary.csv",
    "t20i_bowler_ratings": REPORTS / "t20i_bowler_ratings_primary.csv",

    # Revised IPL eligibility audit
    "ipl_batter_eligibility": REPORTS / "batter_revised_eligibility_audit.csv",
    "ipl_bowler_eligibility": REPORTS / "bowler_revised_eligibility_audit.csv",
}

OUTPUT_REPORT = REPORTS / "FINAL_RR_HACKATHON_METHODOLOGY_REPORT.md"

print("\n" + "=" * 90)
print("STEP 75: FINAL RR HACKATHON SUBMISSION REPORT — REVISED MODEL")
print("=" * 90)


# ============================================================
# 1. REQUIRED INPUT VALIDATION
# ============================================================

required_keys = [
    "ipl_batters",
    "ipl_bowlers",
    "t20i_batters",
    "t20i_bowlers",
    "cross_summary",
    "cross_evidence",
    "ipl_batter_ratings",
    "ipl_bowler_ratings",
    "t20i_batter_ratings",
    "t20i_bowler_ratings",
    "ipl_batter_eligibility",
    "ipl_bowler_eligibility",
]

missing_files = [
    str(FILES[key])
    for key in required_keys
    if not FILES[key].exists()
]

if missing_files:
    print("\nMissing required files:")
    for filename in missing_files:
        print(" -", filename)
    raise FileNotFoundError(
        "Complete Steps 73 and 74 and verify the required report files."
    )

print("\nAll required ranking, rating, cross-format and eligibility files found.")

optional_files = [
    "threshold_summary",
    "threshold_overlap",
]

for key in optional_files:
    if not FILES[key].exists():
        print(f"OPTIONAL FILE NOT FOUND: {FILES[key].name}")


# ============================================================
# 2. GENERAL HELPERS
# ============================================================

def find_column(data, candidates, description):
    for column in candidates:
        if column in data.columns:
            return column
    raise ValueError(
        f"Could not find {description}. "
        f"Expected one of {candidates}. "
        f"Available columns: {data.columns.tolist()}"
    )


def load_csv(key):
    return pd.read_csv(FILES[key])


def format_number(value, decimals=2):
    if pd.isna(value):
        return "N/A"
    return f"{float(value):,.{decimals}f}"


def markdown_table(data, columns=None):
    if columns is not None:
        available = [c for c in columns if c in data.columns]
        data = data[available].copy()

    if data.empty:
        return "_No records available._"

    headers = list(data.columns)
    lines = [
        "| " + " | ".join(str(x) for x in headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |"
    ]

    for _, row in data.iterrows():
        values = []
        for value in row:
            if pd.isna(value):
                values.append("N/A")
            else:
                values.append(str(value).replace("|", "/").replace("\n", " "))
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def clean_player_id(series):
    values = series.astype("string").str.strip()
    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.notna()
    values.loc[valid] = (
        numeric.loc[valid].astype("Int64").astype("string")
    )
    return values


# ============================================================
# 3. STANDARDIZE TOP-10 RANKINGS
# ============================================================

def standardize_top10(file_key, player_type, format_name):
    data = load_csv(file_key)

    if player_type == "Batter":
        name_candidates = ["player_name", "striker_name", "batter_name"]
        id_candidates = ["striker_id", "batter_id", "player_id"]
    else:
        name_candidates = ["player_name", "bowler_name"]
        id_candidates = ["bowler_id", "player_id"]

    name_col = find_column(
        data, name_candidates, f"{format_name} {player_type} name"
    )
    id_col = find_column(
        data, id_candidates, f"{format_name} {player_type} ID"
    )

    rank_candidates = (
        ["final_rank", "rank_primary", "rank"]
        if format_name == "IPL"
        else ["rank", "final_rank", "t20i_rank"]
    )
    rating_candidates = (
        ["rating_primary", "rating"]
        if format_name == "IPL"
        else ["rating", "rating_primary", "reliability_rating"]
    )

    rank_col = find_column(data, rank_candidates, f"{format_name} rank")
    rating_col = find_column(data, rating_candidates, f"{format_name} rating")

    result = pd.DataFrame({
        "rank": pd.to_numeric(data[rank_col], errors="coerce"),
        "player_id": clean_player_id(data[id_col]),
        "player_name": data[name_col].astype("string").str.strip(),
        "rating": pd.to_numeric(data[rating_col], errors="coerce"),
    })

    result = result.dropna(
        subset=["rank", "player_id", "player_name", "rating"]
    ).copy()

    result["rank"] = result["rank"].astype(int)
    result = result.sort_values("rank").reset_index(drop=True)

    if len(result) != 10:
        raise ValueError(
            f"{format_name} {player_type} top 10 has "
            f"{len(result)} rows, expected exactly 10."
        )

    if result["player_id"].duplicated().any():
        raise ValueError(
            f"Duplicate player IDs in {format_name} {player_type} top 10."
        )

    if result["rank"].tolist() != list(range(1, 11)):
        raise ValueError(
            f"{format_name} {player_type} ranks are not exactly 1 to 10."
        )

    result.insert(0, "format", format_name)
    result.insert(1, "player_type", player_type)
    return result


# ============================================================
# 4. LOAD THE FINAL RANKINGS
# ============================================================

ipl_batter_top10 = standardize_top10("ipl_batters", "Batter", "IPL")
ipl_bowler_top10 = standardize_top10("ipl_bowlers", "Bowler", "IPL")
t20i_batter_top10 = standardize_top10("t20i_batters", "Batter", "T20I")
t20i_bowler_top10 = standardize_top10("t20i_bowlers", "Bowler", "T20I")

print("\nFINAL TOP-10 VALIDATION")
print("Revised IPL batters:", len(ipl_batter_top10))
print("Revised IPL bowlers:", len(ipl_bowler_top10))
print("T20I supporting batters:", len(t20i_batter_top10))
print("T20I supporting bowlers:", len(t20i_bowler_top10))


# ============================================================
# 5. LOAD AND VALIDATE ELIGIBLE POPULATIONS
# ============================================================

ipl_batter_ratings = load_csv("ipl_batter_ratings")
ipl_bowler_ratings = load_csv("ipl_bowler_ratings")
t20i_batter_ratings = load_csv("t20i_batter_ratings")
t20i_bowler_ratings = load_csv("t20i_bowler_ratings")

population_counts = {
    "Revised IPL batters": len(ipl_batter_ratings),
    "Revised IPL bowlers": len(ipl_bowler_ratings),
    "Primary T20I batters": len(t20i_batter_ratings),
    "Primary T20I bowlers": len(t20i_bowler_ratings),
}

expected_populations = {
    "Revised IPL batters": 32,
    "Revised IPL bowlers": 49,
    "Primary T20I batters": 41,
    "Primary T20I bowlers": 62,
}

print("\nELIGIBLE POPULATION VALIDATION")
for label, actual in population_counts.items():
    expected = expected_populations[label]
    print(f"{label}: {actual} (expected {expected})")
    if actual != expected:
        raise ValueError(
            f"{label}: expected {expected}, found {actual}."
        )


# ============================================================
# 6. EXPORT CLEAN FINAL RANKING TABLES
# ============================================================

output_rankings = {
    "final_ipl_batter_top10.csv": ipl_batter_top10,
    "final_ipl_bowler_top10.csv": ipl_bowler_top10,
    "final_t20i_batter_supporting_top10.csv": t20i_batter_top10,
    "final_t20i_bowler_supporting_top10.csv": t20i_bowler_top10,
}

for filename, dataframe in output_rankings.items():
    dataframe.to_csv(REPORTS / filename, index=False)

all_rankings = pd.concat(
    [
        ipl_batter_top10,
        ipl_bowler_top10,
        t20i_batter_top10,
        t20i_bowler_top10,
    ],
    ignore_index=True,
)

all_rankings.to_csv(
    REPORTS / "final_all_top10_rankings.csv",
    index=False
)


# ============================================================
# 7. CROSS-FORMAT VALIDATION
# ============================================================

cross_summary = load_csv("cross_summary")
cross_evidence = load_csv("cross_evidence")

required_summary_columns = {
    "player_type",
    "ipl_eligible_players",
    "t20i_eligible_players",
    "matched_player_ids",
    "identity_conflicts",
    "top10_both_formats",
    "top10_ipl_only",
    "top10_t20i_only",
}
missing = required_summary_columns - set(cross_summary.columns)
if missing:
    raise ValueError(
        f"Cross-format summary missing columns: {sorted(missing)}"
    )

if int(cross_summary["identity_conflicts"].sum()) != 0:
    raise ValueError(
        "Identity conflicts exist in cross-format results. "
        "Resolve them before producing the final report."
    )

cross_columns = [
    "player_type",
    "player_name",
    "ipl_rank",
    "ipl_rating",
    "t20i_rank",
    "t20i_rating",
    "cross_format_evidence",
]
missing = [c for c in cross_columns if c not in cross_evidence.columns]
if missing:
    raise ValueError(
        f"Cross-format evidence missing columns: {missing}"
    )

cross_table_data = cross_evidence[cross_columns].copy()
cross_table_data = cross_table_data.sort_values(
    ["player_type", "ipl_rank", "t20i_rank"],
    na_position="last"
)

for column in ["ipl_rating", "t20i_rating"]:
    cross_table_data[column] = cross_table_data[column].map(
        lambda value: format_number(value)
    )

cross_table = markdown_table(cross_table_data)


# ============================================================
# 8. T20I SENSITIVITY TABLES (OPTIONAL)
# ============================================================

threshold_summary = None
threshold_overlap = None

if FILES["threshold_summary"].exists():
    threshold_summary = pd.read_csv(FILES["threshold_summary"])

if FILES["threshold_overlap"].exists():
    threshold_overlap = pd.read_csv(FILES["threshold_overlap"])

if threshold_summary is not None:
    sensitivity_table = markdown_table(threshold_summary)
else:
    sensitivity_table = (
        "_T20I threshold sensitivity results are retained in the "
        "separate Step 64 and Step 66 CSV reports. The expected "
        "summary file was not present when this report was generated._"
    )

if threshold_overlap is not None:
    overlap_table = markdown_table(threshold_overlap)
else:
    overlap_table = (
        "_T20I ranking-overlap results are retained in the separate "
        "Step 64 and Step 66 CSV reports. The expected overlap file "
        "was not present when this report was generated._"
    )


# ============================================================
# 9. REVISED IPL ELIGIBILITY DESCRIPTION
# ============================================================

ipl_batter_eligibility = load_csv("ipl_batter_eligibility")
ipl_bowler_eligibility = load_csv("ipl_bowler_eligibility")

# Step 73 revised batter population includes a normal-exposure
# requirement in addition to the original pressure-exposure rule.
# The Step 71 sensitivity run established that >=100 normal balls
# with >=8 normal matches leaves 32 eligible batters.
#
# The bowler population remains 49; Step 72 tested normal legal-ball
# thresholds of 90, 120 and 180 and all preserved the same top 10.

ipl_eligibility_table = markdown_table(
    pd.DataFrame([
        {
            "Player type": "Batter",
            "Pressure exposure": "At least 8 matches and 100 balls",
            "Normal exposure": "At least 8 matches and 100 balls",
            "Eligible population": 32,
        },
        {
            "Player type": "Bowler",
            "Pressure exposure": "At least 8 matches and 120 legal balls",
            "Normal exposure": "At least 8 matches and 90 legal balls",
            "Eligible population": 49,
        },
    ])
)


# ============================================================
# 10. DATA AUDIT SUMMARY
# ============================================================

data_audit = pd.DataFrame([
    {
        "dataset": "IPL",
        "delivery_records": 87673,
        "matches_with_delivery_data": 367,
        "analysis_period": "2022-2026",
        "status": "Previously validated; revised batter eligibility applied in Step 73",
    },
    {
        "dataset": "T20I",
        "delivery_records": 106315,
        "matches_with_delivery_data": 470,
        "analysis_period": "2022-2026",
        "status": "Previously validated; 12 raw match records had no delivery data",
    },
])

data_audit.to_csv(
    REPORTS / "final_submission_data_audit.csv",
    index=False
)


# ============================================================
# 11. REPORT TABLES
# ============================================================

def report_ranking_table(data):
    result = data.copy()
    result["rating"] = result["rating"].map(
        lambda value: format_number(value)
    )
    return markdown_table(
        result,
        ["rank", "player_name", "rating"]
    )


ipl_batter_table = report_ranking_table(ipl_batter_top10)
ipl_bowler_table = report_ranking_table(ipl_bowler_top10)
t20i_batter_table = report_ranking_table(t20i_batter_top10)
t20i_bowler_table = report_ranking_table(t20i_bowler_top10)

cross_summary_table = markdown_table(cross_summary)

population_table = markdown_table(
    pd.DataFrame([
        {"Format": "IPL revised", "Player type": "Batters", "Eligible": 32},
        {"Format": "IPL revised", "Player type": "Bowlers", "Eligible": 49},
        {"Format": "T20I primary", "Player type": "Batters", "Eligible": 41},
        {"Format": "T20I primary", "Player type": "Bowlers", "Eligible": 62},
    ])
)


# ============================================================
# 12. GENERATE FINAL METHODOLOGY REPORT
# ============================================================

report = f"""
# SupeRR Selector Season 2
## Identifying the Most Reliable Players Under Pressure

**Competition:** Rajasthan Royals IPL 2027 Auction Strategy  
**Analysis period:** 2022–2026  
**Report type:** Revised data-driven player reliability analysis  
**Report generated:** {datetime.now().strftime("%d %B %Y")}

---

# 1. Executive Summary

This project develops a delivery-level statistical framework to identify batters and bowlers who perform reliably under pressure in T20 cricket.

The analysis uses IPL and T20 International delivery-level data from 2022 to 2026. Pressure performance is compared with each player's normal-performance baseline. Eligibility requirements, match-level consistency, sample size and sensitivity checks are incorporated into the rating process.

The revised IPL shortlist contains 10 batters and 10 bowlers. T20I rankings are retained as supplementary evidence and are not blended into the IPL ratings.

A material revision was made after the initial IPL ranking audit: the batter eligibility rule was strengthened to require a meaningful normal-performance comparison sample. This removed Rashid Khan from the eligible IPL batter pool because his normal batting exposure was only 42 balls across 17 matches. He remains eligible for the T20I bowler analysis; the same player ID does not imply the same player role in each ranking.

# 2. Project Objectives

1. Identify players who maintain or improve performance under pressure.
2. Compare pressure performance with normal-performance baselines.
3. Reduce small-sample distortions through eligibility rules.
4. Build separate reliability rankings for batters and bowlers.
5. Test ranking stability under alternative weights and exposure thresholds.
6. Use T20I results as supporting evidence for IPL auction decisions.

# 3. Dataset Overview

## 3.1 IPL

| Attribute | Value |
|---|---:|
| Delivery records | 87,673 |
| Matches represented in delivery data | 367 |
| Analysis period | 2022–2026 |

## 3.2 T20I

| Attribute | Value |
|---|---:|
| Raw match records | 482 |
| Matches with delivery data | 470 |
| Matches without delivery data | 12 |
| Selected delivery records | 106,315 |
| Analysis period | 2022–2026 |

Super-over innings were excluded from the main T20I analysis. Delivery reconstruction included legal-ball accounting, extras, administrative penalty treatment and innings reconciliation.

## 3.3 Data quality checks

The pipeline includes delivery reconstruction, innings run reconciliation, target reconciliation, dismissal attribution, bowler wicket-credit validation, duplicate checks and pressure-label validation. Detailed intermediate audits remain in the reports directory.

# 4. Pressure Definition

The framework distinguishes first-innings pressure from second-innings chase pressure because the relevant match context differs.

## 4.1 IPL first innings

Three signals are considered:

1. Score at least 5 runs below the expected par score.
2. Six or fewer wickets in hand.
3. Early collapse: seven or fewer wickets in hand within the first 36 legal balls.

At least two of the three signals are required. Severe pressure is identified when the score is at least 10 runs below par or three or fewer wickets remain.

The expected par score uses match-held-out, within-season benchmarking so a match does not contribute to its own benchmark.

## 4.2 IPL second innings

The selected chase-pressure rule is:

- Required run rate (RRR) is at least 10 runs per over; and
- Either six or fewer wickets remain, or 30 or fewer legal balls remain.

## 4.3 T20I first innings

Three signals are considered:

1. Score at least 5 runs below expected par.
2. Six or fewer wickets in hand.
3. Early collapse: seven or fewer wickets in hand within the first 30% of scheduled legal balls.

At least two signals are required. Severe pressure is identified when the score is at least 10 runs below par or three or fewer wickets remain.

The par benchmark uses five match-held-out folds within the relevant season and a hierarchical fallback where a more specific benchmark has insufficient support.

## 4.4 T20I second innings

The selected scaled chase-pressure rule is:

- RRR is at least 10 runs per over; and
- Either six or fewer wickets remain, or 25% or less of scheduled legal balls remain.

The proportional remaining-balls condition accounts for shortened matches.

## 4.5 Interpretation

First-innings and second-innings pressure frequencies are not directly interchangeable. First-innings pressure uses par-score context and wickets; chase pressure uses RRR, wickets and remaining scheduled time.

# 5. Player Performance Metrics

## 5.1 Batters

The analysis uses runs, balls faced, strike rate, dismissal rate per 100 balls, match-level consistency and exposure.

- **Strike-rate improvement:** pressure strike rate minus normal strike rate. Positive values indicate a higher scoring rate under pressure.
- **Dismissal-rate improvement:** normal dismissal rate minus pressure dismissal rate. Positive values indicate a lower dismissal rate under pressure.

Dismissals are attributed using the dismissed-player identifier, including non-striker dismissals where applicable.

## 5.2 Bowlers

The analysis uses runs conceded, legal balls, bowler-credit wickets, economy rate, pressure wickets per 100 legal balls, match-level consistency and exposure.

- **Economy improvement:** normal economy rate minus pressure economy rate. Positive values indicate better run control under pressure.
- **Pressure wicket rate:** bowler-credit wickets divided by pressure legal balls, multiplied by 100.

Run-outs and other non-bowler-credit dismissals are excluded from bowler wicket totals.

# 6. Eligibility Rules

## 6.1 Revised IPL eligibility

The original IPL batter top 10 included a player with only 42 normal balls. A normal-exposure sensitivity audit was therefore conducted. The revised batter population uses minimum exposure in both pressure and normal situations.

{ipl_eligibility_table}

The revised eligible populations are:

{population_table}

The revised batter population is 32, down from 36 in the original model. The bowler population remains 49.

The normal-exposure sensitivity audit found 90% top-10 overlap when applying normal-ball thresholds of 60 or 100 balls, and 80% overlap at 150 balls. The selected 100-ball normal threshold removes the identified 42-ball case while retaining 32 eligible batters.

For bowlers, Step 72 tested normal legal-ball thresholds of 90, 120 and 180. All 49 eligible bowlers remained, and the top 10 had 100% overlap across those tested thresholds.

## 6.2 T20I eligibility

T20I primary eligibility requires the minimum match and ball exposure in both pressure and normal groups.

| Scenario | Matches in each group | Batter balls in each group | Bowler legal balls in each group |
|---|---:|---:|---:|
| Flexible | 6 | 75 | 90 |
| Primary | 8 | 100 | 120 |
| Strict | 12 | 150 | 180 |

The primary T20I eligible populations are 41 batters and 62 bowlers. Flexible and strict scenarios are retained as sensitivity checks.

# 7. Reliability Rating Methodology

The model combines four percentile-scored components.

## 7.1 Batter weights

| Component | Weight |
|---|---:|
| Pressure strike-rate improvement | 30% |
| Dismissal-rate improvement | 25% |
| Match-level consistency | 30% |
| Sample-size score | 15% |

## 7.2 Bowler weights

| Component | Weight |
|---|---:|
| Economy improvement | 30% |
| Pressure wickets per 100 legal balls | 25% |
| Match-level consistency | 30% |
| Sample-size score | 15% |

## 7.3 Sample-size score

The sample component combines 60% qualifying-match exposure and 40% pressure-ball exposure. The targets are 20 pressure matches and 300 pressure balls, with exposure scores capped at those targets.

## 7.4 Percentile scoring

Component values are converted into percentiles within the eligible population and combined using the specified weights. Ratings are relative scores, not probabilities of future success. IPL and T20I ratings are calculated independently and must not be averaged or interpreted as directly comparable absolute scores.

# 8. Final IPL Auction Shortlist

IPL is the primary competition for the auction shortlist. The following lists use the revised Step 73 IPL reliability model.

## 8.1 Top 10 batters

{ipl_batter_table}

## 8.2 Top 10 bowlers

{ipl_bowler_table}

The ranking is statistical evidence, not a complete auction decision. Player role, squad balance, auction price, availability, overseas-player limits and team requirements must be evaluated separately.

# 9. T20I Supporting Evidence

T20I provides a separate international T20 view of pressure performance. It is supplementary evidence, not a replacement for IPL performance.

## 9.1 Top 10 T20I batters

{t20i_batter_table}

## 9.2 Top 10 T20I bowlers

{t20i_bowler_table}

These lists use the primary T20I eligibility scenario.

# 10. Revised Cross-Format Comparison

Players were matched by player ID and names were checked for consistency. The comparison uses the revised IPL eligible population and the primary T20I eligible population.

## 10.1 Matching summary

{cross_summary_table}

## 10.2 Matched players appearing in either format's top 10

{cross_table}

The revised comparison found no identity conflicts. There were 8 matched eligible batter IDs and 17 matched eligible bowler IDs. No matched player appeared in both format-specific top 10 lists.

This does not mean that a player absent from one eligible pool performed poorly in that format. It means only that the player did not meet the selected eligibility requirements in that format.

IPL and T20I rankings are based on different competition populations and are not combined.

# 11. Sensitivity Analysis

The project tested alternative eligibility thresholds and scoring weights.

## 11.1 T20I eligibility scenario results

{sensitivity_table}

## 11.2 T20I ranking overlap

{overlap_table}

## 11.3 IPL normal-exposure sensitivity

For batters, the original top 10 had 90% overlap when the minimum normal sample was raised to either 60 or 100 balls, and 80% overlap at 150 balls. The revised model adopts the 100-normal-ball threshold and reduces the eligible batter population from 36 to 32.

For bowlers, all 49 eligible players remained under the tested 90, 120 and 180 normal legal-ball thresholds, with 100% top-10 overlap.

These tests show that eligibility decisions affect the candidate pool and can change the resulting shortlist. This uncertainty is disclosed rather than hidden.

# 12. Validation and Integrity Checks

The pipeline includes:

- Legal and illegal delivery classification.
- Innings-level run reconciliation.
- Target and revised-target checks.
- Super-over exclusion.
- Administrative penalty treatment.
- Correct dismissed-player attribution.
- Bowler-credit wicket classification.
- Match-held-out first-innings par calculation.
- Hierarchical benchmark fallback.
- Pressure-definition sensitivity analysis.
- Scaled chase-pressure validation for shortened matches.
- Minimum eligibility checks.
- Alternative rating-weight scenarios.
- Flexible, primary and strict T20I eligibility comparisons.
- Revised IPL normal-exposure sensitivity checks.
- Cross-format player identity checks.

# 13. Limitations and Assumptions

1. Historical performance does not guarantee future performance.
2. Pressure labels depend on the selected contextual definitions and thresholds.
3. Small samples can produce unstable performance estimates.
4. Percentile scores depend on the eligible comparison population.
5. IPL and T20I ratings are not directly comparable as absolute scores.
6. Players without sufficient evidence are not necessarily poor performers.
7. International T20 performance may not transfer directly to IPL conditions.
8. Auction price, injury risk, availability, overseas-player restrictions and squad composition are not independently modelled.
9. The first-innings pressure definition partly depends on a par-score benchmark, so the pressure label is not an independent measure of match outcome.
10. Some data reconstruction decisions rely on documented working assumptions for unusual extras and revised innings limits.
11. The revised normal-exposure requirement improves baseline comparability but also excludes players whose role or batting opportunities produce fewer normal balls.

The shortlist should support, not replace, cricketing judgement and auction strategy.

# 14. Final Recommendations

1. Use the revised IPL reliability ranking as the primary statistical shortlist.
2. Review T20I pressure performance as supplementary evidence.
3. Give greater confidence to players with larger pressure samples.
4. Investigate players whose rankings change substantially under stricter eligibility.
5. Review player role and squad requirements before making an auction decision.
6. Evaluate price and availability separately from performance reliability.

# 15. Conclusion

This project establishes a reproducible delivery-level framework for evaluating player reliability under pressure. It combines contextual pressure definitions, individual baselines, corrected dismissal attribution, minimum exposure requirements, weighted percentile ratings and sensitivity analysis.

The final output provides revised IPL batter and bowler shortlists, supported by separate T20I evidence and transparent methodological limitations. The framework is intended to support evidence-based evaluation for the Rajasthan Royals IPL 2027 auction strategy.

---

# Appendix A: Primary Methodology Parameters

| Parameter | Selected value |
|---|---|
| Analysis period | 2022–2026 |
| IPL first-innings par validation | Match-held-out within-season folds |
| T20I first-innings par validation | Five match-held-out folds |
| IPL first-innings pressure | At least 2 of 3 signals |
| T20I first-innings pressure | At least 2 of 3 signals |
| Chase pressure RRR threshold | 10 runs per over |
| IPL batter eligibility | 8 pressure matches, 100 pressure balls; 8 normal matches, 100 normal balls |
| IPL bowler eligibility | 8 pressure matches and 120 pressure legal balls; 8 normal matches and tested normal-exposure threshold |
| T20I primary eligibility | 8 matches and minimum exposure in both groups |
| Batter rating weights | 30 / 25 / 30 / 15 |
| Bowler rating weights | 30 / 25 / 30 / 15 |
| Sample-size targets | 20 matches and 300 pressure balls |

# Appendix B: Reproducibility

The project uses Python and pandas for data reconstruction, statistical calculations, validation and report generation. The analysis is divided into sequential scripts. Generated CSV reports preserve player-level calculations and intermediate validation results.

**Project:** SupeRR Selector Season 2  
**End of Report**
"""


# ============================================================
# 13. SAVE REPORT AND FINAL AUDIT
# ============================================================

OUTPUT_REPORT.write_text(report, encoding="utf-8")

final_audit = pd.DataFrame([
    {"check": "IPL batter top 10", "actual": len(ipl_batter_top10), "expected": 10},
    {"check": "IPL bowler top 10", "actual": len(ipl_bowler_top10), "expected": 10},
    {"check": "T20I batter supporting top 10", "actual": len(t20i_batter_top10), "expected": 10},
    {"check": "T20I bowler supporting top 10", "actual": len(t20i_bowler_top10), "expected": 10},
    {"check": "Revised IPL eligible batters", "actual": population_counts["Revised IPL batters"], "expected": 32},
    {"check": "Revised IPL eligible bowlers", "actual": population_counts["Revised IPL bowlers"], "expected": 49},
    {"check": "Primary T20I eligible batters", "actual": population_counts["Primary T20I batters"], "expected": 41},
    {"check": "Primary T20I eligible bowlers", "actual": population_counts["Primary T20I bowlers"], "expected": 62},
    {"check": "Cross-format identity conflicts", "actual": int(cross_summary["identity_conflicts"].sum()), "expected": 0},
])

final_audit["passed"] = final_audit["actual"] == final_audit["expected"]

final_audit.to_csv(
    REPORTS / "final_submission_validation_audit.csv",
    index=False
)

if not final_audit["passed"].all():
    raise ValueError(
        "Final submission validation failed. "
        "Inspect reports/final_submission_validation_audit.csv."
    )

print("\n" + "=" * 90)
print("FINAL REVISED REPORT GENERATED SUCCESSFULLY")
print("=" * 90)
print(f"\nReport: {OUTPUT_REPORT}")
print("\nGenerated ranking files:")
for filename in output_rankings:
    print(" - reports/" + filename)
print(" - reports/final_all_top10_rankings.csv")
print("\nAudit files:")
print(" - reports/final_submission_data_audit.csv")
print(" - reports/final_submission_validation_audit.csv")
print("\nValidated populations:")
for label, count in population_counts.items():
    print(f" - {label}: {count}")
print("\nSTEP 75 COMPLETED.")
