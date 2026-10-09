# Teiko Takehome

## Run in GitHub Codespaces

Open this repository in a Codespace. From the repository root, run:

```sh
make
```

This installs dependencies, runs the full pipeline, and starts the dashboard in sequence. To run these steps individually instead:

```sh
make setup
make pipeline
make dashboard
```

Python 3.10 or newer is required. `make setup` installs the dependencies. `make pipeline` loads all source data, calculates cell frequencies, runs the treatment-response statistics, and produces the baseline subset summaries without manual intervention.

The pipeline creates `mydb.db` in the repository root and exports the results to `outputs/`. Rerunning it replaces the loaded data and regenerates the outputs. The source data is in `data/cell-count.csv`.

`make dashboard` starts Streamlit on port **8501**. In Codespaces, open the **Ports** panel and choose **Open in Browser** for port 8501. Keep the server running while using the dashboard; press **Ctrl+C** in the terminal to stop it.

## Dashboard

[Open the local dashboard](http://localhost:8501) after running `make dashboard`. In Codespaces, use the forwarded port link described above.
