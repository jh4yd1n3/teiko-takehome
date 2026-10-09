import argparse
import sqlite3
from pathlib import Path
import pandas as pd
import plotly.express as px
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests
from analysis.calculating_frequencies import calculate_frequencies
from load_data import POPULATIONS

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "mydb.db"
OUTPUT_DIR = ROOT / "outputs"

def analyze_treatment():
    if not DB_PATH.exists():
        raise FileNotFoundError("Run python load_data.py first")

    frequencies = calculate_frequencies()
    connection = sqlite3.connect(DB_PATH)

    try:
        # Join with Samples and Subjects, filter on subjects and the samples ID will be the bridge
        filtered_samples = connection.execute(
            """
            SELECT samples.sample, subjects.subject, subjects.response
            FROM samples
            JOIN subjects
                ON samples.subject = subjects.subject
            WHERE subjects.condition = 'melanoma'
            AND subjects.treatment = 'miraclib'
            AND samples.sample_type = 'PBMC'
            AND subjects.response IN ('yes', 'no')
            """
        ).fetchall()
    finally:
        connection.close()

    # Returned tuple will be --> (sample_A, subject_A, subject_A_response)

    # Set up calculated frequencies and filtered samples into a data frame for later merge
    frequency_data = pd.DataFrame(
        frequencies,
        columns=["sample", "total_count", "population", "count", "percentage"],
    )
    sample_data = pd.DataFrame(
        filtered_samples,
        columns=["sample", "subject", "response"],
    )

    # Find matches here
    filtered_frequencies = frequency_data.merge(
        sample_data,
        on="sample",
        how="inner",
        validate="many_to_one",
    )

    # Calculate average across percentages to account for multiple samples per subject
    valid_frequencies = filtered_frequencies.dropna(subset=["percentage"])
    subject_averages = (
        valid_frequencies
        .groupby(["subject", "population", "response"], as_index=False)["percentage"]
        .mean()
        .rename(columns={"percentage": "mean_percentage"})
    )

    return subject_averages

# Use manwhitney U to compare between the two groups (yes and no);
# Holmes to make adjustments that account for testing multiHolmes to make adjustments that account for testing multiple ppulations
def compare_response_groups(subject_averages):
    results = []
    for population in POPULATIONS:
        population_data = subject_averages[
            subject_averages["population"] == population
        ]
        responders = population_data.loc[
            population_data["response"] == "yes", "mean_percentage"
        ].dropna()
        nonresponders = population_data.loc[
            population_data["response"] == "no", "mean_percentage"
        ].dropna()

        if len(responders) < 2 or len(nonresponders) < 2:
            raise ValueError(f"Need at least two subjects in each response group for {population}")

        test = mannwhitneyu(
            responders, nonresponders,
            alternative="two-sided", method="asymptotic",
        )
        results.append({
            "population": population,
            "responder_subjects": len(responders),
            "nonresponder_subjects": len(nonresponders),
            "responder_median_percentage": responders.median(),
            "nonresponder_median_percentage": nonresponders.median(),
            "median_difference_pp": responders.median() - nonresponders.median(),
            "rank_biserial": 2 * test.statistic / (len(responders) * len(nonresponders)) - 1,
            "u_statistic": test.statistic,
            "p_value": test.pvalue,
        })

    statistics = pd.DataFrame(results)
    significant, adjusted_p_values, _, _ = multipletests(
        statistics["p_value"], alpha=0.05, method="holm",
    )
    statistics["adjusted_p_value"] = adjusted_p_values
    statistics["significant"] = significant
    return statistics


def export_treatment_results(subject_averages, statistics):
    OUTPUT_DIR.mkdir(exist_ok=True)
    subject_averages.to_csv(OUTPUT_DIR / "treatment_subject_averages.csv", index=False)
    statistics.to_csv(OUTPUT_DIR / "treatment_statistics.csv", index=False)


# Create boxplots after averaging
def create_population_boxplot(subject_averages, population):
    population_data = subject_averages[
        subject_averages["population"] == population
    ]

    figure = px.box(
        population_data,
        x="response",
        y="mean_percentage",
        color="response",
        category_orders={"response": ["yes", "no"]},
        title=population.replace("_", " ").title(),
        labels={
            "response": "Treatment response",
            "mean_percentage": "Subject-average frequency (%)",
        },
    )

    return figure


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--show-plots", action="store_true")
    args = parser.parse_args()
    subject_averages = analyze_treatment()
    statistics = compare_response_groups(subject_averages)
    export_treatment_results(subject_averages, statistics)
    print(statistics.to_string(index=False, float_format=lambda value: f"{value:.6g}"))
    significant_populations = statistics.loc[statistics["significant"], "population"].tolist()
    print("Significant after Holm adjustment:", ", ".join(significant_populations) or "None")
    if args.show_plots:
        for population in POPULATIONS:
            figure = create_population_boxplot(subject_averages, population)
            figure.show(renderer="browser")
