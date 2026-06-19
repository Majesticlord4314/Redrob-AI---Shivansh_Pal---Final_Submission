# Redrob Candidate Ranker

Ranks the top-100 candidates from a 100,000-candidate pool for the **Senior AI
Engineer** job description (Redrob "Intelligent Candidate Discovery & Ranking
Challenge"). Rule-based, consistency-gated, fully transparent — **pure Python
standard library, CPU-only, no network, ~16s for 100k**.

## Quick start (one command to reproduce the submission)

```bash
python rank.py --candidates ./candidates.jsonl --out ./submission.csv
```

That's it — no `pip install` needed. Writes `submission.csv` (the top-100 with
`candidate_id,rank,score,reasoning`) plus `submission.csv.debug.csv` (per-feature
breakdown for inspection).

Requires Python 3.10+ (developed on 3.12, Docker image pins 3.11).

### Validate the output

```bash
python /path/to/validate_submission.py submission.csv   # -> "Submission is valid."
```

### Reproduce in Docker (matches Stage-3 constraints)

```bash
docker build -t redrob-ranker .
docker run --rm -v "$PWD/data:/data" redrob-ranker \
    --candidates /data/candidates.jsonl --out /data/submission.csv
```

## Approach (why it beats the planted traps)

The dataset contains two traps and a kill-switch (verified during recon):
1. **Keyword stuffers** — ~6,000 non-AI-title profiles padded with AI buzzword
   skills. The sample submission ranks exactly these → a deliberately wrong baseline.
2. **Templated text** — career *descriptions* are boilerplate randomly assigned
   across candidates, so mining them is noise.
3. **~80 honeypots** with internally impossible profiles, forced to relevance
   tier 0; **>10% of them in the top-100 = disqualification.**

The ranker is therefore **title- and consistency-driven, not keyword-driven**:

```
stream 100k → consistency gate (drop honeypots) → role-family classify
→ trusted skill-DOMAIN coverage (corroborated by duration/endorsement/assessment)
→ company product-vs-services arc → summary-archetype quality signal
→ weighted fit score → bounded behavioral (availability) modifier
→ top-100, strictly-decreasing scores → feature-grounded reasoning
```

Key design points:
- **Consistency gate** (`redrob/consistency.py`): logically-impossible checks
  (expert skill with 0 months; documented months > experience or > calendar;
  single role > whole career; experience > time since first job; date corruption).
  Catches all known honeypots with ~0 false positives → top-100 honeypot rate 0%.
- **Title-gating** (`redrob/roles.py`): only AI/ML/IR role families score highly;
  AI skills on a non-technical title are treated as stuffing, not signal.
- **Trusted skills** (`redrob/skills.py`): a skill counts only when corroborated;
  we score *distinct trusted domains* (embeddings + vector DB + NLP/IR), not skill count.
- **Summary archetype** (`redrob/summary.py`): the `summary` field is templated into
  quality tiers (search/retrieval/ranking > ML-product > DS > data); used (after the
  consistency gate) to order the top.
- **Behavioral modifier** (`redrob/behavioral.py`): bounded ×[0.6, 1.1] availability
  adjustment; sentinels (−1 GitHub/offer) treated as unknown, not penalized.

See `../ARCHITECTURE.md`, `../DISCOVERIES.md`, `../IMPLEMENTATION_LOG.md` for the
full design rationale, output-driven findings, and measurement history.

## Self-evaluation (no hidden labels)

A 104-candidate hand-tiered **gold set** (`gold/`) measures ranking quality:

```bash
python tools/eval_gold.py        # NDCG@10/50, MAP, P@10 composite + Spearman
python tools/weight_sweep.py     # robustness: top-10 stability under ±20% weights
```

Current gold composite **0.9897** (NDCG@10 1.000); top-10 stays 9–10/10 under
±20% weight perturbation. Gold is a proxy, not the hidden ground truth.

## Repository layout

```
rank.py                     # entry point — produces submission.csv
redrob/
  loader.py                 # stream JSONL -> compact records + derived fields
  consistency.py            # honeypot defense (hard gate + soft penalties)
  roles.py                  # title -> role family (gates text signals)
  companies.py              # company -> category + career-arc score
  skills.py                 # skill trust model -> trusted domain coverage
  summary.py                # summary archetype detection
  scoring.py                # weighted fit score
  behavioral.py             # bounded availability modifier
  reasoning.py              # feature-grounded reasoning column (no hallucination)
app.py                      # hosted sandbox (Streamlit)
sample_candidates_100.jsonl # 100-candidate sample for the sandbox
tools/                      # gold set, eval, weight sweep, experiments (dev-only)
Dockerfile                  # Stage-3 reproduction image
requirements.txt            # empty — ranking needs no third-party packages
requirements-dev.txt        # numpy/scipy/sklearn/xgboost (tools/ experiments only)
requirements-sandbox.txt    # streamlit (app.py only)
```

## Hosted sandbox

`app.py` is a Streamlit app that runs the full pipeline on a ≤100-candidate sample
(uploaded or the bundled `sample_candidates_100.jsonl`).

```bash
pip install -r requirements-sandbox.txt
streamlit run app.py
```

Deploy on HuggingFace Spaces or Streamlit Cloud (free tier): point the Space at
this repo with `app.py` as the entry file and `requirements-sandbox.txt` as deps.

## Compute compliance

| Constraint | This ranker |
|---|---|
| Runtime ≤ 5 min | ~16 s for 100k (CPU, single core) |
| Memory ≤ 16 GB | < 1 GB (streams the file) |
| CPU only | yes — no GPU, no ML model at rank time |
| No network | yes — no API calls, no downloads |
| Reproducible | byte-identical across runs (stable hashing) |
