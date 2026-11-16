"""Rebuild the SQL marts and the insights report from the existing warehouse.

Useful after changing metric SQL or the analytics code: no API refetch needed.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cta.analytics.insights import generate_insights
from cta.config import load_config
from cta.etl.load import connect, execute_script


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    cfg = load_config()
    con = connect(cfg.paths.db_path)
    execute_script(con, (root / "sql" / "02_marts.sql").read_text(encoding="utf-8"))
    docs_path = generate_insights(con, root / "docs")
    reports_path = generate_insights(con, cfg.paths.reports_dir)
    if docs_path.resolve() != reports_path.resolve():
        shutil.copyfile(reports_path, docs_path)
    print(f"insights: {docs_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())