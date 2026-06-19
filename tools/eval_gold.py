#!/usr/bin/env python3
"""Evaluate the current scorer against the gold set.

Ranks ALL gold candidates (including consistency-rejected ones, which should
sink to the bottom) and reports NDCG@10, NDCG@50, MAP, P@10 + the composite,
plus Spearman(scorer_rank, gold_tier) and the top-15 with gold tiers.

This is a PROXY metric on 104 hand-tiered candidates, not the hidden GT. Use it
to compare ranker versions, not as an absolute score.
"""
import csv, math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from redrob import loader, consistency, scoring, behavioral

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = sys.argv[1] if len(sys.argv) > 1 else "../India_runs_data_and_ai_challenge/candidates.jsonl"

gold = {}
for r in csv.DictReader(open(os.path.join(HERE, "gold", "gold_labels.csv"))):
    gold[r["candidate_id"]] = int(r["tier"])

recs = {}
for rec in loader.load(DATA):
    if rec["candidate_id"] in gold:
        recs[rec["candidate_id"]] = rec


def score_all():
    out = []
    for cid, rec in recs.items():
        hard, reasons, soft = consistency.check(rec)
        sc = scoring.score(rec, hard, soft)
        m, _ = behavioral.modifier(rec)
        final = sc["fit"] * m
        out.append((final, cid, gold[cid], rec["title"]))
    out.sort(key=lambda x: (-x[0], x[1]))
    return out


def dcg(tiers):
    return sum((2 ** t - 1) / math.log2(i + 2) for i, t in enumerate(tiers))


def ndcg(ranked_tiers, k):
    ideal = sorted(ranked_tiers, reverse=True)
    idcg = dcg(ideal[:k])
    return dcg(ranked_tiers[:k]) / idcg if idcg > 0 else 0.0


def average_precision(ranked_tiers, rel_threshold=3):
    rel = [1 if t >= rel_threshold else 0 for t in ranked_tiers]
    total_rel = sum(rel)
    if total_rel == 0:
        return 0.0
    hits, s = 0, 0.0
    for i, r in enumerate(rel):
        if r:
            hits += 1
            s += hits / (i + 1)
    return s / total_rel


def precision_at_k(ranked_tiers, k, rel_threshold=3):
    top = ranked_tiers[:k]
    return sum(1 for t in top if t >= rel_threshold) / k


def spearman(ranked):
    # ranked: list ordered by scorer; compute corr between scorer-rank and gold tier
    n = len(ranked)
    scorer_rank = list(range(n))  # 0 best
    tiers = [t for (_, _, t, _) in ranked]
    # rank of tiers (higher tier -> better -> lower rank index). Use -tier.
    import statistics
    # Spearman via Pearson on ranks
    tr = sorted(range(n), key=lambda i: -tiers[i])
    tier_rank = [0] * n
    for pos, i in enumerate(tr):
        tier_rank[i] = pos
    mx = statistics.mean(scorer_rank); my = statistics.mean(tier_rank)
    num = sum((scorer_rank[i] - mx) * (tier_rank[i] - my) for i in range(n))
    den = math.sqrt(sum((scorer_rank[i] - mx) ** 2 for i in range(n)) *
                    sum((tier_rank[i] - my) ** 2 for i in range(n)))
    return num / den if den else 0.0


ranked = score_all()
tiers = [t for (_, _, t, _) in ranked]
n10 = ndcg(tiers, 10); n50 = ndcg(tiers, 50)
ap = average_precision(tiers); p10 = precision_at_k(tiers, 10)
composite = 0.50 * n10 + 0.30 * n50 + 0.15 * ap + 0.05 * p10
sp = spearman(ranked)

print(f"gold candidates: {len(ranked)}  (relevant tier>=3: {sum(1 for t in tiers if t>=3)})")
print(f"NDCG@10={n10:.4f}  NDCG@50={n50:.4f}  MAP={ap:.4f}  P@10={p10:.4f}")
print(f"COMPOSITE={composite:.4f}   Spearman(rank,tier)={sp:.4f}")
print()
print("top 15 by scorer:")
for i, (f, cid, t, title) in enumerate(ranked[:15]):
    print(f"  {i+1:2} tier={t} score={f:.3f} {title[:32]:<33} {cid}")
print("bottom 6 (should be tier 0):")
for f, cid, t, title in ranked[-6:]:
    print(f"     tier={t} score={f:.3f} {title[:32]:<33} {cid}")
