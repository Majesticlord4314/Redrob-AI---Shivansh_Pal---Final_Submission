#!/usr/bin/env python3
"""Experiment: does a TF-IDF semantic feature or an XGBoost LTR beat the V2
rule scorer on the gold set? (Honoring the 'try embeddings/ML' request.)

We can't use neural embeddings (no network / sentence-transformers). TF-IDF is
the offline stand-in. XGBoost is trained on V2 features with 5-fold CV.
"""
import csv, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from redrob import loader, consistency, scoring, behavioral, summary
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = "../India_runs_data_and_ai_challenge/candidates.jsonl"

gold = {r["candidate_id"]: int(r["tier"]) for r in csv.DictReader(open(os.path.join(HERE, "gold", "gold_labels.csv")))}
recs = {rec["candidate_id"]: rec for rec in loader.load(DATA) if rec["candidate_id"] in gold}
cids = list(recs)
tiers = np.array([gold[c] for c in cids])

JD = ("senior ai engineer embeddings retrieval ranking recommendation systems search "
      "vector database hybrid search pinecone faiss nlp information retrieval learning to rank "
      "evaluation ndcg mrr map production applied machine learning product company fine-tuning llm")

# ---- 1) TF-IDF cosine of candidate text vs JD ----
texts = [recs[c]["text_blob"] + " " + recs[c]["summary"].lower() for c in cids]
vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), min_df=2)
M = vec.fit_transform(texts + [JD])
jd_vec = M[-1]
cand = M[:-1]
cos = (cand @ jd_vec.T).toarray().ravel()
sp_tfidf = spearmanr(cos, tiers).correlation

# archetype-only correlation
arch_rank = {"senior_search": 4, "ml_prod": 3, "ds": 2, "data": 1, "other": 0}
arch = np.array([arch_rank[summary.archetype(recs[c]["summary"])] for c in cids])
sp_arch = spearmanr(arch, tiers).correlation

# V2 full fit correlation
v2 = []
for c in cids:
    rec = recs[c]
    hard, _, soft = consistency.check(rec)
    sc = scoring.score(rec, hard, soft)
    m, _ = behavioral.modifier(rec)
    v2.append(sc["fit"] * m)
v2 = np.array(v2)
sp_v2 = spearmanr(v2, tiers).correlation

print("Spearman vs gold tier:")
print(f"  TF-IDF(JD cosine) : {sp_tfidf:.4f}")
print(f"  summary archetype : {sp_arch:.4f}")
print(f"  V2 full scorer    : {sp_v2:.4f}")

# does TF-IDF add info beyond V2? partial: correlate tfidf residual
# blend test: V2 + alpha*tfidf, see if gold composite improves
def metrics(scores):
    order = sorted(range(len(cids)), key=lambda i: -scores[i])
    rt = [tiers[i] for i in order]
    def dcg(ts): return sum((2**t-1)/math.log2(i+2) for i,t in enumerate(ts))
    def ndcg(ts,k):
        idcg=dcg(sorted(ts,reverse=True)[:k]); return dcg(ts[:k])/idcg if idcg else 0
    def ap(ts):
        rel=[1 if t>=3 else 0 for t in ts]; tot=sum(rel)
        if not tot: return 0
        h=0;s=0
        for i,r in enumerate(rel):
            if r: h+=1; s+=h/(i+1)
        return s/tot
    p10=sum(1 for t in rt[:10] if t>=3)/10
    return 0.5*ndcg(rt,10)+0.3*ndcg(rt,50)+0.15*ap(rt)+0.05*p10

base = metrics(v2)
# normalize for blend
v2n = (v2 - v2.mean())/ (v2.std()+1e-9)
cosn = (cos - cos.mean())/(cos.std()+1e-9)
best=(0,base)
for a in [0.05,0.1,0.2,0.3,0.5]:
    comp = metrics(v2n + a*cosn)
    if comp>best[1]: best=(a,comp)
print(f"\ngold composite: V2={base:.4f}  best V2+a*TFIDF={best[1]:.4f} (a={best[0]})")

# ---- 2) XGBoost LTR, 5-fold CV on V2 feature groups ----
try:
    import xgboost as xgb
    from sklearn.model_selection import KFold
    feats = []
    for c in cids:
        rec = recs[c]
        hard, _, soft = consistency.check(rec)
        sc = scoring.score(rec, hard, soft)
        feats.append([sc["g_role"], sc["g_arch"], sc["g_dom"], sc["g_comp"], sc["g_yoe"], sc["g_loc"], 1.0 if hard else 0.0])
    X = np.array(feats); y = tiers
    kf = KFold(n_splits=5, shuffle=True, random_state=0)
    comps = []
    for tr, te in kf.split(X):
        model = xgb.XGBRegressor(n_estimators=50, max_depth=3, learning_rate=0.1)
        model.fit(X[tr], y[tr])
        pred_full = np.zeros(len(cids)) - 1
        # rank te candidates by model, but metrics need full ordering -> eval on te subset only
        # simpler: predict all, rank all, compute composite (train leakage on tr) -> report te-only ranking quality via spearman
        pass
    # cleaner: train on 4 folds, predict held-out, accumulate out-of-fold predictions
    oof = np.zeros(len(cids))
    for tr, te in kf.split(X):
        model = xgb.XGBRegressor(n_estimators=50, max_depth=3, learning_rate=0.1)
        model.fit(X[tr], y[tr]); oof[te] = model.predict(X[te])
    sp_xgb = spearmanr(oof, tiers).correlation
    comp_xgb = metrics(oof)
    print(f"\nXGBoost 5-fold OOF: Spearman={sp_xgb:.4f}  gold composite={comp_xgb:.4f}")
    print(f"(V2 rule composite={base:.4f})")
except Exception as e:
    print("xgb experiment skipped:", e)
