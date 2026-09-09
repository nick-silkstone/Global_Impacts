#!/usr/bin/env python3
"""
merge_impacts.py

Deterministic housekeeping for latest_impacts.csv. Takes the LLM-produced
candidate_impacts.csv from the nightly trawl and:

  1. Archives the current latest_impacts.csv (if it holds data) as
     YYYY_MM_DD_impacts.csv, dated the day before this run — i.e. the last
     day it was an accurate "latest" snapshot.
  2. Merges candidate rows into it: matches on impact_id for revisions,
     inserts new rows otherwise. If a candidate's impact_id collides with
     an existing row that is clearly a *different* event (event_id or
     parent_event_name don't match), treats it as an ID collision rather
     than blindly overwriting — reassigns a fresh id and logs a warning,
     rather than corrupting an unrelated row.
  3. Prunes any row whose date_occurred is more than PRUNE_DAYS old.
  4. Writes the result back to latest_impacts.csv, sorted by date_occurred
     (newest first).

Deliberately does no LLM-style judgement calls — every decision here is a
fixed rule, by design (see severity_classification_addendum.md for why).

Usage:
    python merge_impacts.py \\
        --latest latest_impacts.csv \\
        --candidate candidate_impacts.csv \\
        --archive-dir . \\
        [--run-date YYYY-MM-DD] [--prune-days 10]

Exit code 0 on success (including "nothing to merge"), non-zero on a
fatal error (missing files, unreadable CSV) so the Action step fails
visibly rather than silently doing nothing.
"""

import argparse
import csv
import shutil
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

SCHEMA_COLUMNS = [
    "impact_id", "event_id", "parent_event_name", "hazard_category",
    "hazard_type", "country", "iso3c", "locality", "lat", "lon",
    "geolocation_confidence", "date_occurred", "date_logged",
    "date_last_updated", "severity_level", "severity_confidence",
    "casualties", "displaced", "support_required", "recovery_time_estimate",
    "cost_pct_gdp", "severity_rationale", "description",
    "source_1_url", "source_2_url", "source_3_url",
]


def log(msg: str) -> None:
    print(f"[merge_impacts] {msg}")


def parse_date(value: str, field_name: str, row_id: str = "?") -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError:
        log(f"WARNING: row {row_id} has unparseable {field_name}={value!r}; "
            f"treating as unknown (row will be kept, not pruned).")
        return None


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return []
        missing = set(SCHEMA_COLUMNS) - set(reader.fieldnames)
        extra = set(reader.fieldnames) - set(SCHEMA_COLUMNS)
        if missing:
            log(f"WARNING: {path.name} is missing expected columns: "
                f"{sorted(missing)} — those fields will read as blank.")
        if extra:
            log(f"WARNING: {path.name} has unexpected extra columns: "
                f"{sorted(extra)} — they will be ignored.")
        rows = []
        for row in reader:
            # Normalise: ensure every schema column exists, drop unknowns.
            clean = {col: (row.get(col) or "").strip() for col in SCHEMA_COLUMNS}
            rows.append(clean)
        return rows


def write_rows(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in SCHEMA_COLUMNS})


def archive_previous(latest_path: Path, archive_dir: Path, run_date: date) -> None:
    existing = read_rows(latest_path)
    if not existing:
        log("No existing latest_impacts.csv data to archive (empty or absent).")
        return
    archive_date = run_date - timedelta(days=1)
    archive_path = archive_dir / f"{archive_date:%Y_%m_%d}_impacts.csv"
    if archive_path.exists():
        log(f"Archive {archive_path.name} already exists — skipping "
            f"(assuming this run already archived today; not overwriting).")
        return
    shutil.copy2(latest_path, archive_path)
    log(f"Archived {len(existing)} rows to {archive_path.name}")


def is_same_event(a: dict, b: dict) -> bool:
    """Heuristic for 'is this genuinely a revision of the same event row'."""
    if a.get("event_id") and b.get("event_id"):
        return a["event_id"] == b["event_id"]
    # Fall back to name match if event_id is missing on either side.
    return (a.get("parent_event_name", "").strip().lower()
            == b.get("parent_event_name", "").strip().lower())


def unique_id(base_id: str, taken: set[str]) -> str:
    if base_id not in taken:
        return base_id
    suffix = ord("b")
    while f"{base_id}-{chr(suffix)}" in taken:
        suffix += 1
    return f"{base_id}-{chr(suffix)}"


def merge(existing: list[dict], candidates: list[dict], run_date: date) -> tuple[list[dict], dict]:
    by_id = {row["impact_id"]: row for row in existing if row.get("impact_id")}
    taken_ids = set(by_id.keys())
    stats = {"updated": 0, "inserted": 0, "id_collisions": 0}

    for cand in candidates:
        cid = cand.get("impact_id", "").strip()
        if not cid:
            log("WARNING: candidate row with no impact_id skipped entirely — "
                f"parent_event_name={cand.get('parent_event_name')!r}")
            continue

        if cid in by_id and is_same_event(cand, by_id[cid]):
            # Genuine revision: keep original date_logged, update the rest.
            original_logged = by_id[cid].get("date_logged") or cand.get("date_logged")
            updated = {**by_id[cid], **cand}
            updated["date_logged"] = original_logged
            updated["date_last_updated"] = cand.get("date_last_updated") or f"{run_date:%Y-%m-%d}"
            by_id[cid] = updated
            stats["updated"] += 1
        else:
            if cid in by_id:
                stats["id_collisions"] += 1
                new_id = unique_id(cid, taken_ids)
                log(f"WARNING: impact_id {cid} collides with an unrelated "
                    f"existing row — reassigned candidate to {new_id}.")
                cand["impact_id"] = new_id
                cid = new_id
            cand.setdefault("date_logged", f"{run_date:%Y-%m-%d}")
            cand["date_last_updated"] = cand.get("date_last_updated") or cand["date_logged"]
            by_id[cid] = cand
            taken_ids.add(cid)
            stats["inserted"] += 1

    return list(by_id.values()), stats


def prune(rows: list[dict], run_date: date, prune_days: int) -> tuple[list[dict], int]:
    cutoff = run_date - timedelta(days=prune_days)
    kept, removed = [], 0
    for row in rows:
        occurred = parse_date(row.get("date_occurred", ""), "date_occurred", row.get("impact_id", "?"))
        if occurred is None or occurred >= cutoff:
            kept.append(row)
        else:
            removed += 1
    return kept, removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latest", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--archive-dir", required=True, type=Path)
    parser.add_argument("--run-date", type=str, default=None,
                         help="YYYY-MM-DD; defaults to today (UTC).")
    parser.add_argument("--prune-days", type=int, default=10)
    args = parser.parse_args()

    run_date = (datetime.strptime(args.run_date, "%Y-%m-%d").date()
                if args.run_date else datetime.utcnow().date())

    if not args.candidate.exists():
        log(f"FATAL: candidate file {args.candidate} not found.")
        return 1

    args.archive_dir.mkdir(parents=True, exist_ok=True)
    archive_previous(args.latest, args.archive_dir, run_date)

    existing = read_rows(args.latest)
    candidates = read_rows(args.candidate)
    log(f"Loaded {len(existing)} existing rows, {len(candidates)} candidate rows.")

    merged, merge_stats = merge(existing, candidates, run_date)
    final_rows, pruned_count = prune(merged, run_date, args.prune_days)

    final_rows.sort(key=lambda r: r.get("date_occurred", ""), reverse=True)
    write_rows(args.latest, final_rows)

    log(f"Done. Inserted {merge_stats['inserted']}, updated "
        f"{merge_stats['updated']}, id_collisions {merge_stats['id_collisions']}, "
        f"pruned {pruned_count} (older than {args.prune_days} days). "
        f"latest_impacts.csv now has {len(final_rows)} rows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
