
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
| Batters | 32 |
| Bowlers | 49 |

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
| Batters | 41 |
| Bowlers | 62 |

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

# 8. Final IPL Auction Recommendations

IPL is the primary competition for the auction shortlist.

## 8.1 Top 10 Batters

| rank | player_name | rating |
| --- | --- | --- |
| 1 | Ravindra Jadeja | 90.78 |
| 2 | Namboori Tilak Varma | 89.39 |
| 3 | Ayush Badoni | 88.91 |
| 4 | Nicholas Pooran | 87.26 |
| 5 | David Miller | 84.94 |
| 6 | Rinku Singh | 82.50 |
| 7 | Riyan Parag | 73.99 |
| 8 | Mahendra Singh Dhoni | 73.28 |
| 9 | Tim David | 70.93 |
| 10 | Abdul Samad | 68.18 |

### Batter-level performance evidence

The following table compares each shortlisted batter's pressure performance with their normal-situation baseline. Positive strike-rate improvement indicates faster scoring under pressure; positive dismissal-rate improvement indicates fewer dismissals per 100 balls under pressure.

| rank | player_name | Qualifying pressure matches | Pressure balls | Normal SR | Pressure SR | SR improvement | Normal dismissals / 100 balls | Pressure dismissals / 100 balls | Dismissal improvement | Consistency % | Rating |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Ravindra Jadeja | 22.00 | 380.00 | 130.56 | 142.22 | 11.67 | 4.63 | 3.21 | 1.42 | 77.27 | 90.78 |
| 2 | Namboori Tilak Varma | 14.00 | 256.00 | 135.55 | 177.90 | 42.35 | 3.97 | 3.99 | -0.01 | 85.71 | 89.39 |
| 3 | Ayush Badoni | 21.00 | 341.00 | 129.30 | 155.89 | 26.59 | 5.52 | 5.48 | 0.04 | 76.19 | 88.91 |
| 4 | Nicholas Pooran | 16.00 | 303.00 | 161.21 | 182.41 | 21.20 | 4.85 | 4.01 | 0.84 | 68.75 | 87.26 |
| 5 | David Miller | 20.00 | 289.00 | 131.14 | 168.77 | 37.62 | 3.20 | 4.10 | -0.90 | 70.00 | 84.94 |
| 6 | Rinku Singh | 21.00 | 326.00 | 137.27 | 170.03 | 32.76 | 3.87 | 3.86 | 0.02 | 61.90 | 82.50 |
| 7 | Riyan Parag | 11.00 | 155.00 | 145.24 | 181.61 | 36.37 | 5.36 | 4.60 | 0.76 | 54.55 | 73.99 |
| 8 | Mahendra Singh Dhoni | 23.00 | 317.00 | 145.80 | 151.20 | 5.40 | 5.34 | 4.52 | 0.83 | 56.52 | 73.28 |
| 9 | Tim David | 17.00 | 250.00 | 178.69 | 176.51 | -2.18 | 6.01 | 4.27 | 1.74 | 64.71 | 70.93 |
| 10 | Abdul Samad | 17.00 | 206.00 | 145.88 | 153.04 | 7.17 | 6.70 | 7.39 | -0.69 | 64.71 | 68.18 |

### Batter reliability-rating components

The component scores show how the primary weighted rating was assembled. Performance, secondary-metric and consistency values are percentile scores within the eligible IPL batter population. The sample score is the direct exposure score described in Section 7.5.

| rank | player_name | Performance percentile | Secondary metric percentile | Consistency percentile | Sample score | Final rating |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Ravindra Jadeja | 75.00 | 96.88 | 96.88 | 100.00 | 90.78 |
| 2 | Namboori Tilak Varma | 100.00 | 71.88 | 100.00 | 76.13 | 89.39 |
| 3 | Ayush Badoni | 87.50 | 78.12 | 93.75 | 100.00 | 88.91 |
| 4 | Nicholas Pooran | 84.38 | 93.75 | 84.38 | 88.00 | 87.26 |
| 5 | David Miller | 96.88 | 59.38 | 87.50 | 98.53 | 84.94 |
| 6 | Rinku Singh | 90.62 | 75.00 | 71.88 | 100.00 | 82.50 |
| 7 | Riyan Parag | 93.75 | 87.50 | 53.12 | 53.67 | 73.99 |
| 8 | Mahendra Singh Dhoni | 53.12 | 90.62 | 65.62 | 100.00 | 73.28 |
| 9 | Tim David | 34.38 | 100.00 | 76.56 | 84.33 | 70.93 |
| 10 | Abdul Samad | 59.38 | 62.50 | 76.56 | 78.47 | 68.18 |

## 8.2 Top 10 Bowlers

| rank | player_name | rating |
| --- | --- | --- |
| 1 | Mohit Sharma | 96.21 |
| 2 | Andre Russell | 85.99 |
| 3 | Yash Dayal | 84.78 |
| 4 | Yash Thakur | 81.84 |
| 5 | Sunil Narine | 81.73 |
| 6 | Harshit Rana | 79.19 |
| 7 | Kuldeep Yadav | 78.01 |
| 8 | Prasidh Krishna | 77.52 |
| 9 | Noor Ahmad | 76.79 |
| 10 | Shardul Thakur | 76.57 |

### Bowler-level performance evidence

The table compares each shortlisted bowler's pressure economy with their normal-situation economy. Positive economy improvement indicates fewer runs conceded per over under pressure. Pressure wickets are bowler-credit wickets per 100 pressure legal balls.

| rank | player_name | Qualifying pressure matches | Pressure legal balls | Normal economy | Pressure economy | Economy improvement | Wickets / 100 legal balls | Consistency % | Rating |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Mohit Sharma | 17.00 | 224.00 | 10.48 | 8.15 | 2.33 | 11.61 | 82.35 | 96.21 |
| 2 | Andre Russell | 15.00 | 161.00 | 11.07 | 9.59 | 1.48 | 9.94 | 73.33 | 85.99 |
| 3 | Yash Dayal | 22.00 | 177.00 | 9.99 | 8.07 | 1.93 | 9.04 | 68.18 | 84.78 |
| 4 | Yash Thakur | 11.00 | 120.00 | 11.00 | 9.45 | 1.55 | 10.00 | 72.73 | 81.84 |
| 5 | Sunil Narine | 25.00 | 304.00 | 7.25 | 5.38 | 1.87 | 6.58 | 80.00 | 81.73 |
| 6 | Harshit Rana | 15.00 | 163.00 | 9.95 | 8.26 | 1.68 | 6.75 | 80.00 | 79.19 |
| 7 | Kuldeep Yadav | 23.00 | 249.00 | 8.52 | 7.36 | 1.16 | 7.63 | 78.26 | 78.01 |
| 8 | Prasidh Krishna | 18.00 | 211.00 | 9.01 | 8.04 | 0.96 | 7.58 | 72.22 | 77.52 |
| 9 | Noor Ahmad | 18.00 | 223.00 | 8.46 | 7.05 | 1.41 | 8.52 | 66.67 | 76.79 |
| 10 | Shardul Thakur | 15.00 | 157.00 | 10.66 | 9.71 | 0.94 | 7.01 | 80.00 | 76.57 |

### Bowler reliability-rating components

The component scores show how the primary weighted rating was assembled. Performance, secondary-metric and consistency values are percentile scores within the eligible IPL bowler population. The sample score is the direct exposure score described in Section 7.5.

| rank | player_name | Performance percentile | Secondary metric percentile | Consistency percentile | Sample score | Final rating |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Mohit Sharma | 97.96 | 100.00 | 98.98 | 80.87 | 96.21 |
| 2 | Andre Russell | 87.76 | 95.92 | 85.71 | 66.47 | 85.99 |
| 3 | Yash Dayal | 95.92 | 85.71 | 73.47 | 83.60 | 84.78 |
| 4 | Yash Thakur | 89.80 | 89.80 | 83.67 | 49.00 | 81.84 |
| 5 | Sunil Narine | 93.88 | 42.86 | 92.86 | 100.00 | 81.73 |
| 6 | Harshit Rana | 91.84 | 55.10 | 92.86 | 66.73 | 79.19 |
| 7 | Kuldeep Yadav | 75.51 | 60.20 | 87.76 | 93.20 | 78.01 |
| 8 | Prasidh Krishna | 69.39 | 79.59 | 81.63 | 82.13 | 77.52 |
| 9 | Noor Ahmad | 85.71 | 74.49 | 66.33 | 83.73 | 76.79 |
| 10 | Shardul Thakur | 67.35 | 74.49 | 92.86 | 65.93 | 76.57 |

These rankings are based on the primary IPL reliability rating.

They should be interpreted alongside player roles, squad balance, auction price, availability and team requirements.

---

# 9. T20I Supporting Evidence

T20I provides an additional view of how players perform under pressure in international T20 cricket.

It is supplementary evidence rather than a replacement for IPL performance.

## 9.1 Top 10 T20I Batters

| rank | player_name | rating |
| --- | --- | --- |
| 1 | Jason Holder | 89.88 |
| 2 | Nurul Hasan | 79.88 |
| 3 | Matthew Wade | 79.27 |
| 4 | Sikandar Raza | 79.02 |
| 5 | Dasun Shanaka | 76.28 |
| 6 | Rovman Powell | 76.28 |
| 7 | Curtis Campher | 75.98 |
| 8 | Mark Chapman | 75.12 |
| 9 | Ryan Burl | 67.26 |
| 10 | Gareth Delany | 65.98 |

## 9.2 Top 10 T20I Bowlers

| rank | player_name | rating |
| --- | --- | --- |
| 1 | Abrar Ahmed | 86.21 |
| 2 | Shadab Khan | 84.35 |
| 3 | Mohammad Nawaz | 83.79 |
| 4 | Arshdeep Singh | 83.10 |
| 5 | Benjamin Sears | 81.94 |
| 6 | Varun Chakravarthy | 81.53 |
| 7 | Adam Zampa | 81.53 |
| 8 | Wanindu Hasaranga | 78.35 |
| 9 | Rashid Khan | 77.94 |
| 10 | Mustafizur Rahman | 76.81 |

The T20I lists use the primary eligibility scenario.

---

# 10. Cross-Format Comparison

Players were matched using player IDs, with names checked for identity consistency.

The comparison covered the eligible IPL and T20I populations.

## 10.1 Matching Results

| player_type | ipl_eligible_players | t20i_eligible_players | matched_player_ids | unmatched_ipl_players | unmatched_t20i_players | confirmed_id_and_name_matches | identity_conflicts | top10_both_formats | top10_ipl_only | top10_t20i_only |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Batter | 32 | 41 | 8 | 24 | 33 | 8 | 0 | 0 | 3 | 1 |
| Bowler | 49 | 62 | 17 | 32 | 45 | 17 | 0 | 0 | 1 | 5 |

The matched-player counts describe only players who satisfy the eligibility rules in both formats. The top-10 overlap columns therefore measure overlap within this matched subset, not overlap across the complete IPL and T20I top-10 lists. Unmatched players are not evidence of poor performance; they simply lack a qualifying comparison population in the other format.

No identity conflicts were detected in the matched player records.

## 10.2 Cross-Format Top-10 Evidence

| player_type | player_name | ipl_rank | ipl_rating | t20i_rank | t20i_rating | cross_format_evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Batter | Namboori Tilak Varma | 2.0 | 89.39 | 19.0 | 52.07 | TOP10_IPL_ONLY |
| Batter | David Miller | 5.0 | 84.94 | 36.0 | 34.27 | TOP10_IPL_ONLY |
| Batter | Tim David | 9.0 | 70.93 | 11.0 | 65.85 | TOP10_IPL_ONLY |
| Batter | Rovman Powell | 21.0 | 41.22 | 6.0 | 76.28 | TOP10_T20I_ONLY |
| Bowler | Kuldeep Yadav | 7.0 | 78.01 | 19.0 | 64.07 | TOP10_IPL_ONLY |
| Bowler | Varun Chakravarthy | 14.0 | 73.97 | 6.0 | 81.53 | TOP10_T20I_ONLY |
| Bowler | Mustafizur Rahman | 29.0 | 48.86 | 10.0 | 76.81 | TOP10_T20I_ONLY |
| Bowler | Rashid Khan | 36.0 | 38.16 | 9.0 | 77.94 | TOP10_T20I_ONLY |
| Bowler | Arshdeep Singh | 41.0 | 30.41 | 4.0 | 83.10 | TOP10_T20I_ONLY |
| Bowler | Wanindu Hasaranga | 48.0 | 23.69 | 8.0 | 78.35 | TOP10_T20I_ONLY |

The Step 74 cross-format evidence table reports players who could be identity-matched across both eligible format populations. Its top-10 overlap result applies to that matched subset only; players who were eligible in one format but not the other cannot be treated as a cross-format ranking comparison.

This does not mean that the rankings are contradictory. The formats have different competitive environments, eligible populations and exposure distributions.

T20I performance should be treated as additional evidence, not as a direct forecast of IPL performance.

---

# 11. Sensitivity Analysis

The project tests whether the rankings remain stable when eligibility thresholds change.

## 11.1 IPL Normal-Situation Exposure Sensitivity

The revised IPL eligibility rule was tested against alternative minimum normal-situation ball exposures. Pressure-side requirements and the minimum of eight normal matches were retained.

| player_type | normal_ball_threshold | eligible_players | primary_top10_overlap |
| --- | --- | --- | --- |
| Batter | 60 | 34 | 9/10 |
| Batter | 100 | 32 | 9/10 |
| Batter | 150 | 31 | 8/10 |
| Bowler | 90 | 49 | 10/10 |
| Bowler | 120 | 49 | 10/10 |
| Bowler | 180 | 49 | 10/10 |

For batters, the eligible population changes as the minimum normal-ball requirement increases. The primary 100-ball threshold retains 32 eligible batters and preserves nine of the original ten shortlisted batters. The 150-ball threshold reduces the population to 31 and preserves eight of the ten.

For bowlers, all 49 eligible players remain eligible at the tested normal legal-ball thresholds, and the primary top 10 remains unchanged in all three comparisons.

## 11.2 T20I Eligible Population by Scenario

| scenario | player_type | eligible_players | top10_available |
| --- | --- | --- | --- |
| flexible | Batter | 55 | 10 |
| flexible | Bowler | 79 | 10 |
| primary | Batter | 41 | 10 |
| primary | Bowler | 62 | 10 |
| strict | Batter | 20 | 10 |
| strict | Bowler | 22 | 10 |

## 11.3 T20I Top-10 Ranking Overlap

| player_type | comparison | common_top10_players | top10_overlap_pct | jaccard_overlap_pct |
| --- | --- | --- | --- | --- |
| Batter | Flexible vs Primary | 8 | 80.0 | 66.67 |
| Batter | Primary vs Strict | 5 | 50.0 | 33.33 |
| Batter | Flexible vs Strict | 4 | 40.0 | 25.0 |
| Bowler | Flexible vs Primary | 7 | 70.0 | 53.85 |
| Bowler | Primary vs Strict | 8 | 80.0 | 66.67 |
| Bowler | Flexible vs Strict | 5 | 50.0 | 33.33 |

## 11.4 Alternative Weighting Sensitivity

The alternative weight scenarios are defined in Section 7.6. Where the completed pipeline has generated sensitivity outputs, the observed Top-10 overlap with the primary scenario is shown below. The overlap measures membership, not rank-order stability.

**IPL revised-rating sensitivity**

| player_type | scenario | primary_top10_overlap | overlap_percentage |
| --- | --- | --- | --- |
| Batter | primary | 10 | 100 |
| Batter | performance_heavy | 10 | 100 |
| Batter | consistency_heavy | 10 | 100 |
| Batter | sample_conservative | 10 | 100 |
| Bowler | primary | 10 | 100 |
| Bowler | performance_heavy | 9 | 90 |
| Bowler | consistency_heavy | 9 | 90 |
| Bowler | sample_conservative | 9 | 90 |

**T20I primary-rating sensitivity**

| player_type | scenario | common_top10_players | top10_overlap_pct |
| --- | --- | --- | --- |
| Batter | performance_heavy | 9 | 90.0 |
| Batter | consistency_heavy | 9 | 90.0 |
| Batter | sample_conservative | 10 | 100.0 |
| Bowler | performance_heavy | 9 | 90.0 |
| Bowler | consistency_heavy | 9 | 90.0 |
| Bowler | sample_conservative | 10 | 100.0 |

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
| Sample-size targets | 20 pressure matches and 300 pressure balls |
| IPL normal-exposure sensitivity | Batter: 60 / 100 / 150 balls; Bowler: 90 / 120 / 180 legal balls |

# Appendix B: Reproducibility

The project uses Python and pandas for data reconstruction, statistical calculations, validation and report generation.

The analysis is divided into sequential scripts to make the pipeline reproducible and auditable. Step 73 implements the revised IPL reliability ratings, Step 65 implements the primary T20I reliability ratings, Step 74 performs the revised cross-format identity comparison, and Step 68 generates this report.

For reproduction, install the packages listed in `requirements.txt`, place authorized source datasets in the expected project data directories, and execute the pipeline scripts from the project root in their documented dependency order. This report generator expects the final ranking, rating, cross-format and audit CSV files in `reports/`. It validates the expected eligible populations and independent IPL ranking audit before writing the report. The generated CSV reports preserve player-level calculations and intermediate validation results.

The organizer-provided data pack is not copied into this documentation output. Anyone reproducing the analysis must obtain the source data through an authorized copy and follow its applicable usage terms.

---

**Report generated:** 18 November 2026

**Project:** SupeRR Selector Season 2

**End of Report**
