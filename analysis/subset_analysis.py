import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "mydb.db"
OUTPUT_DIR = ROOT / "outputs"

BASELINE_QUERY = """
    SELECT samples.sample, subjects.subject, subjects.project,
           subjects.response, subjects.sex, subjects.condition,
           subjects.treatment, samples.sample_type,
           samples.time_from_treatment_start
    FROM samples
    JOIN subjects ON samples.subject = subjects.subject
    WHERE subjects.condition = 'melanoma'
      AND subjects.treatment = 'miraclib'
      AND samples.sample_type = 'PBMC'
      AND samples.time_from_treatment_start = 0
"""


def analyze_subsets():
    if not DB_PATH.exists():
        raise FileNotFoundError("Run python load_data.py first")

    connection = sqlite3.connect(DB_PATH)
    try:
        baseline_samples = pd.read_sql_query(
            BASELINE_QUERY + " ORDER BY samples.sample", connection,
        )

        samples_by_project = pd.read_sql_query(
            f"""WITH baseline AS ({BASELINE_QUERY})
                SELECT project, COUNT(*) AS sample_count
                FROM baseline
                GROUP BY project
                ORDER BY project""",
            connection,
        )

        subjects_by_response = pd.read_sql_query(
            f"""WITH baseline AS ({BASELINE_QUERY})
                SELECT COALESCE(response, 'unknown') AS response,
                       COUNT(DISTINCT subject) AS subject_count
                FROM baseline
                GROUP BY response
                ORDER BY response""",
            connection,
        )

        subjects_by_sex = pd.read_sql_query(
            f"""WITH baseline AS ({BASELINE_QUERY})
                SELECT sex, COUNT(DISTINCT subject) AS subject_count
                FROM baseline
                GROUP BY sex
                ORDER BY sex""",
            connection,
        )

        average_b_cells = connection.execute(
            """SELECT AVG(cell_counts.count)
               FROM cell_counts
               JOIN samples ON cell_counts.sample = samples.sample
               JOIN subjects ON samples.subject = subjects.subject
               WHERE cell_counts.population = 'b_cell'
                 AND subjects.condition = 'melanoma'
                 AND subjects.sex = 'M'
                 AND subjects.response = 'yes'
                 AND samples.time_from_treatment_start = 0"""
        ).fetchone()[0]
    finally:
        connection.close()

    return {
        "baseline_samples": baseline_samples,
        "samples_by_project": samples_by_project,
        "subjects_by_response": subjects_by_response,
        "subjects_by_sex": subjects_by_sex,
        "average_b_cells": average_b_cells,
    }


def export_subset_results(results):
    OUTPUT_DIR.mkdir(exist_ok=True)
    for name in (
        "baseline_samples", "samples_by_project",
        "subjects_by_response", "subjects_by_sex",
    ):
        results[name].to_csv(OUTPUT_DIR / f"{name}.csv", index=False)

    average = results["average_b_cells"]
    average_table = pd.DataFrame({"average_b_cell_count": [average]})
    average_table.to_csv(OUTPUT_DIR / "baseline_male_b_cell_average.csv", index=False, float_format="%.2f")


if __name__ == "__main__":
    results = analyze_subsets()
    export_subset_results(results)
    print(f"Baseline melanoma miraclib PBMC samples: {len(results['baseline_samples'])}")
    for name in ("samples_by_project", "subjects_by_response", "subjects_by_sex"):
        print(f"\n{name.replace('_', ' ').title()}")
        print(results[name].to_string(index=False))
    average = results["average_b_cells"]
    if average is None:
        print("\nAverage baseline B-cell count for male melanoma responders: no matching samples")
    else:
        print(f"\nAverage baseline B-cell count for male melanoma responders: {average:.2f}")
