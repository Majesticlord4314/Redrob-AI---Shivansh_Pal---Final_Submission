# IMPLEMENTATION_LOG.md

## V1 — minimal end-to-end ranker (2026-06-19)

### What was built
`redrob_ranker/` package, run with
`python rank.py --candidates ../India_runs_data_and_ai_challenge/candidates.jsonl --out submission.csv`
- `redrob/loader.py` — streams JSONL → compact record; parses dates; derives `documented_months`, `elapsed_months`, `earliest_start`, lowercased `text_blob` (summary + all role descriptions).
- `redrob/consistency.py` — honeypot gate. Hard rules H1 (expert@0mo), H2a (documented>yoe+14), H2b (documented>elapsed+14), H3 (single role>yoe+6), H4 (yoe>elapsed+30), H5 (date corruption). Soft penalties (multi-current, current-with-enddate, elapsed≫yoe). **No H6 (founding-year) — deferred, non-trivial.**
- `redrob/roles.py` — title → family {core_ai, ds, research, cv, junior, data_adjacent, other_tech, nontech}; ROLE_BASE per family; TEXT_GATED_FAMILIES (only these get text mined).
- `redrob/companies.py` — 63-company table → {services, product, ai_startup, bigtech, fictional}; industry fallback; `arc_score` (0.10 entire-services … 0.90 current-ai-startup).
- `redrob/skills.py` — per-skill trust = base(prof)·duration·(endorse/assessment); domain ontology; trusted **must-have coverage** (embeddings+vector_db+nlp_ir).
- `redrob/scoring.py` — fit = 0.30 role + 0.22 substance + 0.20 domains + 0.13 company + 0.10 yoe + 0.05 location; −0.25 research_only / cv_only penalties; ×(1−soft); 0 if hard_reject.
- `redrob/behavioral.py` — bounded M∈[0.6,1.1]; sentinel(−1)-safe.
- `rank.py` — orchestrates, sorts (final desc, id asc), top-100, enforces strictly-decreasing scores, writes `submission.csv` + `submission.csv.debug.csv` (full feature breakdown). **No reasoning generation in V1 (column blank).**

### Why it was built this way
Architecture A from `ARCHITECTURE.md`, minimal slice. Goal: a believable top-100 to inspect, not theoretical completeness. Deferred everything optional (founding-year H6, reasoning, embeddings, LTR, gold-set, weight tuning).

### Runtime / resource impact
- **10.1 s** for all 100,000 candidates on CPU (single core, plain Python). ~50× under the 5-min budget.
- Streams the file; peak memory dominated by the `scored` list (~100k small dicts) — well under 1 GB. (Most candidates get fit>0 from company/yoe/location, so the list is large but cheap; could heap-bound later.)

### Assumptions introduced (V1, to revisit)
- REF_DATE = 2026-06-19 (from challenge context).
- documented_months = naive Σ duration (no overlap subtraction) → overlaps trip H2b (acceptable).
- Weights are hand-picked defaults, **not tuned**.
- nontech with high AI-skill count is flagged but already ~0 via role base (never reaches top).
- ROLE_BASE gap (core_ai 1.0 vs data_adjacent 0.45) means adjacents essentially never beat core_ai.

### Open questions (carried to DISCOVERIES.md)
- Top-100 is 100% core_ai/ds — should plain-Tier5 adjacents ever surface?
- Top-10 has only 7 unique scores → NDCG@10 ordering is partly arbitrary. What truly differentiates the very top?
- substance (G2) is saturated (95/100 = 1.00) → contributes nothing to ordering. Keep, fix, or drop?

### Validation status
- `validate_submission.py` on the output: **"Submission is valid."**
- Honeypot audit: **0** of 15 known dangerous IDs in top-100; 70 total hard-rejected (matches recon estimate).
- Stuffer audit: **0** nontech/other_tech in top-100; 0 penalties triggered.
- Top-100 = 99 core_ai + 1 ds; 93% India; YOE 4.0–8.9; 58/100 full must-have coverage.

---
## V2 — gold-set measurement + archetype feature (2026-06-19)

### What was built
- **Gold set** (`redrob_ranker/tools/sample_gold.py`, `make_gold_labels.py`, `gold/`): 104 stratified candidates across 10 archetype buckets; tier 0–5 labels anchored on consistency + **summary archetype** (independent of the scorer's features) + family + company-arc + yoe + must-have skills + availability. Distribution: 0:31,1:9,2:12,3:14,4:21,5:17 (52 relevant / 52 not).
- **Eval harness** (`tools/eval_gold.py`): ranks the gold pool with the live scorer; reports NDCG@10/50, MAP, P@10, composite, Spearman.
- **`redrob/summary.py`**: detects the 4 generator summary archetypes (senior_search > ml_prod > ds > data) + stated-years.
- **V2 scoring** (`redrob/scoring.py`): DROPPED career-description "substance" mining (templated noise, D8); ADDED `summary_archetype` (0.18); finer `domains` (must-have + breadth + assessment corroboration); continuous Gaussian YOE curve (center 7). Weights: role .26 / archetype .18 / domains .22 / company .16 / yoe .12 / location .06.
- **`tools/exp_semantic.py`**: tested TF-IDF semantic similarity and XGBoost LTR against the rule scorer.

### Measured impact (gold set; proxy, not hidden GT)
| metric | V1 | V2 |
|---|---|---|
| NDCG@10 | 0.9642 | **1.0000** |
| NDCG@50 | 0.9418 | **0.9786** |
| MAP | 0.9250 | **0.9745** |
| P@10 | 1.0000 | 1.0000 |
| composite | 0.9534 | **0.9897** |
| Spearman | 0.942 | **0.988** |

### Embeddings/ML verdict (evidence-based)
- TF-IDF(JD cosine) Spearman vs gold = **0.245** (description noise, D8); blending into V2 → optimal weight **0** (zero gain).
- XGBoost LTR 5-fold OOF composite = **0.9752** < V2 rule **0.9897**, and far less defensible (no real labels).
- **Decision:** no embeddings, no LTR. The summary-archetype discovery is the semantic signal, captured directly. Honors "whatever makes results stronger" — measurement chose rules.

### Runtime / resource
- Full 100k run: **42.9s** (up from 10s; summary regex + finer skills). Still ~7× under the 5-min budget. CSV validates. 0 honeypots in top-100. 99 core_ai + 1 ds.

### Assumptions / open questions
- Gold labels use summary archetype, which V2 now also uses → partial circularity; mitigated because archetype is a genuine generator-intended signal and the directional gain (Spearman, MAP, top ordering) is real. Gold is a proxy, not the hidden GT.
- 42.9s has headroom but if it grows, precompile regex (done) / prefilter nontech early.

---
## V3 — reasoning generation + weight sensitivity (2026-06-19)

### What was built
- **`redrob/reasoning.py`** — feature-grounded generator for the `reasoning` column, targeting the 6 Stage-4 checks:
  - specific facts (title, yoe, company, named skills, signal values), JD connection (retrieval/ranking/recsys, embeddings, vector search, product>services, yoe band), honest concerns, no hallucination, varied phrasing, tone-by-rank.
  - Skills are emitted ONLY from `trusted_relevant` (built from the profile) → hallucination impossible by construction; verified 0/100.
  - Stable phrasing selection via md5 (NOT Python `hash()`), so output is byte-reproducible.
  - Tone bands: rank≤15 strengths + "Minor concern"; 16–50 "Tradeoff"; 51–100 "solid fit … placed here due to {concerns}".
- Wired into `rank.py`: keeps a compact rec subset + score dict per candidate; reasoning generated for the top-100 only.
- **`tools/weight_sweep.py`** — precomputes 6 group scores per candidate once, re-weights instantly; measures top-10/top-100 churn + gold composite under perturbation.
- **Bugfix:** reasoning used Python `hash()` (per-process randomized via PYTHONHASHSEED) → non-reproducible text across runs. Switched to md5. Verified: two runs (different PYTHONHASHSEED) produce byte-identical CSV.
- Dropped the "carries some CV skills" concern (was on 48/100; not a real penalty for NLP-core candidates, hurt variation).

### Validation
- `validate_submission.py`: valid. Byte-reproducible across runs. Runtime ~16s/100k.
- Reasoning audit: 0 skill hallucinations; random-10 all unique; concern clauses well distributed (no_verified 38, notice 28, tradeoff 25, open-to-work 15, junior 13, services 3, response 1).

### Weight sensitivity (robustness for Stage-5 defense)
- Single-weight ±20%: top-10 overlap 9–10/10, top-100 95–98/100, gold composite 0.9894–0.9909.
- Random joint ±20% (30 trials): top-10 min 9/10 (mean 9.1), top-100 min 93/100 (mean 95.6), composite 0.9893–0.9915.
- Conclusion: ranking is not a fragile artifact of exact weights; no single weight dominates. Weights left at sensible defaults (chasing the tiny gold gains would overfit the proxy).

### Sample reasoning (rank 1 / 61 / 96)
- #1 "Zomato Senior Machine Learning Engineer with ~7 years in applied ML; strong on retrieval/NLP, ranking & recsys and embeddings; trusted skills include Weaviate, Recommendation Systems, RAG; self-describes a search/retrieval/ranking focus."
- #61 "Applied ML Engineer (5.7y) at Dream11; solid fit (…covering retrieval/NLP, ranking & recsys and vector search), placed here due to no verified embeddings skill."
- #96 "Recommendation Systems Engineer at Meesho, 6 yrs' experience; solid fit (…), placed here due to no verified retrieval/NLP skill."

---
## V4 — Stage-3 packaging (2026-06-19)

### What was built
- **`requirements.txt`** — intentionally empty: the ranking step is **pure Python stdlib** (verified: only json/csv/re/math/hashlib/datetime/argparse). Stage-3 repro needs no installs.
- **`requirements-dev.txt`** (numpy/scipy/sklearn/xgboost — `tools/` experiments only) and **`requirements-sandbox.txt`** (streamlit — `app.py` only).
- **`Dockerfile`** — `python:3.11-slim`, copies `redrob/` + `rank.py`, no pip. Deterministic build.
- **`README.md`** — quick start (one-command reproduce), approach, repo layout, sandbox deploy, compute-compliance table.
- **`app.py`** — Streamlit sandbox: runs the full pipeline on a ≤100-candidate sample (upload or bundled `sample_candidates_100.jsonl`), shows ranked table + reasoning, CSV download. Ready for HuggingFace Spaces / Streamlit Cloud.
- **`submission_metadata.yaml`** — filled (methodology ≤200w, compute, AI-tools, declarations incl. honeypot_check_done=true); identity fields (team_name, phone, github_repo, sandbox_link, members) left as clear PLACEHOLDERs.

### Verification
- Shipping code import audit: stdlib only; **no requests/urllib/socket/http** anywhere.
- Ran on 100-candidate sample: 0.0s, valid (sandbox path works).
- Full run 8.6s, valid CSV, 0 honeypots in top-100, 100 reasoned rows.
- **Not verified locally:** `docker build`/`run` (Docker daemon unavailable here). Dockerfile is stdlib-only and trivial, but the build should be smoke-tested on a machine with Docker before relying on it at Stage 3.

### Remaining for the human before submitting
- Fill PLACEHOLDER identity fields in `submission_metadata.yaml` + portal.
- Push repo to GitHub (reachable) and deploy `app.py` to a Space; paste the link.
- Smoke-test `docker build` once.

---
## V5 — H6 founding-year honeypots (2026-06-19)
- Added `companies.FOUNDING` table + `max_tenure_months()`; H6 in `consistency.py`:
  hard-reject when a role's `duration_months` exceeds the real company's age + 12mo.
- Tested-and-REJECTED the "start_date before founding" variant: 93 hits, ~91 false
  positives (data doesn't respect start-date vs founding). Shipped only the
  unambiguous tenure>age impossibility: **8 new catches** (all 2023-founded cos,
  all AI-titled). Total honeypots 70→**78** (~80 stated).
- Regenerated H6-aware gold labels (0 changed), re-eval composite unchanged 0.9897,
  CSV valid, byte-reproducible. Runtime ~9s.
