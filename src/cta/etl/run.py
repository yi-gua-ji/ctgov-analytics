"""Orchestrate ingest -> validate -> load -> marts -> insights."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from ..config import Config, load_config
from ..http import CtgovClient
from .extract import extract_rows
from .load import connect, execute_script, load_rows, record_run
from .validate import validate_rows

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
MARTS_SQL = ROOT / "sql" / "02_marts.sql"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


async def run_pipeline(
    cfg: Config,
    *,
    queries: list[str] | None = None,
    strict: bool | None = None,
    skip_insights: bool = False,
    client: CtgovClient | None = None,
) -> dict:
    """Run the full pipeline and return a summary dict."""
    queries = queries or cfg.ingest.queries
    strict = cfg.quality.strict if strict is None else strict
    client = client or CtgovClient(cfg)
    started = datetime.now(UTC)
    run_id = started.strftime("%Y%m%dT%H%M%S")

    raw_dir = Path(cfg.paths.raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    all_rows: list[dict] = []
    fetched = 0
    for query in queries:
        logger.info("ingesting query: %s", query)
        studies = []
        async for study in client.iter_studies(
            query, cfg.ingest.max_studies_per_query, cfg.api.page_size, cfg.ingest.fields
        ):
            studies.append(study)
        rows = extract_rows(studies)
        fetched += len(studies)
        raw_path = raw_dir / f"{run_id}_{_slug(query)}.jsonl"
        with raw_path.open("w", encoding="utf-8") as fh:
            for study in studies:
                fh.write(json.dumps({"fetched_at": started.isoformat(), "study": study}) + "\n")
        logger.info("  fetched=%d rows=%d -> %s", len(studies), len(rows), raw_path.name)
        all_rows.extend(rows)

    validation = validate_rows(all_rows)
    reports_dir = Path(cfg.paths.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "quality_report.json").write_text(
        json.dumps(validation, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    logger.info(
        "quality: rows=%d violations=%d critical=%d ok=%s",
        validation["rows"],
        sum(validation["violations_by_rule"].values()),
        validation["critical"],
        validation["ok"],
    )

    con = connect(cfg.paths.db_path)
    upserted = load_rows(con, all_rows)
    execute_script(con, MARTS_SQL.read_text(encoding="utf-8"))
    total_rows = con.execute("SELECT COUNT(*) FROM stg_studies").fetchall()[0][0]
    record_run(con, fetched, upserted, queries, "success" if validation["ok"] else "quality_warnings", started)

    summary = {
        "run_id": run_id,
        "queries": queries,
        "studies_fetched": fetched,
        "rows_upserted": upserted,
        "staging_rows": total_rows,
        "quality_ok": validation["ok"],
        "violations": sum(validation["violations_by_rule"].values()),
        "db_path": cfg.paths.db_path,
    }

    if not skip_insights:
        from ..analytics.insights import generate_insights

        report_path = generate_insights(con, reports_dir)
        summary["insights_path"] = str(report_path)

    if strict and not validation["ok"]:
        logger.error("strict mode: critical quality violations found")
        raise SystemExit(2)
    return summary


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(prog="cta-pipeline", description="ClinicalTrials.gov analytics pipeline")
    parser.add_argument("--config", default=None)
    parser.add_argument("--query", action="append", dest="queries", help="override query (repeatable)")
    parser.add_argument("--max-studies", type=int, default=None)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--skip-insights", action="store_true")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    if args.max_studies:
        cfg.ingest.max_studies_per_query = args.max_studies
    summary = asyncio.run(
        run_pipeline(cfg, queries=args.queries, strict=args.strict or None, skip_insights=args.skip_insights)
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())