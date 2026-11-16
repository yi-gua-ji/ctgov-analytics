"""Streamlit dashboard over the cardimetabolic trials warehouse.

Run: streamlit run src/cta/dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cta.analytics import metrics
from cta.config import load_config

st.set_page_config(page_title="Cardiometabolic trials", layout="wide")
st.title("ClinicalTrials.gov cardiometabolic trials")

cfg = load_config()
db_path = Path(cfg.paths.db_path)
if not db_path.exists():
    st.warning("Warehouse not found. Run: python scripts/run_pipeline.py")
    st.stop()

con = duckdb.connect(str(db_path), read_only=True)
overview = metrics.overview(con)

k1, k2, k3, k4 = st.columns(4)
k1.metric("Trials", f"{int(overview['n_trials']):,}")
k2.metric("Median enrollment", overview["median_enrollment"])
k3.metric("Completed share", overview["completion_rate"])
k4.metric("Stopped share", overview["stopped_rate"])

df = con.execute("SELECT * FROM v_trials").df()
universe = df.dropna(subset=["start_year"])
if universe.empty:
    st.warning("No trials with a start date yet.")
    st.stop()

year_min, year_max = int(universe["start_year"].min()), int(universe["start_year"].max())
phases = sorted([p for p in df["phase_category"].dropna().unique()])
sponsors = sorted([s for s in df["sponsor_class"].dropna().unique()])

year_range = st.slider("Start year", year_min, year_max, (year_min, year_max))
phase_filter = st.multiselect("Phase", phases, default=phases)
sponsor_filter = st.multiselect("Sponsor class", sponsors, default=sponsors)
search = st.text_input("Search title / condition")

mask = (
    (df["start_year"] >= year_range[0])
    & (df["start_year"] <= year_range[1])
    & (df["phase_category"].isin(phase_filter))
    & (df["sponsor_class"].isin(sponsor_filter))
)
if search:
    text = search.lower()
    mask &= df["title"].fillna("").str.lower().str.contains(text) | df["conditions"].fillna("").str.lower().str.contains(text)
filtered = df[mask]

st.caption(f"{len(filtered):,} trials match the filters")

by_year = filtered.groupby("start_year").size().rename("n_trials")
st.subheader("Trials per start year")
st.bar_chart(by_year)

c1, c2 = st.columns(2)
with c1:
    st.subheader("Phase distribution")
    st.bar_chart(filtered.groupby("phase_category").size())
with c2:
    st.subheader("Status distribution")
    st.bar_chart(filtered.groupby("status").size())

st.subheader("Enrollment by phase")
st.bar_chart(filtered.groupby("phase_category")["enrollment_count"].median())

st.subheader("Completion by sponsor class")
sponsor_table = filtered.groupby("sponsor_class").agg(
    n_trials=("nct_id", "count"),
    completion_rate=("is_completed", "mean"),
    stopped_rate=("is_stopped", "mean"),
).reset_index()
st.dataframe(sponsor_table, use_container_width=True)

st.subheader("Top conditions")
st.dataframe(filtered["conditions"].value_counts().head(15).rename_axis("conditions").reset_index(name="n_trials"), use_container_width=True)