# HK Census Trend Report

This project fetches selected historical series from the Hong Kong Census and Statistics Department, computes ten trend views, and writes a local HTML report to `dist/index.html`.

The report is rendered locally with inline SVG charts. It does not depend on a remote charting library at runtime.

## What it covers

- Population level
- Population growth components
- Ageing and dependency
- Fertility pressure
- Household downsizing
- Household income
- Labour force participation
- Unemployment cycle
- Real GDP per capita
- Inflation regime

## Run it

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Build or refresh the report:

```powershell
python build_report.py
```

The generated report includes:

- one primary long-history chart for each section
- supporting mini graphics chosen for that section
- event markers such as the 2000 dot-com bubble, the 2003 SARS outbreak, the 2008 global financial crisis, and the 2020 COVID-19 shock where relevant to the time range

Check whether any configured source tables have newer `last_modified_date` values without rebuilding:

```powershell
python build_report.py --check-only
```

Force a full refresh of cached source files and rebuild:

```powershell
python build_report.py --force-refresh
```

## Update behavior

- Raw C&SD metadata and CSV files are cached under `data/raw/`.
- The last-seen source dates are recorded in `data/metadata.json`.
- Each run checks the configured tables for a newer official `last_modified_date`.
- If a table changed, the script refreshes the cache and rewrites `dist/index.html`.

## Periodic local checks

On Windows, schedule the report with Task Scheduler and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -Command "cd C:\github\HKCensus; python build_report.py"
```

That gives you a local periodic check plus automatic incorporation of newly published values in the configured source set.
