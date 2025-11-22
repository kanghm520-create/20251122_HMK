from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

LOG_PATH = Path("data/fomc_statements/download_log.csv")


class MeetingEntry(BaseModel):
    meeting_date: str
    meeting_label: str
    statement_path: str
    projection_path: str
    source_url: str


def _load_entries(log_path: Path = LOG_PATH) -> List[MeetingEntry]:
    if not log_path.exists():
        return []
    entries: List[MeetingEntry] = []
    with log_path.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            entries.append(
                MeetingEntry(
                    meeting_date=row["meeting_date"],
                    meeting_label=row["meeting_label"],
                    statement_path=row["statement_path"],
                    projection_path=row["projection_path"],
                    source_url=row["source_url"],
                )
            )
    return entries


def _group_by_year(entries: List[MeetingEntry]) -> Dict[str, List[MeetingEntry]]:
    grouped: Dict[str, List[MeetingEntry]] = {}
    for entry in entries:
        year = entry.meeting_date.split("-")[0]
        grouped.setdefault(year, []).append(entry)
    for values in grouped.values():
        values.sort(key=lambda item: item.meeting_date)
    return dict(sorted(grouped.items(), key=lambda kv: kv[0], reverse=True))


app = FastAPI(title="FOMC Statements API", description="Serve FOMC statements grouped by year and date.")


@app.get("/")
def root() -> dict:
    return {
        "message": "FOMC Statements API",
        "endpoints": ["/statements", "/statements/{year}", "/years"],
    }


@app.get("/years")
def list_years() -> List[str]:
    entries = _load_entries()
    grouped = _group_by_year(entries)
    return list(grouped.keys())


@app.get("/statements")
def all_statements() -> Dict[str, List[MeetingEntry]]:
    entries = _load_entries()
    grouped = _group_by_year(entries)
    return grouped


@app.get("/statements/{year}")
def statements_by_year(year: str) -> List[MeetingEntry]:
    entries = _load_entries()
    grouped = _group_by_year(entries)
    if year not in grouped:
        raise HTTPException(status_code=404, detail=f"No statements found for {year}")
    return grouped[year]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
