# FOMC Statement Collector

This project fetches Federal Reserve FOMC statement PDFs and projection materials for the most recent 10 years, storing them in a structured folder layout and exposing a small FastAPI server that groups files by year and meeting date.

## Features
- Scrapes the official FOMC calendar (`https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm`).
- Downloads statement and projection PDFs with consistent filenames.
- Logs missing projection materials.
- Serves grouped metadata via JSON endpoints.

## Setup
Install the Python dependencies:

```bash
pip install -r requirements.txt
```

## Collecting statements
Run the collector to parse the FOMC calendar. Include `--download` to fetch PDFs (metadata-only mode skips downloads but still writes the log headers).

```bash
python -m fomc.collector --years 10 --download
```

Downloaded files and logs are stored under `data/fomc_statements/` by default:
- `download_log.csv` — timestamped entries for each meeting.
- `missing_projections.txt` — list of meetings without projection materials.

## Running the API server
After collecting data, start the FastAPI app (defaults to port 8000):

```bash
python -m uvicorn fomc.server:app --host 0.0.0.0 --port 8000
```

> **Note:** If the `uvicorn` command is not found, using `python -m uvicorn ...` ensures
> the module is executed from the same Python environment where dependencies were
> installed (including Codespaces, which installs packages into `~/.local`).

Available endpoints:
- `GET /` — Service metadata.
- `GET /years` — Available meeting years.
- `GET /statements` — Statements grouped by year.
- `GET /statements/{year}` — Statements for a specific year.
