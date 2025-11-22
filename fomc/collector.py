from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re
from typing import Iterable, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

CALENDAR_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
DATE_RANGE_YEARS = 10


@dataclass
class MeetingDocuments:
    meeting_date: date
    label: str
    statement_url: Optional[str]
    projection_url: Optional[str]
    source_url: str

    @property
    def meeting_year(self) -> int:
        return self.meeting_date.year

    def filename_stub(self) -> str:
        label_part = re.sub(r"[^a-z0-9-]", "", self.label.lower().replace(" ", "-")) or "fomc"
        return f"{self.meeting_date.isoformat()}_{label_part}"


class DownloadLogger:
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.log_path = base_dir / "download_log.csv"
        self.missing_projection_path = base_dir / "missing_projections.txt"
        self._ensure_headers()

    def _ensure_headers(self) -> None:
        if not self.log_path.exists():
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("w", newline="", encoding="utf-8") as fp:
                writer = csv.writer(fp)
                writer.writerow(
                    [
                        "timestamp",
                        "meeting_date",
                        "meeting_label",
                        "statement_path",
                        "projection_path",
                        "source_url",
                    ]
                )

    def record(self, meeting: MeetingDocuments, statement_path: Optional[Path], projection_path: Optional[Path]) -> None:
        with self.log_path.open("a", newline="", encoding="utf-8") as fp:
            writer = csv.writer(fp)
            writer.writerow(
                [
                    datetime.utcnow().isoformat(),
                    meeting.meeting_date.isoformat(),
                    meeting.label,
                    statement_path.as_posix() if statement_path else "missing",
                    projection_path.as_posix() if projection_path else "missing",
                    meeting.source_url,
                ]
            )
        if projection_path is None:
            with self.missing_projection_path.open("a", encoding="utf-8") as fp:
                fp.write(f"{meeting.meeting_date.isoformat()} {meeting.label}: missing projection materials\n")


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_year_from_text(text: str) -> Optional[int]:
    match = re.search(r"(20\d{2})", text)
    if match:
        return int(match.group(1))
    return None


def _find_year_for_row(row: BeautifulSoup) -> Optional[int]:
    for ancestor in row.parents:
        candidate_sources = []
        for attr in ("id", "data-year", "aria-labelledby"):
            value = ancestor.get(attr)
            if isinstance(value, str):
                candidate_sources.append(value)
        candidate_sources.append(ancestor.get_text(" ", strip=True))
        for source in candidate_sources:
            year = _extract_year_from_text(source)
            if year:
                return year
    return None


def _find_context_label(row: BeautifulSoup) -> Optional[str]:
    heading = row.find_previous(["h2", "h3", "h4", "h5"])
    if heading:
        text = _normalize_whitespace(heading.get_text())
        if text:
            return text
    return None


def _parse_meeting_date(raw_text: str, year: int) -> date:
    cleaned = _normalize_whitespace(raw_text)
    cleaned = cleaned.split(":")[0]
    cleaned = cleaned.replace("\u2013", "-").replace("\u2014", "-")
    cleaned = cleaned.replace(",", "")
    month_match = re.match(r"([A-Za-z]+)\s+([0-9]{1,2})(?:[-–][0-9]{1,2})?", cleaned)
    if not month_match:
        raise ValueError(f"Could not parse meeting date from '{raw_text}'")
    month_name, day_part = month_match.group(1), month_match.group(2)
    parsed = datetime.strptime(f"{month_name} {day_part} {year}", "%B %d %Y").date()
    return parsed


def _extract_links(cell: BeautifulSoup) -> tuple[Optional[str], Optional[str]]:
    statement_url: Optional[str] = None
    projection_url: Optional[str] = None
    for link in cell.find_all("a"):
        text = link.get_text(strip=True).lower()
        href = link.get("href")
        if not href:
            continue
        href = urljoin(CALENDAR_URL, href)
        if "statement" in text:
            statement_url = href
        if "projection" in text:
            projection_url = href
    return statement_url, projection_url


def parse_calendar(html: str, max_years: int = DATE_RANGE_YEARS) -> List[MeetingDocuments]:
    soup = BeautifulSoup(html, "html.parser")
    current_year = date.today().year
    min_year = current_year - max_years + 1
    meetings: List[MeetingDocuments] = []

    for row in soup.find_all("tr"):
        date_cell = row.find("th")
        link_cell = row.find("td")
        if date_cell is None or link_cell is None:
            continue
        year = _find_year_for_row(row)
        if year is None or year < min_year:
            continue
        date_text = _normalize_whitespace(date_cell.get_text())
        try:
            meeting_date = _parse_meeting_date(date_text, year)
        except ValueError:
            continue
        statement_url, projection_url = _extract_links(link_cell)
        label = _find_context_label(row) or f"FOMC {year}"
        description = _normalize_whitespace(link_cell.get_text())
        if description:
            label = description
        meetings.append(
            MeetingDocuments(
                meeting_date=meeting_date,
                label=label,
                statement_url=statement_url,
                projection_url=projection_url,
                source_url=CALENDAR_URL,
            )
        )
    meetings.sort(key=lambda m: m.meeting_date)
    return meetings


def _download_file(url: str, destination: Path) -> Optional[Path]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
    except requests.RequestException:
        return None
    content_type = response.headers.get("Content-Type", "")
    if "pdf" not in content_type.lower():
        return None
    with destination.open("wb") as fp:
        fp.write(response.content)
    return destination


def download_documents(meetings: Iterable[MeetingDocuments], base_dir: Path) -> List[MeetingDocuments]:
    logger = DownloadLogger(base_dir)
    successful: List[MeetingDocuments] = []
    for meeting in meetings:
        year_dir = base_dir / str(meeting.meeting_year)
        stub = meeting.filename_stub()
        statement_path: Optional[Path] = None
        projection_path: Optional[Path] = None
        if meeting.statement_url:
            statement_path = _download_file(meeting.statement_url, year_dir / f"{stub}_statement.pdf")
        if meeting.projection_url:
            projection_path = _download_file(meeting.projection_url, year_dir / f"{stub}_projections.pdf")
        logger.record(meeting, statement_path, projection_path)
        successful.append(meeting)
    return successful


def collect(base_dir: Path, years: int = DATE_RANGE_YEARS) -> List[MeetingDocuments]:
    try:
        response = requests.get(CALENDAR_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(f"Failed to download FOMC calendar page: {exc}")
    meetings = parse_calendar(response.text, max_years=years)
    return download_documents(meetings, base_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect FOMC statements and projection materials.")
    parser.add_argument("--base-dir", type=Path, default=Path("data/fomc_statements"), help="Directory to store PDFs and logs.")
    parser.add_argument("--years", type=int, default=DATE_RANGE_YEARS, help="Number of recent years to include (default: 10).")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download PDFs after parsing metadata. If omitted, only metadata is parsed and logged.",
    )
    args = parser.parse_args()

    try:
        response = requests.get(CALENDAR_URL, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise SystemExit(f"Failed to download FOMC calendar page: {exc}")

    meetings = parse_calendar(response.text, max_years=args.years)
    print(f"Found {len(meetings)} meetings in the last {args.years} years.")

    if args.download:
        completed = download_documents(meetings, args.base_dir)
        print(f"Downloaded entries for {len(completed)} meetings. Logs stored in {args.base_dir}.")
    else:
        print("Download flag not set; metadata collection only. Use --download to fetch PDFs.")


if __name__ == "__main__":
    main()
