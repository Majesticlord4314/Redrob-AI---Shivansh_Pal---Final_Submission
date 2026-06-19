#!/usr/bin/env python3
"""Weight sensitivity sweep.

Precomputes each candidate's 6 feature-group scores once, then re-weights
instantly. Reports how much the top-10 / top-100 churn under +/-20% weight
perturbations, plus gold-set composite stability. Stable top-10 => robust ranker.
"""
import csv, math, os, sys, itertools, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from redrob import loader, consistency, scoring, behavioral

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = "../India_runs_data_and_ai_challenge/candidates.jsonl"
KEYS = ["role", "archetype", "domains", "company", "yoe", "location"]
W0 = dict(scoring.WEIGHTS)

gold = {r["candidate_id"]: int(r["tier"]) for r in csv.DictReader(open(os.path.join(HERE, "gold", "gold_labels.csv")))}

# precompute per-candidate components
P = []  # (cid, comps dict, penalty_sub, soft, m, hard, gold_tier_or_None)
for rec in loader.load(DATA):
    hard, _, soft = consistency.check(rec)
    sc = scoring.score(rec, hard, soft)
    pen = 0.25 * sum(1 for p in sc["penalties"] if p in ("research_only", "cv_only"))
    m, _ = behavioral.modifier(rec)
    comps = (sc["g_role"], sc["g_arch"], sc["g_dom"], sc["g_comp"], sc["g_yoe"], sc["g_loc"])
    P.append((rec["candidate_id"], comps, pen, soft, m, hard, gold.get(rec["candidate_id"])))
print(f"precomputed {len(P)} candidates")


def rank_with(W):
    wv = [W[k] for k in KEYS]
    scored = []
    for cid, comps, pen, soft, m, hard, gt in P:
        if hard:
            continue
        ws = sum(wv[i] * comps[i] for i in range(6)) - pen
        if ws <= 0:
            continue
        final = ws * (1 - soft) * m
        scored.append((final, cid))
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [c for _, c in scored[:100]]


def gold_composite(W):
    wv = [W[k] for k in KEYS]
    rows = []
    for cid, comps, pen, soft, m, hard, gt in P:
        if gt is None:
            continue
        if hard:
            final = 0.0
        else:
            ws = max(sum(wv[i] * comps[i] for i in range(6)) - pen, 0.0)
            final = ws * (1 - soft) * m
        rows.append((final, gt))
    rows.sort(key=lambda x: -x[0])
    tiers = [t for _, t in rows]

    def dcg(ts): return sum((2 ** t - 1) / math.log2(i + 2) for i, t in enumerate(ts))
    def ndcg(ts, k):
        idcg = dcg(sorted(ts, reverse=True)[:k]); return dcg(ts[:k]) / idcg if idcg else 0
    rel = [1 if t >= 3 else 0 for t in tiers]; tot = sum(rel)
    h = 0; ap = 0.0
    for i, r in enumerate(rel):
        if r: h += 1; ap += h / (i + 1)
    ap = ap / tot if tot else 0
    p10 = sum(1 for t in tiers[:10] if t >= 3) / 10
    return 0.5 * ndcg(tiers, 10) + 0.3 * ndcg(tiers, 50) + 0.15 * ap + 0.05 * p10


base100 = rank_with(W0)
base10 = base100[:10]
base_comp = gold_composite(W0)
print(f"\nbaseline gold composite={base_comp:.4f}")
print("baseline top-10:", [c[-4:] for c in base10])


def overlap(a, b):
    return len(set(a) & set(b))


print("\n--- single-weight +/-20% perturbations ---")
print(f"{'perturb':<18}{'top10∩':>8}{'top100∩':>9}{'gold':>9}")
worst10 = 100
for k in KEYS:
    for sign, tag in [(0.8, "-20%"), (1.2, "+20%")]:
        W = dict(W0); W[k] = W0[k] * sign
        t100 = rank_with(W); t10 = t100[:10]
        o10 = overlap(t10, base10); o100 = overlap(t100, base100)
        worst10 = min(worst10, o10)
        print(f"{k+' '+tag:<18}{o10:>6}/10{o100:>7}/100{gold_composite(W):>9.4f}")

print("\n--- random joint perturbations (all weights, +/-20% uniform) ---")
random.seed(0)
o10s, o100s, comps = [], [], []
for _ in range(30):
    W = {k: W0[k] * random.uniform(0.8, 1.2) for k in KEYS}
    t100 = rank_with(W); t10 = t100[:10]
    o10s.append(overlap(t10, base10)); o100s.append(overlap(t100, base100))
    comps.append(gold_composite(W))
print(f"top10  overlap: min={min(o10s)}/10  mean={sum(o10s)/len(o10s):.1f}/10")
print(f"top100 overlap: min={min(o100s)}/100 mean={sum(o100s)/len(o100s):.1f}/100")
print(f"gold composite: min={min(comps):.4f} max={max(comps):.4f} (baseline {base_comp:.4f})")
print(f"\nworst single-weight top-10 overlap: {worst10}/10")
