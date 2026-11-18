# SupeRR Selector Season 2

## Identifying the Most Reliable Players Under Pressure

A data-driven cricket analytics project developed for **SupeRR Selector Season 2**, focused on identifying reliable batters and bowlers for Rajasthan Royals' IPL 2027 auction strategy.

The project evaluates player performance in pressure situations, compares it with normal match conditions, and combines performance, consistency, and sample-strength measures to produce evidence-based IPL reliability rankings.

---

## Project Objectives

- Define measurable pressure situations in T20 cricket.
- Reconstruct and validate ball-by-ball match data.
- Measure player performance under pressure against an appropriate normal-condition baseline.
- Evaluate consistency across qualifying matches.
- Apply eligibility thresholds so players are compared using meaningful samples.
- Generate and validate ranked IPL batter and bowler shortlists.
- Use T20I analysis as supplementary cross-format evidence.

## Final IPL Reliability Shortlists

The following are the project's final IPL Top 10 rankings. Rank 1 represents the highest reliability rating within the respective category.

### Top 10 Batters

| Rank | Player |
| ---: | --- |
| 1 | Ravindra Jadeja |
| 2 | Namboori Tilak Varma |
| 3 | Ayush Badoni |
| 4 | Nicholas Pooran |
| 5 | David Miller |
| 6 | Rinku Singh |
| 7 | Riyan Parag |
| 8 | Mahendra Singh Dhoni |
| 9 | Tim David |
| 10 | Abdul Samad |

### Top 10 Bowlers

| Rank | Player |
| ---: | --- |
| 1 | Mohit Sharma |
| 2 | Andre Russell |
| 3 | Yash Dayal |
| 4 | Yash Thakur |
| 5 | Sunil Narine |
| 6 | Harshit Rana |
| 7 | Kuldeep Yadav |
| 8 | Prasidh Krishna |
| 9 | Noor Ahmad |
| 10 | Shardul Thakur |

These are analytical reliability shortlists. They are not a complete auction-value, player-availability, squad-balance, or salary recommendation.

## Project Deliverables

The `docs/` directory contains the final project documentation and presentation.

| Deliverable | File |
| --- | --- |
| Final Methodology Report (PDF) | [`FINAL_RR_HACKATHON_METHODOLOGY_REPORT.pdf`](docs/FINAL_RR_HACKATHON_METHODOLOGY_REPORT.pdf) |
| Final Methodology Report (Markdown) | [`FINAL_RR_HACKATHON_METHODOLOGY_REPORT.md`](docs/FINAL_RR_HACKATHON_METHODOLOGY_REPORT.md) |
| Project Presentation (PPTX) | [`CRICKET_DATA_PRESSURE_PERFORMANCE.pptx`](docs/CRICKET_DATA_PRESSURE_PERFORMANCE.pptx) |
| Project Presentation (PDF) | [`CRICKET_DATA_PRESSURE_PERFORMANCE.pdf`](docs/CRICKET_DATA_PRESSURE_PERFORMANCE.pdf) |

The methodology report is the detailed reference for the pressure definitions, metric formulas, eligibility criteria, scoring methodology, validation results, sensitivity analysis, player rankings, and limitations.

## Methodology Overview

The analysis pipeline is organized into the following stages:

1. **Data integration and reconstruction** — integrates match and ball-by-ball sources and reconstructs innings and delivery-level information.
2. **Data-quality and rules validation** — audits scheduled balls, legal deliveries, extras, over numbering, innings limits, and related data-quality issues.
3. **Pressure-context modelling** — identifies pressure situations using match context and validates pressure signals and thresholds through sensitivity checks.
4. **Player performance analysis** — compares pressure performance with normal-condition baselines using role-appropriate batting and bowling metrics.
5. **Reliability scoring** — combines performance, secondary performance/risk measures, match-level consistency, and sample strength.

### Primary Scoring Weights

| Component | Weight |
| --- | ---: |
| Performance | 30% |
| Secondary metric | 25% |
| Consistency | 30% |
| Sample strength | 15% |
| **Total** | **100%** |

6. **Eligibility and robustness checks** — applies minimum sample requirements and tests ranking stability through alternative thresholds, weighting scenarios, and leave-one-match-out or related sensitivity analyses.
7. **Cross-format supporting analysis** — uses T20I results as supplementary evidence. IPL remains the primary basis for the final IPL shortlists.

For the complete pressure definition, metric formulas, thresholds, assumptions, validation results, and player-level evidence, refer to the methodology report in `docs/`.

## Repository Structure

```text
SupeRR-Selector-Season-2-Rajasthan-Royals-hackathon/
│
├── README.md
├── .gitignore
├── requirements.txt
│
├── docs/
│   ├── CRICKET_DATA_PRESSURE_PERFORMANCE.pdf
│   ├── CRICKET_DATA_PRESSURE_PERFORMANCE.pptx
│   ├── FINAL_RR_HACKATHON_METHODOLOGY_REPORT.pdf
│   └── FINAL_RR_HACKATHON_METHODOLOGY_REPORT.md
│
└── src/
    ├── 01_data_integration.py
    ├── 02_innings_reconstruction.py
    ├── ...
    └── analysis, validation, sensitivity,
        and report-generation scripts
```

The `src/` directory contains the Python pipeline, audits, validation scripts, sensitivity analyses, and report-generation scripts.

## Technology Stack

- Python
- pandas
- NumPy
- Matplotlib
- Seaborn
- scikit-learn
- SciPy
- Jupyter
- openpyxl

Exact package versions are listed in `requirements.txt`.

## Setup

### 1. Clone the Repository

```powershell
git clone https://github.com/Kamalesh-Suresh-Kumar/SupeRR-Selector-Season-2-Rajasthan-Royals-hackathon.git

cd SupeRR-Selector-Season-2-Rajasthan-Royals-hackathon
```

### 2. Create and Activate a Virtual Environment

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Data Availability and Reproducibility

The repository intentionally excludes organizer-provided raw datasets and locally generated intermediate data, including files under `Data Pack/`, `data/`, `reports/`, and `outputs/`.

This avoids redistributing source data without confirming the organizer's data-sharing permissions and keeps the repository focused on source code and methodology documentation.

To reproduce the analysis:

1. Obtain the required source data through an authorized copy of the hackathon data pack.
2. Place the data in the directory structure and filenames expected by the scripts.
3. Install the dependencies listed in `requirements.txt`.
4. Execute the scripts in their intended dependency order.
5. Review the generated audit outputs and rankings alongside the methodology report.

The source scripts and report document the intended processing and validation workflow. Reproduction may require the original authorized input files.

## Methodology Report

The complete methodology report is available in both formats:

- [View the Methodology Report (PDF)](docs/FINAL_RR_HACKATHON_METHODOLOGY_REPORT.pdf)
- [View the Methodology Report (Markdown)](docs/FINAL_RR_HACKATHON_METHODOLOGY_REPORT.md)

It documents:

- Pressure definitions and match-context criteria
- Batting and bowling performance metrics
- Eligibility rules and sample-size requirements
- Reliability rating methodology and scoring weights
- Final IPL batter and bowler rankings
- T20I supporting analysis
- Data-quality and validation checks
- Sensitivity and robustness analysis
- Limitations and reproducibility notes

## Important Notes

- Rankings are based on the defined dataset, pressure model, eligibility criteria, and scoring methodology.
- T20I analysis is supplementary; it does not replace the IPL-based final rankings.
- Ratings are relative to the eligible player population and should be interpreted within the scope of this analysis.
- The analysis has limitations arising from data coverage, sample sizes, role differences, and the operational definition of pressure. These are discussed in the methodology report.
- The final shortlists should be interpreted as analytical evidence, not standalone auction decisions.

---

## Project Information

**Project:** SupeRR Selector Season 2  
**Focus:** Identifying the Most Reliable Players Under Pressure  
**Repository:** [SupeRR Selector Season 2 – GitHub](https://github.com/Kamalesh-Suresh-Kumar/SupeRR-Selector-Season-2-Rajasthan-Royals-hackathon)  
**Author:** Kamalesh S P  
**GitHub Profile:** [Kamalesh S P](https://github.com/Kamalesh-Suresh-Kumar/)
