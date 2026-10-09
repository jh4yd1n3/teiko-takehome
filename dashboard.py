from pathlib import Path
import sqlite3

import streamlit as st
import pandas as pd
from analysis.calculating_frequencies import calculate_frequencies
from analysis.subset_analysis import analyze_subsets
from analysis.treatment_analysis import (
    analyze_treatment,
    compare_response_groups,
    create_population_boxplot,
)
from load_data import POPULATIONS

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "mydb.db"

st.set_page_config(page_title="Immune Cell Analysis", layout="wide")

st.title("Immune Cell Analysis")
st.caption("Explore sample frequencies, treatment response, and baseline subsets.")

if not DB_PATH.exists():
    st.error("The database has not been created. Run python load_data.py first.")
    st.stop()

database_tab, overview_tab, treatment_tab, baseline_tab = st.tabs(
    ["Database overview", "Cell frequencies", "Treatment response", "Baseline subsets"]
)

with database_tab:
    st.header("Relational database")
    st.write(
        "Part 1 stores all CSV records in five linked SQLite tables. "
        "Projects contain subjects; subjects provide samples; each sample has "
        "counts for the five populations. Select a table to inspect its records."
    )
    table_names = ["projects", "subjects", "samples", "populations", "cell_counts"]
    selected_table = st.selectbox("Database table", table_names)
    connection = sqlite3.connect(f"{DB_PATH.as_uri()}?mode=ro", uri=True)
    try:
        table_counts = []
        for table in table_names:
            count = connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            table_counts.append({"table": table, "rows": count})
        table_data = pd.read_sql_query(f"SELECT * FROM {selected_table}", connection)
    finally:
        connection.close()

    st.dataframe(pd.DataFrame(table_counts), hide_index=True, width="stretch")
    st.subheader(selected_table)
    st.caption(f"{len(table_data):,} records · Read-only view")
    st.dataframe(table_data, hide_index=True, width="stretch")

with overview_tab:
    st.header("Cell frequencies")
    st.write(
        "All samples across all projects, conditions, treatments, and sample types. "
        "Each population's percentage is its count divided by the sample's total "
        "count across the five cell populations, multiplied by 100."
    )
    frequencies = pd.DataFrame(
        calculate_frequencies(),
        columns=["sample", "total_count", "population", "count", "percentage"],
    )
    frequencies = frequencies.sort_values(["sample", "population"])
    column_picker, value_input = st.columns(2)
    filter_column = column_picker.selectbox("Filter column", frequencies.columns)
    filter_examples = {
        "sample": "sample00000",
        "population": "b_cell",
        "total_count": "93214",
        "count": "10908",
        "percentage": "11.70",
    }
    filter_value = value_input.text_input(
        f"Filter by {filter_column}",
        placeholder=f"e.g. {filter_examples[filter_column]}",
        help="Leave blank to show all rows. Enter the exact value you want to find.",
        key="frequency_filter_value",
    )
    displayed_frequencies = frequencies
    if filter_value.strip():
        if filter_column in ("total_count", "count", "percentage"):
            try:
                numeric_value = float(filter_value)
            except ValueError:
                st.warning("Enter a number for this column.")
            else:
                values = frequencies[filter_column]
                if filter_column == "percentage":
                    values = values.round(2)
                displayed_frequencies = frequencies[values == numeric_value]
        else:
            displayed_frequencies = frequencies[
                frequencies[filter_column].str.casefold() == filter_value.strip().casefold()
            ]
    st.caption(
        f"Showing {len(displayed_frequencies):,} of {len(frequencies):,} population rows. "
        "Filters match exact values; percentages match the displayed two-decimal value. "
        "Sample totals always include all five populations."
    )
    if displayed_frequencies.empty:
        st.info("No rows match this value.")
    st.dataframe(
        displayed_frequencies,
        hide_index=True,
        width="stretch",
        column_config={
            "percentage": st.column_config.NumberColumn("percentage", format="%.2f"),
        },
    )
    st.caption("Percentages are displayed to two decimals. A missing percentage means the sample's total count is zero.")
    st.download_button(
        "Download displayed frequencies",
        data=displayed_frequencies.to_csv(index=False).encode("utf-8"),
        file_name="frequencies.csv",
        mime="text/csv",
    )

with treatment_tab:
    st.header("Treatment response")
    st.write(
        "Melanoma subjects receiving miraclib, using PBMC samples with a recorded "
        "yes/no treatment response. Each subject contributes one average percentage "
        "per population across their available samples and collection days."
    )
    subject_averages = analyze_treatment()
    if subject_averages.empty:
        st.info("No eligible samples with valid cell percentages were found.")
    else:
        responder_count = subject_averages.loc[
            subject_averages["response"] == "yes", "subject"
        ].nunique()
        nonresponder_count = subject_averages.loc[
            subject_averages["response"] == "no", "subject"
        ].nunique()
        st.caption(f"Responders: {responder_count} subjects · Non-responders: {nonresponder_count} subjects")

        if "plot_population" not in st.session_state:
            st.session_state["plot_population"] = POPULATIONS[0]

        previous_column, next_column = st.columns(2)
        if previous_column.button("← Previous population"):
            current_index = POPULATIONS.index(st.session_state["plot_population"])
            st.session_state["plot_population"] = POPULATIONS[(current_index - 1) % len(POPULATIONS)]
        with next_column:
            next_clicked = st.container(horizontal=True, horizontal_alignment="right").button(
                "Next population →"
            )
        if next_clicked:
            current_index = POPULATIONS.index(st.session_state["plot_population"])
            st.session_state["plot_population"] = POPULATIONS[(current_index + 1) % len(POPULATIONS)]

        population = st.selectbox(
            "Cell population",
            POPULATIONS,
            format_func=lambda name: name.replace("_", " ").title(),
            key="plot_population",
        )
        st.caption(f"Plot {POPULATIONS.index(population) + 1} of {len(POPULATIONS)}")
        figure = create_population_boxplot(subject_averages, population)
        st.plotly_chart(figure, width="stretch")

        st.subheader("Statistical comparison")
        st.write(
            "Two-sided Mann–Whitney U tests compare the groups' distributions. "
            "Holm adjustment accounts for the five population tests; significance "
            "is assessed at an adjusted p-value of 0.05. Median differences are "
            "in percentage points (responders minus non-responders)."
        )
        try:
            statistics = compare_response_groups(subject_averages)
        except ValueError as error:
            st.warning(str(error))
        else:
            st.dataframe(statistics, hide_index=True, width="stretch")
            significant = statistics.loc[statistics["significant"], "population"].tolist()
            if significant:
                st.write("Significant after Holm adjustment: " + ", ".join(significant))
            else:
                st.info("No populations meet the significance threshold after Holm adjustment.")
        st.caption(
            "This exploratory comparison includes post-treatment measurements and "
            "averages over time. It does not establish a treatment effect or validate "
            "prediction before treatment, and does not adjust for project or demographics."
        )

with baseline_tab:
    st.header("Baseline subsets")
    st.write(
        "Baseline samples (day 0) from melanoma subjects treated with miraclib, "
        "restricted to PBMC. Summaries count samples by project and distinct "
        "subjects by response and sex."
    )
    subset_results = analyze_subsets()
    baseline_samples = subset_results["baseline_samples"]
    st.metric("Matching baseline samples", f"{len(baseline_samples):,}")

    st.subheader("Baseline samples")
    st.dataframe(baseline_samples, hide_index=True, width="stretch")

    project_column, response_column, sex_column = st.columns(3)
    with project_column:
        st.subheader("Samples by project")
        st.caption("Number of qualifying baseline samples")
        st.dataframe(subset_results["samples_by_project"], hide_index=True, width="stretch")
    with response_column:
        st.subheader("Subjects by response")
        st.caption("yes = responders; no = non-responders")
        st.dataframe(subset_results["subjects_by_response"], hide_index=True, width="stretch")
    with sex_column:
        st.subheader("Subjects by sex")
        st.caption("M = male; F = female")
        st.dataframe(subset_results["subjects_by_sex"], hide_index=True, width="stretch")

    st.subheader("Average B-cell count for baseline male melanoma responders")
    st.write(
        "The separate B-cell average uses male melanoma responders at day 0 "
        "across all treatments and sample types, and measures raw counts rather "
        "than percentages."
    )
    average_b_cells = subset_results["average_b_cells"]
    if average_b_cells is None:
        st.info("No samples meet the criteria for this average.")
    else:
        st.metric("Average B-cell count", f"{average_b_cells:.2f}")
