PYTHON ?= python
PORT ?= 8501
.DEFAULT_GOAL := all

.PHONY: all setup pipeline dashboard

all:
	$(MAKE) setup
	$(MAKE) pipeline
	$(MAKE) dashboard

setup:
	$(PYTHON) -m pip install -r requirements.txt

pipeline:
	$(PYTHON) load_data.py
	$(PYTHON) -m analysis.calculating_frequencies
	$(PYTHON) -m analysis.treatment_analysis
	$(PYTHON) -m analysis.subset_analysis

dashboard:
	$(PYTHON) -m streamlit run dashboard.py --server.address=0.0.0.0 --server.port=$(PORT) --server.headless=true
