# ---- Starter Makefile for BTC Blockspace Research ----
# Usage:
#   make init
#   make extract_factors extract_elasticity extract_seasonality
#   make paper
#
# Requirements: Python 3.11+, `pip install google-cloud-bigquery pandas-gbq pyarrow pandas`,
# and valid GCP credentials (GOOGLE_APPLICATION_CREDENTIALS).

PY ?= python
PROJECT ?= your-gcp-project-id
LOCATION ?= US

SQL_DIR := sql
DATA_RAW := data/raw
PAPER := paper/paper.qmd

# Helper: run a SQL file on BigQuery and save to Parquet locally
define RUN_SQL_TO_PARQUET
$(PY) scripts/run_query.py --project $(PROJECT) --location $(LOCATION) --sql $(1) --out $(2)
endef

init:
	mkdir -p data/raw data/derived data/figs

extract_factors: init
	$(call RUN_SQL_TO_PARQUET,$(SQL_DIR)/factors.sql,$(DATA_RAW)/factors.parquet)

extract_elasticity: init
	$(call RUN_SQL_TO_PARQUET,$(SQL_DIR)/elasticity.sql,$(DATA_RAW)/elasticity.parquet)

extract_seasonality: init
	$(call RUN_SQL_TO_PARQUET,$(SQL_DIR)/seasonality.sql,$(DATA_RAW)/seasonality.parquet)

paper:
	quarto render $(PAPER)

clean:
	rm -f data/raw/*.parquet data/derived/*.parquet data/figs/*

.PHONY: init extract_factors extract_elasticity extract_seasonality paper clean