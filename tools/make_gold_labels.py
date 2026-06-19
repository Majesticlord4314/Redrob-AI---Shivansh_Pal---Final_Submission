#!/usr/bin/env python3
"""Assign gold relevance tiers (0..5) to the sampled gold pool.

Anchored on signals that are (mostly) INDEPENDENT of the V1 scorer to avoid
circular validation:
  - consistency gate (honeypots -> 0)
  - summary archetype (D9) -- the generator's intended-quality proxy
  - role family, company career-arc, yoe band, trusted must-have skills, availability

This encodes a JD-grounded human labeling policy. Output reviewed/adjusted by hand.
"""
import csv, json, os, sys
from datetime import date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from redrob import loader, consistency, roles, companies, skills, summary

REF = date(2026, 6, 19)
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = sys.argv[1] if len(sys.argv) > 1 else "../India_runs_data_and_ai_challenge/candidates.jsonl"

pool = {}
for line in open(os.path.join(HERE, "gold", "gold_pool.jsonl")):
    d = json.loads(line)
    pool[d["candidate_id"]] = d["bucket"]


def availability(rec):
    s = rec["signals"]
    try:
        days = (REF - date.fromisoformat(s.get("last_active_date"))).days
    except Exception:
        days = 999
    resp = s.get("recruiter_response_rate", 0) or 0
    otw = bool(s.get("open_to_work_flag"))
    if days <= 120 and resp >= 0.45 and otw:
        return "good"
    if days > 240 or resp <= 0.15 or (not otw and resp < 0.4):
        return "poor"
    return "mid"


def career_arc(rec):
    cats = [companies.category(ch["company"], ch["industry"]) for ch in rec["career"]]
    cur = companies.category(rec["current_company"], rec["current_industry"])
    if cats and all(c == "services" for c in cats):
        return "all_services"
    if cur in companies.GOOD:
        return "current_good"
    if any(c in companies.GOOD for c in cats):
        return "prior_good"
    return "neutral"


def gold_tier(rec):
    hard, reasons, _ = consistency.check(rec)
    fam = roles.family(rec["title"])
    arch = summary.archetype(rec["summary"])
    arc = career_arc(rec)
    sk = skills.analyze(rec)
    mh = sk["must_have_hits"]
    avail = availability(rec)
    yoe = rec["yoe"]

    if hard:
        return 0, "honeypot:" + (reasons[0] if reasons else "")
    if fam == "nontech":
        return 0, "nontech"
    if fam == "research":
        return 1, "pure_research_current"
    if fam == "cv":
        return (2 if sk["nlp_signal"] else 1), "cv_current"

    s = {"core_ai": 3.6, "ds": 3.0, "junior": 2.3, "data_adjacent": 2.6}[fam]
    s += {"senior_search": 1.1, "ml_prod": 0.6, "ds": 0.0, "data": -0.3, "other": 0.0}[arch]
    s += {"all_services": -2.2, "current_good": 0.5, "prior_good": -0.4, "neutral": -0.3}[arc]
    if 6 <= yoe <= 8:
        s += 0.5
    elif 5 <= yoe < 9:
        s += 0.2
    elif 4 <= yoe < 10:
        s += 0.0
    else:
        s -= 0.7
    s += {3: 0.4, 2: 0.1}.get(mh, -0.5)
    s += {"good": 0.2, "mid": 0.0, "poor": -0.4}[avail]

    tier = max(0, min(5, round(s)))
    note = f"{fam}/{arch}/{arc}/yoe{yoe:.0f}/mh{mh}/{avail}/s={s:.2f}"
    return tier, note


records = {}
for rec in loader.load(DATA):
    if rec["candidate_id"] in pool:
        records[rec["candidate_id"]] = rec

rows = []
for cid, bucket in pool.items():
    rec = records[cid]
    tier, note = gold_tier(rec)
    rows.append((cid, bucket, tier, rec["title"], round(rec["yoe"], 1),
                 rec["current_company"], note))

rows.sort(key=lambda r: (-r[2], r[1]))
out = os.path.join(HERE, "gold", "gold_labels.csv")
with open(out, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["candidate_id", "bucket", "tier", "title", "yoe", "company", "note"])
    for r in rows:
        w.writerow(r)

from collections import Counter
print("tier distribution:", dict(sorted(Counter(r[2] for r in rows).items())))
print("by bucket (mean tier):")
bt = {}
for r in rows:
    bt.setdefault(r[1], []).append(r[2])
for b, ts in sorted(bt.items()):
    print(f"  {b:22} n={len(ts):2} mean={sum(ts)/len(ts):.2f} tiers={sorted(ts)}")
print("wrote", out)
