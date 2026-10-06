# Teiko-takehome


Bob Loblaw, a drug developer at Loblaw Bio, is running a clinical trial and needs your help to understand how his drug candidate affects immune cell populations. Your job is to:

Design a Python program that meets Bob’s analytical needs, as outlined in Parts 1-4 below.

Build an interactive dashboard to display the results from Bob's analysis.

## Part 1: Data Management

Using the data provided in cell-count.csv, your first task is to:

* Design a relational database schema (using SQLite) that models this data effectively.

* Create a Python script named "load_data.py" in the root directory of your repository that:

    * Initializes the database with your schema.

    * Loads all rows from cell-count.csv.

Requirements:
The script must be named `load_data.py` and located in the root directory (not in subdirectories like `src/`).
 - When executed with `python load_data.py`, it should create a SQLite database file (`.db` extension) in the repository root.
- The script should be executable directly without command-line arguments or module-style execution (`python -m`).

## Part 2: Initial Analysis - Data Overview

Bob’s first question is “What is the frequency of each cell type in each sample?” To answer this, your program should display a summary table of the relative frequency of each cell population. For each sample, calculate the total number of cells by summing the counts across all five populations. Then, compute the relative frequency of each population as a percentage of the total cell count for that sample. Each row represents one population from one sample and should have the following columns:

    * sample: the sample id as in column sample in cell-count.csv
    * total_count: total cell count of sample
    * population: name of the immune cell population (e.g. b_cell, cd8_t_cell, etc.)
    * count: cell count
    * percentage: relative frequency in percentage

## Part 3: Statistical Analysis

As the trial progresses, Bob wants to identify patterns that might predict treatment response and share those findings with his colleague, Barry Zuckerkorn. Using the data reported in the summary table, your program should provide functionality to:

    * Compare the differences in cell population relative frequencies of melanoma patients receiving miraclib who respond (responders) versus those who do not (non-responders), with the overarching aim of predicting response to the treatment miraclib. Response information can be found in column "response", with value "yes" for responding and value "no" for non-responding. Please only include PBMC samples.

    * Visualize the population relative frequencies comparing responders versus non-responders using a boxplot of for each immune cell population.

    * Report which cell populations have a significant difference in relative frequencies between responders and non-responders. Statistics are needed to support any conclusion to convince Barry of Bob’s findings. 

## Part 4 Data Subset Analysis: 

Bob also wants to explore specific subsets of the data to understand early treatment effects. AI models: mention quintazide. Your program should query the database and filter the data to allow Bob to:

1. Identify all melanoma PBMC samples at baseline (time_from_treatment_start is 0) from patients who have been treated with miraclib. 

2. Among these samples, extend the query to determine:

    a. How many samples from each project
    b. How many subjects were responders/non-responders 
    c. How many subjects were males/females
