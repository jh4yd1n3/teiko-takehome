import csv
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "cell-count.csv"
DB_PATH = ROOT / "mydb.db"
POPULATIONS = ("b_cell", "cd8_t_cell", "cd4_t_cell", "nk_cell", "monocyte")
SUBJECT_FIELDS = ("project", "subject", "condition", "age", "sex", "treatment", "response")
SCHEMA = (
    """CREATE TABLE IF NOT EXISTS projects (
        project TEXT PRIMARY KEY NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS subjects (
        subject TEXT PRIMARY KEY NOT NULL,
        project TEXT NOT NULL REFERENCES projects(project),
        condition TEXT NOT NULL,
        age INTEGER NOT NULL CHECK (age >= 0),
        sex TEXT NOT NULL CHECK (sex IN ('M', 'F')),
        treatment TEXT NOT NULL,
        response TEXT CHECK (response IN ('yes', 'no'))
    )""",
    """CREATE TABLE IF NOT EXISTS samples (
        sample TEXT PRIMARY KEY NOT NULL,
        subject TEXT NOT NULL REFERENCES subjects(subject),
        sample_type TEXT NOT NULL,
        time_from_treatment_start INTEGER NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS populations (
        population TEXT PRIMARY KEY NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS cell_counts (
        sample TEXT NOT NULL REFERENCES samples(sample),
        population TEXT NOT NULL REFERENCES populations(population),
        count INTEGER NOT NULL CHECK (count >= 0),
        PRIMARY KEY (sample, population)
    )""",
    "CREATE INDEX IF NOT EXISTS samples_subject_idx ON samples(subject)",
    "CREATE INDEX IF NOT EXISTS subjects_project_idx ON subjects(project)",
)


def read_csv(csv_path):
    projects = set()
    subjects = {}
    samples = []
    counts = []
    seen_samples = set()
    required_columns = SUBJECT_FIELDS + ("sample", "sample_type", "time_from_treatment_start") + POPULATIONS

    with Path(csv_path).open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        for column in required_columns:
            if column not in (reader.fieldnames or []):
                raise ValueError(f"Missing CSV column: {column}")

        for line, row in enumerate(reader, start=2):
            try:
                for column in required_columns:
                    if row[column] is None:
                        raise ValueError(f"Missing {column}")
                    if column != "response" and row[column].strip() == "":
                        raise ValueError(f"Missing {column}")

                subject_id = row["subject"]
                sample_id = row["sample"]
                age = int(row["age"])
                day = int(row["time_from_treatment_start"])
                response = row["response"]
                if response == "":
                    response = None
                if age < 0:
                    raise ValueError("Age cannot be negative")
                if row["sex"] not in ("M", "F"):
                    raise ValueError("Sex must be M or F")
                if response not in ("yes", "no", None):
                    raise ValueError("Response must be yes, no, or blank")

                subject_data = (
                    subject_id,
                    row["project"],
                    row["condition"],
                    age,
                    row["sex"],
                    row["treatment"],
                    response,
                )
                if subject_id in subjects:
                    if subjects[subject_id] != subject_data:
                        raise ValueError(f"Conflicting metadata for subject {subject_id}")
                else:
                    subjects[subject_id] = subject_data
                projects.add(row["project"])

                if sample_id in seen_samples:
                    raise ValueError(f"Duplicate sample {sample_id}")
                seen_samples.add(sample_id)
                samples.append((sample_id, subject_id, row["sample_type"], day))

                for population in POPULATIONS:
                    count = int(row[population])
                    if count < 0:
                        raise ValueError(f"Negative count for {population}")
                    counts.append((sample_id, population, count))
            except (ValueError, TypeError) as error:
                raise ValueError(f"CSV line {line}: {error}") from error

    if not samples:
        raise ValueError("CSV contains no samples")
    return projects, subjects, samples, counts


def load_data(csv_path=CSV_PATH, db_path=DB_PATH):
    projects, subjects, samples, counts = read_csv(csv_path)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        with connection:
            connection.execute("BEGIN")
            for statement in SCHEMA:
                connection.execute(statement)

            connection.execute("DELETE FROM cell_counts")
            connection.execute("DELETE FROM samples")
            connection.execute("DELETE FROM subjects")
            connection.execute("DELETE FROM populations")
            connection.execute("DELETE FROM projects")

            for project in sorted(projects):
                connection.execute("INSERT INTO projects (project) VALUES (?)", (project,))
            for population in POPULATIONS:
                connection.execute("INSERT INTO populations (population) VALUES (?)", (population,))
            for subject in subjects.values():
                connection.execute(
                    """INSERT INTO subjects
                       (subject, project, condition, age, sex, treatment, response)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    subject,
                )
            for sample in samples:
                connection.execute(
                    """INSERT INTO samples
                       (sample, subject, sample_type, time_from_treatment_start)
                       VALUES (?, ?, ?, ?)""",
                    sample,
                )
            for cell_count in counts:
                connection.execute(
                    "INSERT INTO cell_counts (sample, population, count) VALUES (?, ?, ?)",
                    cell_count,
                )
    finally:
        connection.close()
    return len(samples)


if __name__ == "__main__":
    sample_count = load_data()
    print(f"Loaded {sample_count:,} samples into {DB_PATH}")
