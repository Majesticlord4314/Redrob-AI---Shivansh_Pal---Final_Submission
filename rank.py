#!/usr/bin/env python3
"""Redrob candidate ranker — V1.

Usage:
    python rank.py --candidates ../India_runs_data_and_ai_challenge/candidates.jsonl --out submission.csv

Produces the top-100 submission CSV. Also writes <out>.debug.csv with the
feature breakdown for analysis. No reasoning generation in V1 (column left blank).
"""
import argparse
import csv
import time

from redrob import loader, consistency, scoring, behavioral, reasoning


def run(path, out):
    t0 = time.time()
    scored = []
    n = 0
    hard_rejects = 0
    for rec in loader.load(path):
        n += 1
        hard, reasons, soft = consistency.check(rec)
        if hard:
            hard_rejects += 1
        sc = scoring.score(rec, hard, soft)
        if sc["fit"] <= 0.0:
            continue  # never rank honeypots / irrelevant
        m, notes = behavioral.modifier(rec)
        final = sc["fit"] * m
        rec_min = {
            "candidate_id": rec["candidate_id"],
            "title": rec["title"],
            "yoe": rec["yoe"],
            "current_company": rec["current_company"],
            "current_industry": rec["current_industry"],
            "signals": {k: rec["signals"].get(k) for k in
                        ("recruiter_response_rate", "last_active_date",
                         "open_to_work_flag", "notice_period_days")},
        }
        scored.append({
            "candidate_id": rec["candidate_id"],
            "final": final,
            "fit": sc["fit"],
            "m": m,
            "rec_min": rec_min,
            "sc": sc,
            "title": rec["title"],
            "family": sc["family"],
            "archetype": sc["archetype"],
            "yoe": rec["yoe"],
            "company": rec["current_company"],
            "industry": rec["current_industry"],
            "location": rec["location"],
            "country": rec["country"],
            "domains": ",".join(sc["trusted_domains"]),
            "must_have": sc["must_have_hits"],
            "n_ai_raw": sc["n_ai_skills_raw"],
            "g_role": sc["g_role"], "g_arch": sc["g_arch"], "g_dom": sc["g_dom"],
            "g_comp": sc["g_comp"], "g_yoe": sc["g_yoe"], "g_loc": sc["g_loc"],
            "penalties": "|".join(sc["penalties"]),
            "notes": "|".join(notes),
            "hard_reasons": "|".join(reasons),
        })

    # rank: final desc, tie-break candidate_id asc
    scored.sort(key=lambda x: (-x["final"], x["candidate_id"]))
    top = scored[:100]

    # enforce strictly-decreasing scores for the validator
    eps = 1e-6
    prev = None
    for i, row in enumerate(top):
        s = round(row["final"], 6)
        if prev is not None and s >= prev:
            s = round(prev - eps, 6)
        row["score_out"] = s
        prev = s

    for i, row in enumerate(top):
        row["reasoning"] = reasoning.generate(row["rec_min"], row["sc"], i + 1)

    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        for i, row in enumerate(top):
            w.writerow([row["candidate_id"], i + 1, f"{row['score_out']:.6f}", row["reasoning"]])

    dbg = out + ".debug.csv"
    cols = ["candidate_id", "final", "fit", "m", "title", "family", "archetype", "yoe",
            "company", "industry", "location", "country", "domains", "must_have", "n_ai_raw",
            "g_role", "g_arch", "g_dom", "g_comp", "g_yoe", "g_loc", "penalties",
            "notes", "hard_reasons"]
    with open(dbg, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rank"] + cols)
        w.writeheader()
        for i, row in enumerate(top):
            r = {k: row.get(k) for k in cols}
            r["rank"] = i + 1
            w.writerow(r)

    dt = time.time() - t0
    print(f"Processed {n} candidates in {dt:.1f}s")
    print(f"Hard-rejected (honeypot/impossible): {hard_rejects}")
    print(f"Scorable (fit>0): {len(scored)}")
    print(f"Wrote {out} (top 100) and {dbg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--out", default="submission.csv")
    args = ap.parse_args()
    run(args.candidates, args.out)


if __name__ == "__main__":
    main()
