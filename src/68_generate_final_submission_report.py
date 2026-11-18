
from pathlib import Path
from datetime import datetime
import shutil

import pandas as pd


# ============================================================
# STEP 68: FINAL RR HACKATHON SUBMISSION REPORT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS = BASE_DIR / "reports"
DOCS = BASE_DIR / "docs"
REPORTS.mkdir(parents=True, exist_ok=True)
DOCS.mkdir(parents=True, exist_ok=True)

FILES = {
    "ipl_batters": REPORTS / "batter_ipl_top10_revised.csv",
    "ipl_bowlers": REPORTS / "bowler_ipl_top10_revised.csv",
    "t20i_batters": REPORTS / "t20i_batter_top10_primary.csv",
    "t20i_bowlers": REPORTS / "t20i_bowler_top10_primary.csv",
    "cross_summary": REPORTS / "cross_format_revised_comparison_summary.csv",
    "cross_evidence": REPORTS / "cross_format_revised_top10_evidence.csv",
    "threshold_summary": REPORTS / "t20i_rating_threshold_summary.csv",
    "threshold_overlap": REPORTS / "t20i_rating_threshold_overlap.csv",
    "ipl_batter_ratings": REPORTS / "batter_reliability_ratings_revised.csv",
    "ipl_bowler_ratings": REPORTS / "bowler_reliability_ratings_revised.csv",
    "ipl_integrity_audit": REPORTS / "ipl_final_ranking_integrity_summary.csv",
    "t20i_batter_ratings": REPORTS / "t20i_batter_ratings_primary.csv",
    "t20i_bowler_ratings": REPORTS / "t20i_bowler_ratings_primary.csv",
    "ipl_batter_evidence": REPORTS / "final_ipl_batter_top10_evidence.csv",
    "ipl_bowler_evidence": REPORTS / "final_ipl_bowler_top10_evidence.csv"
}

OUTPUT_REPORT = REPORTS / "FINAL_RR_HACKATHON_METHODOLOGY_REPORT.md"
DOCS_REPORT = DOCS / "FINAL_RR_HACKATHON_METHODOLOGY_REPORT.md"

# Public competition context and implementation repository
GITHUB_REPOSITORY = "https://github.com/Kamalesh-Suresh-Kumar/SupeRR-Selector-Season-2-Rajasthan-Royals-hackathon"
REGISTERED_PARTICIPANTS = 28197  # Unstop listing snapshot: 17 November 2026
ROUND_1_FINALISTS = 16
ROUND_1_FINALIST_SHARE = ROUND_1_FINALISTS / REGISTERED_PARTICIPANTS * 100

print("\n" + "=" * 85)
print("STEP 68: FINAL RR HACKATHON SUBMISSION REPORT")
print("=" * 85)


# ============================================================
# 1. INPUT FILE VALIDATION
# ============================================================

missing_files = [
    str(path)
    for path in FILES.values()
    if not path.exists()
]

if missing_files:
    print("\nMissing required files:")

    for file in missing_files:
        print(" -", file)

    raise FileNotFoundError(
        "Required reports are missing. Complete the earlier steps first."
    )

print("\nAll required input files found.")


# ============================================================
# 2. GENERAL HELPERS
# ============================================================

def find_column(data, candidates, description):
    for column in candidates:
        if column in data.columns:
            return column

    raise ValueError(
        f"Could not find {description}. "
        f"Expected one of: {candidates}"
    )


def load_csv(name):
    return pd.read_csv(FILES[name])


def format_number(value, decimals=2):
    if pd.isna(value):
        return "N/A"

    return f"{float(value):,.{decimals}f}"


def markdown_table(data, columns=None):
    if columns is not None:
        data = data[columns].copy()

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
                values.append(str(value).replace("|", "/"))

        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


# ============================================================
# 3. STANDARDIZE TOP-10 RANKINGS
# ============================================================

def standardize_top10(
    file_key,
    player_type,
    format_name
):

    data = load_csv(file_key)

    if player_type == "Batter":
        name_candidates = [
            "striker_name",
            "player_name",
            "batter_name"
        ]
    else:
        name_candidates = [
            "bowler_name",
            "player_name"
        ]

    name_col = find_column(
        data,
        name_candidates,
        f"{format_name} {player_type} name"
    )

    rank_candidates = (
        ["final_rank", "rank_primary", "rank"]
        if format_name == "IPL"
        else ["rank", "t20i_rank"]
    )

    rating_candidates = (
        ["rating_primary", "rating"]
        if format_name == "IPL"
        else ["rating", "reliability_rating"]
    )

    rank_col = find_column(
        data,
        rank_candidates,
        f"{format_name} rank"
    )

    rating_col = find_column(
        data,
        rating_candidates,
        f"{format_name} rating"
    )

    id_col = (
        "striker_id"
        if player_type == "Batter"
        else "bowler_id"
    )

    if id_col not in data.columns:
        raise ValueError(
            f"{id_col} missing in {file_key}"
        )

    result = pd.DataFrame({
        "rank": pd.to_numeric(
            data[rank_col], errors="coerce"
        ),
        "player_id": data[id_col].astype("string"),
        "player_name": data[name_col].astype("string"),
        "rating": pd.to_numeric(
            data[rating_col], errors="coerce"
        )
    })

    result = result.dropna(
        subset=["rank", "player_id", "player_name", "rating"]
    )

    result["rank"] = result["rank"].astype(int)

    result = result.sort_values("rank").reset_index(drop=True)

    if len(result) != 10:
        raise ValueError(
            f"{format_name} {player_type} top 10 contains "
            f"{len(result)} rows instead of 10."
        )

    if result["player_id"].duplicated().any():
        raise ValueError(
            f"Duplicate player IDs in {format_name} "
            f"{player_type} top 10."
        )

    result.insert(0, "format", format_name)
    result.insert(1, "player_type", player_type)

    return result


# ============================================================
# 4. LOAD FINAL RANKINGS
# ============================================================

ipl_batter_top10 = standardize_top10(
    "ipl_batters", "Batter", "IPL"
)

ipl_bowler_top10 = standardize_top10(
    "ipl_bowlers", "Bowler", "IPL"
)

t20i_batter_top10 = standardize_top10(
    "t20i_batters", "Batter", "T20I"
)

t20i_bowler_top10 = standardize_top10(
    "t20i_bowlers", "Bowler", "T20I"
)

print("\nFinal top-10 files validated.")

print("IPL batters:", len(ipl_batter_top10))
print("IPL bowlers:", len(ipl_bowler_top10))
print("T20I batters:", len(t20i_batter_top10))
print("T20I bowlers:", len(t20i_bowler_top10))


# ============================================================
# 5. EXPORT CLEAN FINAL RANKING TABLES
# ============================================================

ipl_batter_top10.to_csv(
    REPORTS / "final_ipl_batter_top10.csv",
    index=False
)

ipl_bowler_top10.to_csv(
    REPORTS / "final_ipl_bowler_top10.csv",
    index=False
)

t20i_batter_top10.to_csv(
    REPORTS / "final_t20i_batter_supporting_top10.csv",
    index=False
)

t20i_bowler_top10.to_csv(
    REPORTS / "final_t20i_bowler_supporting_top10.csv",
    index=False
)

all_rankings = pd.concat(
    [
        ipl_batter_top10,
        ipl_bowler_top10,
        t20i_batter_top10,
        t20i_bowler_top10
    ],
    ignore_index=True
)

all_rankings.to_csv(
    REPORTS / "final_all_top10_rankings.csv",
    index=False
)


# ============================================================
# 6. LOAD VALIDATION REPORTS
# ============================================================

cross_summary = load_csv("cross_summary")
cross_evidence = load_csv("cross_evidence")

threshold_summary = load_csv("threshold_summary")
threshold_overlap = load_csv("threshold_overlap")

ipl_batter_ratings = load_csv("ipl_batter_ratings")
ipl_bowler_ratings = load_csv("ipl_bowler_ratings")

t20i_batter_ratings = load_csv("t20i_batter_ratings")
t20i_bowler_ratings = load_csv("t20i_bowler_ratings")


# ============================================================
# 7. VALIDATE PRIMARY ELIGIBLE POPULATIONS
# ============================================================

ipl_batter_count = len(ipl_batter_ratings)
ipl_bowler_count = len(ipl_bowler_ratings)

t20i_batter_count = len(t20i_batter_ratings)
t20i_bowler_count = len(t20i_bowler_ratings)

expected_populations = {
    "IPL batters": (ipl_batter_count, 32),
    "IPL bowlers": (ipl_bowler_count, 49),
    "T20I batters": (t20i_batter_count, 41),
    "T20I bowlers": (t20i_bowler_count, 62)
}

for label, (actual, expected) in expected_populations.items():
    if actual != expected:
        raise ValueError(
            f"{label}: expected {expected}, found {actual}. "
            "Investigate the primary rating population."
        )

print("\nPrimary eligible population validation passed.")


# ============================================================
# 7A. VALIDATE INDEPENDENT IPL RANKING INTEGRITY AUDIT
# ============================================================

ipl_integrity_audit = load_csv("ipl_integrity_audit")

required_audit_columns = [
    "player_type",
    "eligible_population",
    "rating_failures",
    "rank_failures",
    "top10_match",
    "overall_status"
]

missing_audit_columns = [
    column for column in required_audit_columns
    if column not in ipl_integrity_audit.columns
]

if missing_audit_columns:
    raise ValueError(
        "IPL independent integrity audit is missing columns: "
        f"{missing_audit_columns}"
    )

for player_type, expected_count in [("Batter", 32), ("Bowler", 49)]:
    rows = ipl_integrity_audit[
        ipl_integrity_audit["player_type"].astype(str).str.casefold()
        == player_type.casefold()
    ]

    if len(rows) != 1:
        raise ValueError(
            f"Expected exactly one independent audit row for {player_type}; "
            f"found {len(rows)}."
        )

    row = rows.iloc[0]

    checks_pass = (
        int(row["eligible_population"]) == expected_count
        and int(row["rating_failures"]) == 0
        and int(row["rank_failures"]) == 0
        and str(row["top10_match"]).strip().casefold() == "true"
        and str(row["overall_status"]).strip().upper() == "PASS"
    )

    if not checks_pass:
        raise ValueError(
            f"Independent IPL {player_type.lower()} ranking audit did not pass. "
            f"Audit row: {row.to_dict()}"
        )

print("Independent IPL ranking integrity audit: PASS (32 batters, 49 bowlers).")


# ============================================================
# 7B. IPL NORMAL-EXPOSURE SENSITIVITY RESULTS
# ============================================================
# Recorded results from the completed Steps 71 and 72.
# These results document the eligibility sensitivity analysis;
# they do not alter the primary ratings or final shortlist.

ipl_normal_sensitivity = pd.DataFrame([
    {"player_type": "Batter", "normal_ball_threshold": 60,
     "eligible_players": 34, "primary_top10_overlap": "9/10"},
    {"player_type": "Batter", "normal_ball_threshold": 100,
     "eligible_players": 32, "primary_top10_overlap": "9/10"},
    {"player_type": "Batter", "normal_ball_threshold": 150,
     "eligible_players": 31, "primary_top10_overlap": "8/10"},
    {"player_type": "Bowler", "normal_ball_threshold": 90,
     "eligible_players": 49, "primary_top10_overlap": "10/10"},
    {"player_type": "Bowler", "normal_ball_threshold": 120,
     "eligible_players": 49, "primary_top10_overlap": "10/10"},
    {"player_type": "Bowler", "normal_ball_threshold": 180,
     "eligible_players": 49, "primary_top10_overlap": "10/10"},
])


# ============================================================
# 8. BUILD DATA QUALITY AUDIT
# ============================================================

audit_rows = [
    {
        "dataset": "IPL",
        "records": 87673,
        "matches": 367,
        "period": "2022-2026",
        "status": "Validated"
    },
    {
        "dataset": "T20I",
        "records": 106315,
        "matches": 470,
        "period": "2022-2026",
        "status": "Validated; 12 match records had no delivery data"
    }
]

data_audit = pd.DataFrame(audit_rows)

data_audit.to_csv(
    REPORTS / "final_submission_data_audit.csv",
    index=False
)


# ============================================================
# 9. BUILD TOP-10 TABLES FOR THE REPORT
# ============================================================

def report_ranking_table(data):
    result = data.copy()

    result["rating"] = result["rating"].map(
        lambda x: format_number(x)
    )

    return markdown_table(
        result,
        ["rank", "player_name", "rating"]
    )


ipl_batter_table = report_ranking_table(
    ipl_batter_top10
)

ipl_bowler_table = report_ranking_table(
    ipl_bowler_top10
)

t20i_batter_table = report_ranking_table(
    t20i_batter_top10
)

t20i_bowler_table = report_ranking_table(
    t20i_bowler_top10
)


# ============================================================
# 9A. VALIDATE AND BUILD PLAYER-LEVEL IPL EVIDENCE TABLES
# ============================================================

batter_evidence = load_csv("ipl_batter_evidence")
bowler_evidence = load_csv("ipl_bowler_evidence")

def validate_evidence(evidence, ranking, player_type):
    required = [
        "rank", "player_name", "qualifying_pressure_matches",
        "consistency_percentage", "performance_score",
        "risk_score", "consistency_score", "sample_score",
        "reliability_rating"
    ]

    if player_type == "Batter":
        required += [
            "pressure_balls", "normal_matches", "normal_balls",
            "normal_strike_rate", "pressure_strike_rate",
            "strike_rate_improvement",
            "normal_dismissals_per_100_balls",
            "pressure_dismissals_per_100_balls",
            "dismissal_rate_improvement"
        ]
    else:
        required += [
            "pressure_legal_balls", "normal_matches",
            "normal_legal_balls", "normal_economy",
            "pressure_economy", "economy_improvement",
            "pressure_wickets",
            "pressure_wickets_per_100_legal_balls"
        ]

    missing = [c for c in required if c not in evidence.columns]
    if missing:
        raise ValueError(
            f"{player_type} evidence file is missing columns: {missing}"
        )

    if len(evidence) != 10:
        raise ValueError(
            f"{player_type} evidence must contain exactly 10 rows; "
            f"found {len(evidence)}."
        )

    left = evidence.sort_values("rank").reset_index(drop=True)
    right = ranking.sort_values("rank").reset_index(drop=True)

    if left["player_name"].astype(str).tolist() != right["player_name"].astype(str).tolist():
        raise ValueError(
            f"{player_type} evidence player order does not match final ranking."
        )

    if not (pd.to_numeric(left["rank"]).tolist() == pd.to_numeric(right["rank"]).tolist()):
        raise ValueError(f"{player_type} evidence ranks do not match final ranking.")

    if not (
        (pd.to_numeric(left["reliability_rating"]) -
         pd.to_numeric(right["rating"])).abs() < 0.000001
    ).all():
        raise ValueError(
            f"{player_type} evidence ratings do not match final ranking."
        )

    return left


batter_evidence = validate_evidence(
    batter_evidence, ipl_batter_top10, "Batter"
)
bowler_evidence = validate_evidence(
    bowler_evidence, ipl_bowler_top10, "Bowler"
)

def make_evidence_tables(data, player_type):
    if player_type == "Batter":
        raw_cols = [
            "rank", "player_name", "qualifying_pressure_matches",
            "pressure_balls", "normal_strike_rate",
            "pressure_strike_rate", "strike_rate_improvement",
            "normal_dismissals_per_100_balls",
            "pressure_dismissals_per_100_balls",
            "dismissal_rate_improvement", "consistency_percentage",
            "reliability_rating"
        ]
        rename = {
            "qualifying_pressure_matches": "Qualifying pressure matches",
            "pressure_balls": "Pressure balls",
            "normal_strike_rate": "Normal SR",
            "pressure_strike_rate": "Pressure SR",
            "strike_rate_improvement": "SR improvement",
            "normal_dismissals_per_100_balls": "Normal dismissals / 100 balls",
            "pressure_dismissals_per_100_balls": "Pressure dismissals / 100 balls",
            "dismissal_rate_improvement": "Dismissal improvement",
            "consistency_percentage": "Consistency %",
            "reliability_rating": "Rating"
        }
    else:
        raw_cols = [
            "rank", "player_name", "qualifying_pressure_matches",
            "pressure_legal_balls", "normal_economy",
            "pressure_economy", "economy_improvement",
            "pressure_wickets_per_100_legal_balls",
            "consistency_percentage", "reliability_rating"
        ]
        rename = {
            "qualifying_pressure_matches": "Qualifying pressure matches",
            "pressure_legal_balls": "Pressure legal balls",
            "normal_economy": "Normal economy",
            "pressure_economy": "Pressure economy",
            "economy_improvement": "Economy improvement",
            "pressure_wickets_per_100_legal_balls": "Wickets / 100 legal balls",
            "consistency_percentage": "Consistency %",
            "reliability_rating": "Rating"
        }

    raw = data[raw_cols].rename(columns=rename).copy()

    component_cols = [
        "rank", "player_name", "performance_score",
        "risk_score", "consistency_score", "sample_score",
        "reliability_rating"
    ]
    components = data[component_cols].rename(columns={
        "performance_score": "Performance percentile",
        "risk_score": "Secondary metric percentile",
        "consistency_score": "Consistency percentile",
        "sample_score": "Sample score",
        "reliability_rating": "Final rating"
    }).copy()

    for frame in (raw, components):
        for col in frame.columns:
            if col not in ("rank", "player_name"):
                frame[col] = frame[col].map(
                    lambda x: format_number(x, 2)
                )

    return markdown_table(raw), markdown_table(components)


batter_raw_evidence_table, batter_component_table = make_evidence_tables(
    batter_evidence, "Batter"
)
bowler_raw_evidence_table, bowler_component_table = make_evidence_tables(
    bowler_evidence, "Bowler"
)

print("Player-level evidence validation: PASS (10 batters, 10 bowlers).")


# ============================================================
# 9B. BUILD EVIDENCE-LED SQUAD CONTRIBUTION INTERPRETATION
# ============================================================

def build_squad_contribution_table(data, player_type):
    rows = []

    for _, row in data.sort_values("rank").iterrows():
        player = str(row["player_name"])
        matches = int(row["qualifying_pressure_matches"])
        consistency = float(row["consistency_percentage"])

        if player_type == "Batter":
            sr_change = float(row["strike_rate_improvement"])
            dismissal_change = float(row["dismissal_rate_improvement"])

            signals = []
            if sr_change > 0:
                signals.append("scored faster under pressure than their normal baseline")
            elif sr_change < 0:
                signals.append("scored more slowly under pressure than their normal baseline")
            else:
                signals.append("matched their normal scoring rate under pressure")

            if dismissal_change > 0:
                signals.append("had a lower dismissal rate under pressure")
            elif dismissal_change < 0:
                signals.append("had a higher dismissal rate under pressure")
            else:
                signals.append("had an unchanged dismissal rate under pressure")

            evidence = (
                f"Across {matches} qualifying pressure matches, the player "
                f"{'; and '.join(signals)}. Consistency: {consistency:.1f}%."
            )
            implication = (
                "Can inform RR's assessment of pressure-innings scoring and "
                "batting stability. Validate batting position, role and squad "
                "fit separately; this analysis does not assign a batting role."
            )
        else:
            economy_change = float(row["economy_improvement"])
            wicket_rate = float(row["pressure_wickets_per_100_legal_balls"])

            if economy_change > 0:
                economy_signal = "conceded fewer runs per over under pressure"
            elif economy_change < 0:
                economy_signal = "conceded more runs per over under pressure"
            else:
                economy_signal = "matched their normal economy under pressure"

            evidence = (
                f"Across {matches} qualifying pressure matches, the player "
                f"{economy_signal}; pressure wicket rate was "
                f"{wicket_rate:.2f} per 100 legal balls. "
                f"Consistency: {consistency:.1f}%."
            )
            implication = (
                "Can inform RR's assessment of pressure-overs run control and "
                "wicket threat. Validate bowling phase, role and squad fit "
                "separately; this analysis does not assign an over or phase."
            )

        rows.append({
            "rank": int(row["rank"]),
            "player": player,
            "pressure evidence": evidence,
            "potential RR squad relevance": implication
        })

    return markdown_table(pd.DataFrame(rows))


batter_squad_contribution_table = build_squad_contribution_table(
    batter_evidence, "Batter"
)
bowler_squad_contribution_table = build_squad_contribution_table(
    bowler_evidence, "Bowler"
)


# ============================================================
# 10. BUILD CROSS-FORMAT EVIDENCE TABLE
# ============================================================

cross_columns = [
    "player_type",
    "player_name",
    "ipl_rank",
    "ipl_rating",
    "t20i_rank",
    "t20i_rating",
    "cross_format_evidence"
]

for column in cross_columns:
    if column not in cross_evidence.columns:
        raise ValueError(
            f"Cross-format evidence is missing column: {column}"
        )

cross_table = cross_evidence[cross_columns].copy()

cross_table = cross_table.sort_values(
    ["player_type", "ipl_rank", "t20i_rank"],
    na_position="last"
)

for column in ["ipl_rating", "t20i_rating"]:
    cross_table[column] = cross_table[column].map(
        lambda x: format_number(x)
    )

cross_table = markdown_table(cross_table)


# ============================================================
# 11. CROSS-FORMAT SUMMARY
# ============================================================

cross_summary_table = markdown_table(cross_summary)


# ============================================================
# 12. ELIGIBILITY SENSITIVITY TABLE
# ============================================================

sensitivity_table = markdown_table(
    threshold_summary,
    [
        "scenario",
        "player_type",
        "eligible_players",
        "top10_available"
    ]
)

overlap_table = markdown_table(
    threshold_overlap
)

ipl_normal_sensitivity_table = markdown_table(
    ipl_normal_sensitivity,
    ["player_type", "normal_ball_threshold", "eligible_players", "primary_top10_overlap"]
)

def optional_sensitivity_table(filename, expected_columns, display_columns):
    path = REPORTS / filename
    if not path.exists():
        return f"_Sensitivity output `{filename}` was not found; no overlap values are asserted._"
    data = pd.read_csv(path)
    missing = [column for column in expected_columns if column not in data.columns]
    if missing:
        return f"_Sensitivity output `{filename}` is missing expected fields {missing}; no overlap values are asserted._"
    return markdown_table(data, display_columns)

ipl_weight_sensitivity_table = optional_sensitivity_table(
    "ipl_revised_ranking_weight_sensitivity.csv",
    ["player_type", "scenario", "primary_top10_overlap", "overlap_percentage"],
    ["player_type", "scenario", "primary_top10_overlap", "overlap_percentage"]
)

t20i_weight_sensitivity_table = optional_sensitivity_table(
    "t20i_reliability_ranking_sensitivity.csv",
    ["player_type", "scenario", "common_top10_players", "top10_overlap_pct"],
    ["player_type", "scenario", "common_top10_players", "top10_overlap_pct"]
)


# ============================================================
# 13. GENERATE FINAL METHODOLOGY REPORT
# ============================================================

report = f"""
# SupeRR Selector Season 2
## Identifying the Most Reliable Players Under Pressure

**Competition:** Rajasthan Royals IPL 2027 Auction Strategy

**Analysis period:** 2022–2026

**Report type:** Data-driven player reliability analysis

---

# 1. Executive Summary

This project develops a data-driven framework to identify batters and bowlers who perform reliably under pressure in T20 cricket.

The analysis uses IPL and T20 International delivery-level data from 2022 to 2026.

Rather than selecting players using reputation or aggregate career statistics, the framework compares performance under defined pressure situations against each player's normal-performance baseline.

The final IPL shortlist contains:

- 10 batters.
- 10 bowlers.

T20I results are used as supplementary evidence. They are not blended with IPL ratings because each competition has a different eligible population and independently calculated percentile scores.

The methodology combines performance improvement, consistency and sample-size evidence into a weighted reliability rating.

## 1.1 Competition Progression and Selection Context

The Unstop competition listing displayed **{REGISTERED_PARTICIPANTS:,} registered participants** (listing snapshot dated 17 November 2026). The published progression identifies **{ROUND_1_FINALISTS} Round 1 finalists** for the in-person Round 2 hackathon in Mumbai. This represents approximately **{ROUND_1_FINALIST_SHARE:.3f}%** of the displayed registration count. The listing states that the Round 2 winner advances to the Round 3 IPL 2027 Auction Finale in Goa and presents their strategy to Rajasthan Royals' leadership.

The published Round 1 brief asks participants to identify reliable players under pressure and submit the methodology, top picks and explanation of how the players could strengthen the Rajasthan Royals squad. The public event listing does not publish a detailed numerical judging rubric for selecting the Top 16 or the Round 2 winner. Accordingly, this report does not claim to know or reverse-engineer undisclosed evaluation weights. It focuses on making the stated analytical task independently assessable through explicit definitions, player-level evidence, reproducible calculations, validation checks and clearly stated limitations.

**What this analysis makes assessable:** (i) why a player qualifies, (ii) how pressure performance compares with that player's normal baseline, (iii) how frequently the player performs above that baseline across pressure matches, (iv) how much qualifying evidence supports the rating, and (v) whether the final ranking survives independent integrity and sensitivity checks. The player-level evidence tables are intended to let a reviewer trace each shortlist position back to the underlying indicators rather than rely on a name-only recommendation.

The reliability shortlist is a statistical decision-support layer, not a complete squad-building or auction-bidding model. Player role, squad gaps, availability, auction price and tactical fit must be considered separately before a final franchise decision.

---

# 2. Project Objectives

The primary objectives are:

1. Identify players who maintain or improve performance under pressure.
2. Compare pressure performance with normal-performance baselines.
3. Distinguish genuine performance evidence from small-sample results.
4. Build separate reliability rankings for batters and bowlers.
5. Validate rankings using alternative eligibility thresholds and scoring weights.
6. Use T20I evidence to provide additional context for IPL auction decisions.

---

# 3. Dataset Overview

The project uses two primary datasets.

## 3.1 IPL Dataset

| Attribute | Value |
|---|---:|
| Delivery records | 87,673 |
| Matches represented in delivery data | 367 |
| Analysis period | 2022–2026 |

The IPL dataset was reconstructed and processed at delivery level.

First-innings and second-innings pressure were evaluated using different contextual definitions.

## 3.2 T20I Dataset

| Attribute | Value |
|---|---:|
| Raw match records | 482 |
| Matches with delivery data | 470 |
| Matches without delivery data | 12 |
| Selected delivery records | 106,315 |
| Analysis period | 2022–2026 |

Super-over innings were excluded from the main analysis.

The T20I delivery data was reconstructed with separate treatment of legal deliveries, illegal deliveries, extras and administrative penalty events.

## 3.3 Data Quality

The project includes:

- Delivery reconstruction.
- Legal-ball accounting.
- Innings score reconciliation.
- Target reconciliation.
- Dismissal attribution.
- Bowler wicket-credit validation.
- Duplicate and missing-value checks.
- Pressure-label validation.

The detailed data audit and intermediate validation reports are retained in the reports directory.

---

# 4. Pressure Definition

Pressure is not defined as a single match situation.

The framework distinguishes first-innings pressure from second-innings chase pressure.

This is necessary because the available contextual information differs between the two innings.

### Operational terminology

- **Par score:** the expected cumulative score at a given first-innings checkpoint, estimated from comparable innings.
- **Runs below par:** par score minus the actual score at the same checkpoint. A positive difference means the batting side is behind the benchmark.
- **Wickets in hand:** wickets remaining at the delivery being evaluated.
- **Required run rate (RRR):** runs still required divided by legal balls remaining, multiplied by six.
- **Legal balls remaining:** scheduled legal deliveries left in the innings, rather than a count that includes wides or no-balls.
- **Pressure threshold:** an operational classification rule used consistently in this analysis; it is not presented as a universal definition of pressure in cricket.

For first-innings comparisons, the par benchmark is estimated without using the match being evaluated. This match-held-out design reduces self-influence: a match cannot raise or lower its own expected-score benchmark. Where the T20I benchmark has insufficient support at a more specific level, the documented hierarchical fallback is used.

## 4.1 IPL First-Innings Pressure

Three signals are considered:

1. Score at least 5 runs below the expected par score.
2. Six or fewer wickets in hand.
3. Early collapse: seven or fewer wickets in hand within the first 36 legal balls.

A delivery is labelled as first-innings pressure when at least two of these three signals are present.

Severe pressure is identified when:

- The score is at least 10 runs below par; or
- Three or fewer wickets remain.

The expected par score uses a match-held-out, within-season benchmark so a match does not contribute to its own benchmark.

## 4.2 IPL Second-Innings Pressure

The primary chase rule is:

- Required run rate is at least 10 runs per over; and
- Either six or fewer wickets remain, or 30 or fewer legal balls remain.

This combines scoring demand with match context. The RRR condition captures the required scoring pace; the wickets/remaining-balls condition adds information about the batting side's resources or time constraint.

The value of 10 runs per over is the selected operational cutoff in this analysis. It should be interpreted alongside the sensitivity and limitations discussed later, rather than as a universal boundary between pressure and non-pressure.

## 4.3 T20I First-Innings Pressure

Three signals are considered:

1. Score at least 5 runs below expected par.
2. Six or fewer wickets in hand.
3. Early collapse: seven or fewer wickets in hand within the first 30% of scheduled legal balls.

At least two of the three signals are required.

Severe pressure is identified when:

- The score is at least 10 runs below par; or
- Three or fewer wickets remain.

The par benchmark uses five match-held-out folds within the relevant season and a hierarchical fallback when a more specific benchmark has insufficient support.

## 4.4 T20I Second-Innings Pressure

The selected scaled chase rule is:

- Required run rate is at least 10 runs per over; and
- Either six or fewer wickets remain, or 25% or less of the scheduled legal balls remain.

The proportional definition scales the remaining-ball condition to the scheduled legal-ball allowance of the innings. This makes the time component more comparable when an innings has a shortened allocation than a fixed absolute-ball cutoff would be. The RRR condition remains part of the rule.

## 4.5 Why Separate Definitions Are Necessary

First-innings pressure depends on performance against an expected scoring benchmark.

Second-innings pressure depends on the required scoring rate, wickets in hand and remaining time.

These two situations are not directly interchangeable. Their pressure frequencies should therefore not be interpreted as identical measures.

The numerical cutoffs in this section are explicit, reproducible operating choices for this analysis. They simplify complex match states into delivery-level labels. They do not imply that every delivery crossing a threshold is equally difficult, or that pressure can be captured completely by a small set of rules.

---

# 5. Player Performance Metrics

## 5.1 Batter Metrics

The batter analysis compares pressure and normal situations using:

- Runs scored.
- Balls faced.
- Strike rate.
- Dismissal rate per 100 balls.
- Match-level consistency.
- Pressure sample size.

The main performance signals are:

**Strike-rate improvement**

Pressure strike rate minus normal strike rate.

A positive value indicates a higher scoring rate under pressure.

**Dismissal-rate improvement**

Normal dismissal rate minus pressure dismissal rate.

A positive value indicates a lower dismissal rate under pressure.

## 5.2 Match-Level Consistency Calculation

Consistency compares each player's pressure performance in each individual pressure match with that player's overall normal-situation baseline.

For IPL batters:
1. Calculate the batter's strike rate in each match containing pressure deliveries.
2. Compare it with the batter's overall normal-situation strike rate.
3. Count a match as above baseline only when its pressure strike rate is strictly greater than the normal baseline.
4. Calculate consistency percentage as: (pressure matches above the normal strike-rate baseline / total pressure matches) × 100.

For IPL bowlers:
1. Calculate the bowler's economy rate in each match containing pressure deliveries.
2. Compare it with the bowler's overall normal-situation economy.
3. Count a match as better than baseline only when its pressure economy is strictly lower than the normal baseline.
4. Calculate consistency percentage as: (pressure matches with lower-than-normal economy / total pressure matches) × 100.

A match equal to the normal baseline is not counted as an above-baseline match. Each pressure match contributes one binary outcome; the percentage is not a weighted average of match-level rates. The normal baseline is calculated from the player's normal-situation records across the analysis dataset.

The IPL implementation records this percentage in the player consistency dataset. T20I ratings use the precomputed `consistency_pct` field supplied by the T20I pressure-consistency inputs. Step 65 merges this field into the eligible T20I population and checks that it is present; Step 65 does not itself reconstruct the match-level consistency calculation.

## 5.3 Bowler Metrics

The bowler analysis uses:

- Runs conceded.
- Legal balls bowled.
- Wickets.
- Economy rate.
- Pressure wickets per 100 legal balls.
- Match-level consistency.
- Pressure sample size.

The principal performance signals are:

**Economy improvement**

Normal economy rate minus pressure economy rate.

A positive value indicates better run control under pressure.

**Pressure wickets per 100 legal balls**

Pressure wickets divided by pressure legal balls, multiplied by 100.

Only bowler-credit dismissals are counted as bowler wickets.

Run-outs and other non-bowler-credit dismissals are excluded. The pressure wicket rate is calculated as bowler-credit wickets divided by pressure legal balls, multiplied by 100.

---

# 6. Eligibility Thresholds

Players must have sufficient evidence before receiving a reliability ranking.

## 6.1 IPL Eligibility

The revised IPL eligibility requirements require sufficient exposure in both pressure and normal situations.

| Player type | Minimum pressure matches | Minimum pressure balls | Minimum normal matches | Minimum normal balls |
|---|---:|---:|---:|---:|
| Batter | 8 | 100 | 8 | 100 |
| Bowler | 8 | 120 legal balls | 8 | 180 legal balls |

The revised eligible IPL population is:

| Player type | Eligible players |
|---|---:|
| Batters | {ipl_batter_count} |
| Bowlers | {ipl_bowler_count} |

These additional normal-situation exposure requirements reduce the risk of comparing pressure performance against an inadequately supported baseline.

## 6.2 T20I Eligibility

T20I uses stricter comparative exposure requirements.

A player must meet the required match and ball thresholds in both pressure and normal situations.

| Scenario | Matches in each group | Batter balls in each group | Bowler legal balls in each group |
|---|---:|---:|---:|
| Flexible | 6 | 75 | 90 |
| Primary | 8 | 100 | 120 |
| Strict | 12 | 150 | 180 |

The primary T20I eligible population is:

| Player type | Eligible players |
|---|---:|
| Batters | {t20i_batter_count} |
| Bowlers | {t20i_bowler_count} |

The primary scenario is used for the final T20I supporting rankings.

---

# 7. Reliability Rating Methodology

The reliability score combines four components.

## 7.1 Batter Weights

| Component | Weight |
|---|---:|
| Pressure strike-rate improvement | 30% |
| Dismissal-rate improvement | 25% |
| Match-level consistency | 30% |
| Sample-size score | 15% |

## 7.2 Bowler Weights

| Component | Weight |
|---|---:|
| Economy improvement | 30% |
| Pressure wickets per 100 legal balls | 25% |
| Match-level consistency | 30% |
| Sample-size score | 15% |

## 7.3 Metric Direction and Sample-Size Score

All component directions are standardized so that a higher component value represents stronger pressure performance:

- Batter strike-rate improvement: pressure strike rate minus normal strike rate; higher is better.
- Batter dismissal-rate improvement: normal dismissal rate minus pressure dismissal rate; higher is better.
- Bowler economy improvement: normal economy rate minus pressure economy rate; higher is better.
- Bowler pressure wicket rate: bowler-credit wickets per 100 pressure legal balls; higher is better.
- Match-level consistency: higher consistency percentage is better.

The sample-size component is calculated using:

- 60% qualifying-match exposure.
- 40% pressure-ball exposure.

The sample targets are:

- 20 pressure matches.
- 300 pressure balls.

The match and pressure-ball exposure ratios are each capped at 100% of their respective targets before the weighted sample-size score is calculated. This component rewards evidence volume; it does not directly measure performance quality.

## 7.4 Exact Reliability-Score Formula

The primary weighted structure is:

`Reliability rating = 0.30 × P1 + 0.25 × P2 + 0.30 × C + 0.15 × S`

where P1 is the percentile score for the primary pressure-performance improvement, P2 is the percentile score for the secondary performance metric, C is the consistency percentile score, and S is the sample-size component used by that format's implementation.

For batters, P1 is pressure-minus-normal strike-rate improvement and P2 is normal-minus-pressure dismissal-rate improvement. For bowlers, P1 is normal-minus-pressure economy improvement and P2 is pressure wickets per 100 legal balls.

## 7.5 Percentile Scoring and Sample-Size Implementation

The revised IPL implementation converts performance and consistency components to percentile scores within the revised eligible population. It uses ascending percentile ranks multiplied by 100, with average ranks for tied component values. Metric direction is standardized so higher values indicate better performance.

The revised IPL sample component is calculated directly from exposure:

`S_IPL = 100 × [0.60 × min(qualifying pressure matches / 20, 1) + 0.40 × min(pressure balls / 300, 1)]`

The sample component is not percentile-ranked in the revised IPL script. For bowlers, pressure balls in this formula are pressure legal balls.

The T20I implementation calculates the same 60% match-exposure and 40% pressure-ball-exposure blend, capped at 20 pressure matches and 300 pressure balls. Unlike the revised IPL implementation, Step 65 percentile-ranks this sample score within the eligible T20I population before applying the 15% sample weight. T20I component percentiles use average ranks. When assigning the displayed T20I order, equal reliability ratings are sorted by pressure-match count.

The ratings are relative composite scores, not probabilities of future success. IPL and T20I ratings are calculated independently and must not be directly averaged or interpreted as identical absolute scales.

## 7.6 Alternative Weight Scenarios

The revised IPL and primary T20I scripts test these configurations:

| Scenario | Primary performance | Secondary metric | Consistency | Sample |
|---|---:|---:|---:|---:|
| Primary | 30% | 25% | 30% | 15% |
| Performance-heavy | 35% | 20% | 30% | 15% |
| Consistency-heavy | 25% | 20% | 40% | 15% |
| Sample-conservative | 30% | 25% | 25% | 20% |

These are sensitivity scenarios, not additional final rankings. The primary scenario is used for the submitted Top 10 lists.

---

# 8. Final IPL Reliability Shortlists and Player Evidence

IPL is the primary competition for the auction shortlist.

## 8.1 Top 10 Batters

{ipl_batter_table}

### Batter-level performance evidence

The following table compares each shortlisted batter's pressure performance with their normal-situation baseline. Positive strike-rate improvement indicates faster scoring under pressure; positive dismissal-rate improvement indicates fewer dismissals per 100 balls under pressure.

{batter_raw_evidence_table}

### Batter reliability-rating components

The component scores show how the primary weighted rating was assembled. Performance, secondary-metric and consistency values are percentile scores within the eligible IPL batter population. The sample score is the direct exposure score described in Section 7.5.

{batter_component_table}

## 8.2 Top 10 Bowlers

{ipl_bowler_table}

### Bowler-level performance evidence

The table compares each shortlisted bowler's pressure economy with their normal-situation economy. Positive economy improvement indicates fewer runs conceded per over under pressure. Pressure wickets are bowler-credit wickets per 100 pressure legal balls.

{bowler_raw_evidence_table}

### Bowler reliability-rating components

The component scores show how the primary weighted rating was assembled. Performance, secondary-metric and consistency values are percentile scores within the eligible IPL bowler population. The sample score is the direct exposure score described in Section 7.5.

{bowler_component_table}

## 8.3 How the Pressure Evidence Can Inform RR Squad Decisions

The following interpretations translate the measured pressure signals into decision-support context. They do not claim that the analysis has modelled RR's current squad gaps, player availability, auction price or tactical role.

### Batter contribution context

{batter_squad_contribution_table}

### Bowler contribution context

{bowler_squad_contribution_table}

Use these evidence-led observations as a starting point for role and squad-fit review. The final franchise decision should also consider batting position, bowling phase, role coverage, overseas-player constraints, availability, auction price and the existing squad composition. Those factors are outside the current reliability model.

These rankings are based on the primary IPL reliability rating.

They should be interpreted alongside player roles, squad balance, auction price, availability and team requirements.

---

# 9. T20I Supporting Evidence

T20I provides an additional view of how players perform under pressure in international T20 cricket.

It is supplementary evidence rather than a replacement for IPL performance.

## 9.1 Top 10 T20I Batters

{t20i_batter_table}

## 9.2 Top 10 T20I Bowlers

{t20i_bowler_table}

The T20I lists use the primary eligibility scenario.

---

# 10. Cross-Format Comparison

Players were matched using player IDs, with names checked for identity consistency.

The comparison covered the eligible IPL and T20I populations.

## 10.1 Matching Results

{cross_summary_table}

The matched-player counts describe only players who satisfy the eligibility rules in both formats. The top-10 overlap columns therefore measure overlap within this matched subset, not overlap across the complete IPL and T20I top-10 lists. Unmatched players are not evidence of poor performance; they simply lack a qualifying comparison population in the other format.

No identity conflicts were detected in the matched player records.

## 10.2 Cross-Format Top-10 Evidence

{cross_table}

The Step 74 cross-format evidence table reports players who could be identity-matched across both eligible format populations. Its top-10 overlap result applies to that matched subset only; players who were eligible in one format but not the other cannot be treated as a cross-format ranking comparison.

This does not mean that the rankings are contradictory. The formats have different competitive environments, eligible populations and exposure distributions.

T20I performance should be treated as additional evidence, not as a direct forecast of IPL performance.

---

# 11. Sensitivity Analysis

The project tests whether the rankings remain stable when eligibility thresholds change.

## 11.1 IPL Normal-Situation Exposure Sensitivity

The revised IPL eligibility rule was tested against alternative minimum normal-situation ball exposures. Pressure-side requirements and the minimum of eight normal matches were retained.

{ipl_normal_sensitivity_table}

For batters, the eligible population changes as the minimum normal-ball requirement increases. The primary 100-ball threshold retains 32 eligible batters and preserves nine of the original ten shortlisted batters. The 150-ball threshold reduces the population to 31 and preserves eight of the ten.

For bowlers, all 49 eligible players remain eligible at the tested normal legal-ball thresholds, and the primary top 10 remains unchanged in all three comparisons.

## 11.2 T20I Eligible Population by Scenario

{sensitivity_table}

## 11.3 T20I Top-10 Ranking Overlap

{overlap_table}

## 11.4 Alternative Weighting Sensitivity

The alternative weight scenarios are defined in Section 7.6. Where the completed pipeline has generated sensitivity outputs, the observed Top-10 overlap with the primary scenario is shown below. The overlap measures membership, not rank-order stability.

**IPL revised-rating sensitivity**

{ipl_weight_sensitivity_table}

**T20I primary-rating sensitivity**

{t20i_weight_sensitivity_table}

The primary thresholds were retained as the final selection because:

- Flexible thresholds admit players with smaller samples.
- Strict thresholds remove a substantial portion of the eligible population.
- The primary scenario provides a balance between evidence volume and player coverage.

The sensitivity results demonstrate that some rankings depend on the chosen minimum exposure requirements.

This uncertainty is retained rather than hidden.

---

# 12. Validation and Integrity Checks

The analysis includes several independent checks.

### Data reconstruction

- Legal and illegal delivery classification.
- Innings-level run reconciliation.
- Target and revised-target checks.
- Super-over exclusion.
- Administrative penalty treatment.

### Player attribution

- Correct dismissed-player attribution.
- Bowler-credit wicket classification.
- Run-out exclusion from bowler-credit wickets.

### Benchmark validation

- Match-held-out first-innings par calculation.
- Hierarchical benchmark fallback.
- Pressure-definition sensitivity analysis.
- Scaled chase-pressure validation for shortened matches.

### Ranking validation

- Minimum eligibility checks.
- Separate batter and bowler ratings.
- Alternative weighting scenarios.
- Flexible, primary and strict eligibility comparisons.
- Cross-format player identity checks.

### Independent IPL ranking integrity audit

The revised IPL rankings were independently recalculated from the consolidated player metric datasets.

| Audit check | Batters | Bowlers |
|---|---:|---:|
| Eligible population | 32 | 49 |
| Rating matches | 32/32 | 49/49 |
| Rank matches | 32/32 | 49/49 |
| Top-10 comparison | PASS | PASS |
| Rating mismatches | 0 | 0 |
| Rank mismatches | 0 | 0 |

Both revised IPL ranking populations passed the independent integrity audit.

---

# 13. Limitations and Assumptions

The results should be interpreted with the following limitations.

1. Historical performance does not guarantee future performance.
2. Pressure labels depend on the selected thresholds and contextual definitions.
3. Small player samples can produce unstable performance estimates.
4. Percentile scores depend on the eligible comparison population.
5. IPL and T20I ratings are not directly comparable as absolute scores.
6. Players without sufficient evidence are not necessarily poor performers.
7. International T20 performance may not transfer directly to IPL conditions.
8. The analysis does not independently model auction price, salary expectations, injury risk, availability, overseas-player restrictions or squad composition.
9. The first-innings pressure definition partly depends on the par-score benchmark, so the resulting pressure label is not an independent measure of match outcome.
10. Some delivery-reconstruction decisions for unusual extras and revised innings limits use documented working assumptions where the source data does not fully resolve event classification. Administrative penalty events are treated separately from legal-ball counts. These assumptions are retained as limitations and should not be interpreted as independent verification of every unusual event.

The final shortlist should therefore support, not replace, auction strategy and cricketing judgement.

---

# 14. Final Recommendations

The recommended decision framework is:

1. Use the IPL reliability ranking as the primary statistical shortlist.
2. Review T20I pressure performance as supplementary evidence.
3. Give greater confidence to players with larger pressure samples.
4. Investigate players whose rankings change substantially under strict eligibility.
5. Review player role and squad requirements before making an auction decision.
6. Evaluate price and availability separately from performance reliability.

The strongest candidates are not automatically the players with the highest aggregate career statistics. They are players who demonstrate comparatively strong performance under pressure with sufficient evidence.

---

# 15. Conclusion

This project establishes a reproducible, delivery-level statistical framework for evaluating player reliability under pressure.

It combines contextual pressure definitions, individual performance baselines, corrected dismissal attribution, sample-size requirements, weighted percentile ratings and sensitivity analysis.

The final output provides separate IPL batter and bowler shortlists, supported by T20I evidence and transparent methodological limitations.

The framework is designed to support more evidence-based player evaluation for the Rajasthan Royals IPL 2027 auction strategy.

---

# Appendix A: Primary Methodology Parameters

| Parameter | Selected value |
|---|---|
| Analysis period | 2022–2026 |
| IPL first-innings par validation | Match-held-out within-season folds |
| T20I first-innings par validation | Five match-held-out folds |
| First-innings pressure | At least 2 of 3 signals |
| Chase pressure RRR threshold | 10 runs per over |
| Batter eligibility, IPL | 8 pressure matches, 100 pressure balls, 8 normal matches and 100 normal balls |
| Bowler eligibility, IPL | 8 pressure matches, 120 pressure legal balls, 8 normal matches and 180 normal legal balls |
| T20I primary eligibility | 8 matches and minimum exposure in both groups |
| Batter rating weights | 30 / 25 / 30 / 15 |
| Bowler rating weights | 30 / 25 / 30 / 15 |
| Sample-size targets | 20 pressure matches and 300 pressure balls |\n| IPL normal-exposure sensitivity | Batter: 60 / 100 / 150 balls; Bowler: 90 / 120 / 180 legal balls |

# Appendix B: Reproducibility

The project uses Python and pandas for data reconstruction, statistical calculations, validation and report generation.

The analysis is divided into sequential scripts to make the pipeline reproducible and auditable. Step 73 implements the revised IPL reliability ratings, Step 65 implements the primary T20I reliability ratings, Step 74 performs the revised cross-format identity comparison, and Step 68 generates this report.

For reproduction, install the packages listed in `requirements.txt`, place authorized source datasets in the expected project data directories, and execute the pipeline scripts from the project root in their documented dependency order. This report generator expects the final ranking, rating, cross-format and audit CSV files in `reports/`. It validates the expected eligible populations and independent IPL ranking audit before writing the report. The generated CSV reports preserve player-level calculations and intermediate validation results.

The organizer-provided data pack is not copied into this documentation output. Anyone reproducing the analysis must obtain the source data through an authorized copy and follow its applicable usage terms.

## B.1 Source Code and Implementation Repository

The complete Python source code, data-processing pipeline, validation scripts, sensitivity-analysis scripts, dependency requirements and project documentation are available in the public GitHub repository:

**GitHub Repository:** [SupeRR Selector Season 2 – Rajasthan Royals IPL 2027 Auction Strategy]({GITHUB_REPOSITORY})

The repository provides implementation transparency and supports review of the analytical workflow. Organizer-provided raw datasets and locally generated intermediate files are excluded from the public repository. Reproduction therefore requires an authorized copy of the original competition data pack and compliance with its applicable usage terms. The repository contains the implementation; this report remains the authoritative explanation of the pressure definitions, rating methodology, results and limitations.

---

**Report generated:** {datetime.now().strftime("%d %B %Y")}

**Project:** SupeRR Selector Season 2

**Author:** Kamalesh S P

**GitHub:** [github.com/Kamalesh-Suresh-Kumar/](https://github.com/Kamalesh-Suresh-Kumar/)

**End of Report**
"""


# ============================================================
# 14. SAVE FINAL REPORT
# ============================================================

OUTPUT_REPORT.write_text(
    report,
    encoding="utf-8"
)

shutil.copy2(OUTPUT_REPORT, DOCS_REPORT)

print("\n" + "=" * 85)
print("FINAL REPORT GENERATED")
print("=" * 85)

print("\nReport:")
print(OUTPUT_REPORT)
print("\nGitHub documentation copy:")
print(DOCS_REPORT)

print("\nFinal ranking files:")
print(" - final_ipl_batter_top10.csv")
print(" - final_ipl_bowler_top10.csv")
print(" - final_t20i_batter_supporting_top10.csv")
print(" - final_t20i_bowler_supporting_top10.csv")
print(" - final_all_top10_rankings.csv")

print("\nAudit file:")
print(" - final_submission_data_audit.csv")
print(" - IPL independent ranking integrity audit: PASS")
print(" - IPL normal-exposure sensitivity: Steps 71 and 72 recorded results included")

print("\n" + "=" * 85)
print("STEP 68 COMPLETED")
print("=" * 85)

print("\nThe methodology report is ready for review.")
print(f"Competition context: {REGISTERED_PARTICIPANTS:,} registered; {ROUND_1_FINALISTS} Round 1 finalists ({ROUND_1_FINALIST_SHARE:.3f}% of listed registrations).")
print("GitHub repository link included in Appendix B.1.")
print("Check the final report before submitting.")
