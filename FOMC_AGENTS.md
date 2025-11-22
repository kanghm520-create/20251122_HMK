# FOMC Data Collection Prompt Guide

This guide defines a clear prompt for collecting FOMC Statement and Projection Materials PDFs from the Federal Reserve website for the last 10 years.

## Scope
- Source: Federal Reserve monetary policy page (`https://www.federalreserve.gov/monetarypolicy`).
- Documents: FOMC Statement PDFs and Projection Materials PDFs.
- Period: Most recent 10 years of available meetings.
- Storage: Save downloaded PDFs to a convenient local folder (e.g., `data/fomc_statements/<year>/`).

## Recommended Prompt
Use the following prompt (edit the save path as needed) when directing an agent to gather the files:

```
Collect all FOMC Statement PDFs and FOMC Projection Materials PDFs from the Federal Reserve monetary policy site (https://www.federalreserve.gov/monetarypolicy) for the most recent 10 years of FOMC meetings.

Requirements:
- Capture every meeting within the 10-year window.
- Prefer the PDF links labeled "Statement" and "Projection Materials" (or similar) on each meeting page.
- Save each PDF using the pattern `<YYYY-MM-DD>_<meeting-label>_statement.pdf` and `<YYYY-MM-DD>_<meeting-label>_projections.pdf` into a local folder like `data/fomc_statements/<year>/`.
- If a projection PDF is not available for a meeting, note that in a log file (e.g., `data/fomc_statements/missing_projections.txt`).
- Verify downloads by opening each PDF and confirming it is not an HTML error page.
- Do not scrape or rely on non-Fed sources.
```

## Logging
- Keep a simple log (text or CSV) listing meeting date, statement file path, projection file path (or "missing"), and source URL.
- Include timestamps for when downloads were performed.

## Validation Checklist
- All meetings within the last 10 years are represented.
- Filenames follow the specified pattern.
- Every saved file is a PDF and opens correctly.
- Missing projection materials are documented in the log.
