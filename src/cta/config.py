"""Configuration loading for the ClinicalTrials.gov analytics pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ApiConfig:
    base_url: str = "https://clinicaltrials.gov/api/v2"
    page_size: int = 1000
    timeout: float = 60.0
    rate_limit_per_sec: float = 3.0
    max_retries: int = 4


@dataclass
class IngestConfig:
    queries: list[str] = field(default_factory=list)
    max_studies_per_query: int = 1200
    fields: list[str] = field(default_factory=list)


@dataclass
class PathsConfig:
    raw_dir: str = "data/raw"
    db_path: str = "data/ctgov.duckdb"
    reports_dir: str = "reports"


@dataclass
class QualityConfig:
    strict: bool = False


@dataclass
class Config:
    api: ApiConfig = field(default_factory=ApiConfig)
    ingest: IngestConfig = field(default_factory=IngestConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    quality: QualityConfig = field(default_factory=QualityConfig)
    root_dir: Path = field(default_factory=lambda: Path.cwd())


def _build(cls, data: dict[str, Any]):
    known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    return cls(**{k: v for k, v in (data or {}).items() if k in known})


def load_config(path: str | None = None) -> Config:
    """Load YAML config and resolve relative paths against the project root."""
    config_path = path or os.environ.get("CTA_CONFIG") or "config/default.yaml"
    p = Path(config_path)
    if not p.is_absolute():
        p = Path.cwd() / p
    raw: dict[str, Any] = {}
    if p.exists():
        with p.open("r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    cfg = Config(
        api=_build(ApiConfig, raw.get("api")),
        ingest=_build(IngestConfig, raw.get("ingest")),
        paths=_build(PathsConfig, raw.get("paths")),
        quality=_build(QualityConfig, raw.get("quality")),
        root_dir=Path.cwd(),
    )
    for attr in ("raw_dir", "db_path", "reports_dir"):
        value = Path(getattr(cfg.paths, attr))
        if not value.is_absolute():
            setattr(cfg.paths, attr, str(Path.cwd() / value))
    return cfg