"""Scraper: fetch LOTO6 history from mk-mode.com CSV (single source)."""

import logging
import httpx
import csv
import io
from typing import List, Dict

log = logging.getLogger("loto6")

CSV_URL = "https://www.mk-mode.com/rails/loto/LOTO6_ALL.csv"
TIMEOUT = 30


def fetch_csv() -> List[Dict]:
    """Download full LOTO6 CSV from mk-mode.com and parse rows."""
    resp = httpx.get(CSV_URL, timeout=TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    text = resp.text
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header:
        log.warning("CSV header is empty")
        return []

    rows = []
    for line in reader:
        if len(line) < 9:
            continue
        try:
            rnd = int(line[0])
            date_str = line[1].strip()
            nums = [int(line[i]) for i in range(2, 8)]
            bonus = int(line[8])
            nums_sorted = sorted(nums)
            rows.append({
                "round": rnd,
                "date": date_str,
                "n1": nums_sorted[0],
                "n2": nums_sorted[1],
                "n3": nums_sorted[2],
                "n4": nums_sorted[3],
                "n5": nums_sorted[4],
                "n6": nums_sorted[5],
                "bonus": bonus,
            })
        except (ValueError, IndexError) as e:
            log.debug("skip row: %s (%s)", line, e)
            continue
    return rows


def fetch_all() -> tuple:
    """Fetch all draw data. Returns (rows, source_name)."""
    try:
        rows = fetch_csv()
        log.info("scrape OK: source=mk-mode-csv fetched=%d", len(rows))
        return rows, "mk-mode-csv"
    except Exception as e:
        log.error("scrape FAILED: %s", e)
        return [], "error"
