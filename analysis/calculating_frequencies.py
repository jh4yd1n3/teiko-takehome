import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "mydb.db"
OUTPUT_PATH = ROOT / "outputs" / "frequencies.csv"



# In each sample, sum the total cell_counts from each population, then get frequencies by doing each cell_count over total cell_count
def calculate_frequencies():
    if not DB_PATH.exists():
        raise FileNotFoundError("Run python load_data.py first")

    connection = sqlite3.connect(DB_PATH)

    try:
        rows = connection.execute(
            "SELECT sample, population, count FROM cell_counts"
        ).fetchall()
    finally:
        connection.close()

    totals = {}

    for sample, population, count in rows:
        if sample not in totals:
            totals[sample] = 0

        totals[sample] += count

    frequencies = []

    for sample, population, count in rows:
        total_count = totals[sample]

        if total_count == 0:
            percentage = None
        else:
            percentage = count / total_count * 100

        frequencies.append(
            (sample, total_count, population, count, percentage)
        )

    return frequencies


def export_frequencies(frequencies):
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with OUTPUT_PATH.open("w", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(
            ["sample", "total_count", "population", "count", "percentage"]
        )
        writer.writerows(frequencies)

if __name__ == "__main__":
    frequencies = calculate_frequencies()
    export_frequencies(frequencies)
