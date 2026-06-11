"""
Accuracy dashboard for developers.

Run from backend/:
    uv run streamlit run evals/dashboard.py

Reads eval_runs / eval_results from the app database (Supabase Postgres).
"""

from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env", override=False)

import pandas as pd
import plotly.express as px
import streamlit as st

from app.database import engine

st.set_page_config(page_title="ShipHappens — AI Accuracy", layout="wide")


@st.cache_data(ttl=30)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    runs = pd.read_sql("SELECT * FROM eval_runs ORDER BY created_at DESC", engine)
    results = pd.read_sql("SELECT * FROM eval_results", engine)
    return runs, results


runs, results = load_data()

st.title("AI Accuracy Dashboard")

if runs.empty:
    st.info("No eval runs yet. Run `uv run python -m evals.run` from backend/ first.")
    st.stop()

results = results.merge(
    runs[["id", "created_at", "git_sha", "offline"]],
    left_on="run_id", right_on="id", suffixes=("", "_run"),
)
results["run_label"] = (
    results["created_at"].dt.strftime("%m-%d %H:%M") + " (" + results["git_sha"] + ")"
)

page = st.sidebar.radio("Page", ["Overview", "Failures", "Cost"])
st.sidebar.markdown("---")
st.sidebar.caption(f"{len(runs)} runs · {len(results)} results")

if page == "Overview":
    st.subheader("Pass rate per surface, per run")
    gated = results[results["passed"].notna()].copy()
    if gated.empty:
        st.info("No pass/fail checks recorded yet.")
    else:
        gated["passed"] = gated["passed"].astype(bool)
        agg = (
            gated.groupby(["run_label", "created_at", "surface"])["passed"]
            .agg(pass_rate="mean", checks="count")
            .reset_index()
            .sort_values("created_at")
        )
        fig = px.line(
            agg, x="run_label", y="pass_rate", color="surface",
            markers=True, hover_data=["checks"], range_y=[0, 1.05],
        )
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Latest run breakdown")
        latest_run_id = runs.iloc[0]["id"]
        latest = gated[gated["run_id"] == latest_run_id]
        cols = st.columns(max(len(latest["surface"].unique()), 1))
        for col, (surface, grp) in zip(cols, latest.groupby("surface")):
            col.metric(
                surface,
                f"{grp['passed'].mean():.0%}",
                f"{int(grp['passed'].sum())}/{len(grp)} checks",
            )

    st.subheader("Key drift metrics over time")
    drift = results[results["metric"] == "total_marks_drift_pct"]
    if not drift.empty:
        fig2 = px.line(
            drift.sort_values("created_at"),
            x="run_label", y="value", color="case_id", markers=True,
            labels={"value": "total marks drift %"},
        )
        fig2.add_hline(y=10, line_dash="dash", line_color="red")
        st.plotly_chart(fig2, use_container_width=True)

elif page == "Failures":
    run_label = st.selectbox("Run", results["run_label"].unique())
    subset = results[(results["run_label"] == run_label) & (results["passed"] == False)]  # noqa: E712
    st.subheader(f"{len(subset)} failed check(s)")
    if subset.empty:
        st.success("No failures in this run.")
    for _, row in subset.iterrows():
        with st.expander(f"{row['surface']} / {row['case_id']} :: {row['metric']} = {row['value']:.3f}"):
            st.json(row["detail"])

elif page == "Cost":
    st.subheader("Token spend per run")
    cost = (
        results.groupby(["run_label", "created_at", "surface"])
        .agg(tokens=("tokens_in", "sum"), tokens_out=("tokens_out", "sum"),
             cost_usd=("cost_usd", "sum"))
        .reset_index()
        .sort_values("created_at")
    )
    cost["tokens_total"] = cost["tokens"] + cost["tokens_out"]
    fig = px.bar(cost, x="run_label", y="cost_usd", color="surface")
    st.plotly_chart(fig, use_container_width=True)

    total_cost = results["cost_usd"].sum()
    total_tokens = (results["tokens_in"] + results["tokens_out"]).sum()
    c1, c2 = st.columns(2)
    c1.metric("All-time eval cost", f"${total_cost:.4f}")
    c2.metric("All-time eval tokens", f"{int(total_tokens):,}")
    st.dataframe(cost, use_container_width=True)
