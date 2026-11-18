import pandas as pd

df = pd.read_csv("reports/batter_reliability_ratings.csv")

r = df[df["striker_id"] == 4722].iloc[0]

columns = [
    "striker_name",
    "runs_normal",
    "balls_normal",
    "matches_normal",
    "runs_pressure",
    "balls_pressure",
    "matches_pressure",
    "strike_rate_normal",
    "strike_rate_pressure",
    "strike_rate_difference",
    "pressure_dismissals_per_100_balls",
    "normal_dismissals_per_100_balls",
    "dismissal_improvement",
    "consistency_percentage",
    "sample_score",
    "performance_score",
    "risk_score",
    "consistency_score",
    "rating_primary",
    "final_rank"
]

print("\nRASHID KHAN — DETAILED RATING COMPONENTS\n")

for col in columns:
    if col in df.columns:
        print(f"{col:45} : {r[col]}")

print("\n\nAVAILABLE BATTER REPORT FILES:")
import os
for f in os.listdir("reports"):
    if "batter" in f.lower() and f.endswith(".csv"):
        print(f)
