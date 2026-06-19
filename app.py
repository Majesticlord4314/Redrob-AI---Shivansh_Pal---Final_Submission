"""Hosted sandbox for the Redrob ranker (Stage-3 sanity check).

Accepts a small candidate sample (<=100) as JSONL — uploaded or the bundled
example — runs the full ranking pipeline end-to-end on CPU and shows the ranked
table with reasoning. Deploy on HuggingFace Spaces / Streamlit Cloud.

Run locally:  streamlit run app.py
Deps:         pip install -r requirements-sandbox.txt
"""
import io
import json
import os
import tempfile

import streamlit as st

from redrob import loader, consistency, scoring, behavioral, reasoning

st.set_page_config(page_title="Redrob Ranker — Sandbox", layout="wide")
st.title("Redrob Candidate Ranker — Sandbox")
st.caption("Rule-based, consistency-gated ranker. Pure stdlib, CPU-only, no network. "
           "Upload up to 100 candidates (JSONL) or use the bundled sample.")

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "sample_candidates_100.jsonl")

src = st.radio("Input", ["Bundled 100-candidate sample", "Upload JSONL"], horizontal=True)
path = SAMPLE
if src == "Upload JSONL":
    up = st.file_uploader("candidates.jsonl (one JSON object per line, <=100)", type=["jsonl", "json"])
    if up is not None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl", mode="wb")
        tmp.write(up.read()); tmp.close()
        path = tmp.name
    else:
        st.stop()

rows = []
n = hard = 0
for rec in loader.load(path):
    n += 1
    hd, _, soft = consistency.check(rec)
    if hd:
        hard += 1
    sc = scoring.score(rec, hd, soft)
    if sc["fit"] <= 0:
        continue
    m, _ = behavioral.modifier(rec)
    rec_min = {
        "candidate_id": rec["candidate_id"], "title": rec["title"], "yoe": rec["yoe"],
        "current_company": rec["current_company"], "current_industry": rec["current_industry"],
        "signals": {k: rec["signals"].get(k) for k in
                    ("recruiter_response_rate", "last_active_date", "open_to_work_flag", "notice_period_days")},
    }
    rows.append((sc["fit"] * m, rec_min, sc))

rows.sort(key=lambda x: (-x[0], x[1]["candidate_id"]))
top = rows[:100]

st.success(f"Ranked {n} candidates · {hard} hard-rejected (honeypot/impossible) · showing top {len(top)}")

table = []
for i, (score, rec_min, sc) in enumerate(top):
    table.append({
        "rank": i + 1,
        "candidate_id": rec_min["candidate_id"],
        "score": round(score, 4),
        "title": rec_min["title"],
        "yoe": rec_min["yoe"],
        "company": rec_min["current_company"],
        "archetype": sc["archetype"],
        "must_have": sc["must_have_hits"],
        "reasoning": reasoning.generate(rec_min, sc, i + 1),
    })
st.dataframe(table, use_container_width=True, hide_index=True)

csv_lines = ["candidate_id,rank,score,reasoning"]
import csv as _csv
buf = io.StringIO()
w = _csv.writer(buf)
w.writerow(["candidate_id", "rank", "score", "reasoning"])
for r in table:
    w.writerow([r["candidate_id"], r["rank"], f"{r['score']:.6f}", r["reasoning"]])
st.download_button("Download ranked CSV", buf.getvalue(), file_name="submission.csv", mime="text/csv")
