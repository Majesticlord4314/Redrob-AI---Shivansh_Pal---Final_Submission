# HACKATHON_CONTEXT.md — Redrob "Intelligent Candidate Discovery & Ranking" Challenge

> Compressed permanent memory. Read this file first. Everything verified against the actual data (100,000 candidates) on 2026-06-19. Implementation NOT yet started.

## 1. TASK IN ONE LINE
Rank the **top 100 of 100,000 candidates** for ONE job description (Senior AI Engineer, founding team, Redrob AI) → output `submission.csv` with `candidate_id,rank,score,reasoning`. Best fit = rank 1.

## 2. FILES (in `India_runs_data_and_ai_challenge/`)
- `candidates.jsonl` — 100k candidates, 487MB uncompressed (~52MB gz in real bundle). Stream it; do NOT load all into RAM naively.
- `candidate_schema.json` — full field schema (profile, career_history[1-10], education[0-5], skills, certifications, languages, redrob_signals{23 fields}).
- `job_description.docx` → the JD. **The last two paragraphs ("Final note for participants") are decisive** — they tell you the trap.
- `submission_spec.docx` — rules, scoring, 5 evaluation stages.
- `redrob_signals_doc.docx` — the 23 behavioral signals.
- `sample_submission.csv` — **DELIBERATELY BAD baseline** (a keyword-stuffer victim; see §7). Format reference only.
- `submission_metadata_template.yaml` — metadata to ship in repo + portal.
- `validate_submission.py` — run before submitting.
- Convert docx with: `textutil -convert txt -output /tmp/x.txt file.docx` (macOS).

## 3. THE JOB (what "relevant" means)
Senior AI Engineer, Pune/Noida hybrid, **5–9 yrs (flexible range, not hard)**. Ideal = **6–8 yrs, 4–5 of them applied ML at PRODUCT companies**, has shipped ≥1 end-to-end **ranking / search / recommendation** system to real users, opinions on retrieval/eval/LLM-integration, located in or willing to relocate to Noida/Pune, **active on platform**.

MUST-HAVE: production **embeddings retrieval** (sentence-transformers/BGE/E5/OpenAI emb), **vector DB / hybrid search** (Pinecone/Weaviate/Qdrant/Milvus/FAISS/Elasticsearch/OpenSearch), strong Python, **ranking-eval frameworks (NDCG/MRR/MAP)**.
NICE: LoRA/QLoRA/PEFT, learning-to-rank (XGBoost/neural), HR-tech, distributed/inference, OSS.

### DISQUALIFIERS / REJECT (explicit in JD)
- **Pure research / academic** (incl. title "AI Research Engineer", "Senior Applied Scientist") with no production deployment → reject.
- **CV / speech / robotics** primary without NLP/IR → reject ("Computer Vision Engineer" title is a trap).
- **Consulting-only careers** (TCS, Infosys, Wipro, Cognizant, Accenture, Capgemini, Tech Mahindra, Mphasis, Mindtree, Genpact, HCL...) for entire career → reject. (31,155 candidates currently at such firms; only penalize if *entire* history is services.)
- **Title-chasers** — job-hop every ~1.5 yrs chasing Senior→Staff→Principal → reject (want 3+ yr tenure intent).
- **Framework enthusiasts** — only recent (<12mo) LangChain-calling-OpenAI, no pre-LLM ML → reject unless real prior ML.
- **18+ months no code** (moved to "architecture"/"tech lead") → reject. This role writes code.
- **Closed-source 5+ yrs, no external validation** → weak.

## 4. SCORING (the math you optimize)
`composite = 0.50·NDCG@10 + 0.30·NDCG@50 + 0.15·MAP + 0.05·P@10`
- **Top-10 quality dominates (50%).** Get the 10 best, in the right order. NDCG is order-sensitive & log-discounted → rank 1–3 matter most.
- NDCG@50 (30%): the next 40 must be relevant and roughly ordered.
- MAP (15%) + P@10 (5%, tier-3+ in top10): reward precision; ranks 51–100 barely matter.
- **Precision >> recall.** Aggressive filtering to a clean candidate pool beats broad ranking. Better 10 great than 1000 maybes (JD says this explicitly).
- Ground truth uses **relevance tiers** (tier 0..5; "tier 3+ = relevant"; honeypots forced to **tier 0**; "Tier 5" = top fit).
- Tiebreak between submissions: P@5 → P@10 → earlier timestamp.

## 5. CONSTRAINTS (hard, enforced at Stage 3 in Docker)
≤5 min wall-clock · ≤16GB RAM · **CPU only** · **NO network** (no hosted LLM APIs) · ≤5GB disk. Per-candidate LLM calls = impossible/disqualified. Pre-computation (embeddings/index/training) allowed offline and may exceed 5min, but the **ranking step that emits the CSV must finish in 5 min** and be reproducible from the repo. 3 submissions max, last valid counts. **No live leaderboard** — score revealed only after close. Validate locally with methodology, not by submitting variants.

## 6. SUBMISSION FORMAT (validator-enforced)
CSV, UTF-8, filename `<participant_id>.csv`. Header EXACTLY `candidate_id,rank,score,reasoning`. Exactly 100 data rows. Ranks 1..100 each once. candidate_id `^CAND_[0-9]{7}$`, must exist in pool, unique. `score` float, **monotonically non-increasing** with rank. Score ties allowed but then tie-break by **candidate_id ascending** (validator checks this!). Common auto-rejects: 99/101 rows, rank from 0, dup ids, all-equal scores, increasing scores, wrong extension.

## 7. THE CENTRAL TRAP — KEYWORD STUFFERS (verified)
Skills are assigned ~randomly across the pool. There is a set of **~11 "AI core" skills** (each on ~5,000 candidates): Information Retrieval, LLMs, Recommendation Systems, Semantic Search, Sentence Transformers, Embeddings, Vector Search, Pinecone, FAISS, RAG, Fine-tuning LLMs; plus a rarer tier (~1,400 each): QLoRA, Weaviate, Milvus, Learning to Rank, BM25, PyTorch/TensorFlow, Qdrant, PEFT, LoRA, NLP, Elasticsearch, OpenSearch.
**~6,000 candidates carry 6–10 AI core skills but hold NON-AI titles** (HR Manager, Accountant, Content Writer, Graphic Designer, Mechanical Engineer...). These are the **keyword stuffers**.
**`sample_submission.csv` ranks exactly these stuffers #1–100** (its reasoning literally says "HR Manager with 6.1 yrs; 9 AI core skills"). Its `score` is fake/linear (`1.0 − 0.008·(rank−1)`). **It is the naive-baseline-that-fails. Do not emulate it.**
→ **A skill-keyword/embedding-only ranker WILL be fooled.** The decisive signal is **current_title + career_history descriptions**, validated against the JD. High AI-skill-count on a non-AI title is a NEGATIVE (stuffing) signal, not positive.

## 8. HONEYPOTS (~80 stated; ~70 found by clean signatures; forced to tier 0)
>10% honeypots in top 100 (i.e. ≥11) = **Stage-3 disqualification**, regardless of score.
Verified impossible-profile signatures (union ≈70 candidates):
- **Expert proficiency with `duration_months == 0`** — 21 candidates (account for all 84 such skill instances; 3–5 each). Matches spec example verbatim.
- **Σ career durations > years_of_experience·12 + ~14mo** (worked more months than career allows) — 24.
- **A single role longer than total experience** — 21 (subset of above).
- **Earliest career start → today span >> years_of_experience (+2.5y)** — 3.
- **Career span << years_of_experience (−2.5y)** (claims 15–16 yrs but dates show 4–8) — 25.
**15 of these honeypots wear AI/data titles** (NLP Engineer×3, Recsys Engineer×2, Search Engineer×2, AI Engineer×2, ML Engineer, Applied ML, Senior ML, Senior Applied Scientist, Senior Data Engineer, Backend Engineer) with PERFECT skills (RAG/Pinecone/Weaviate/Sentence Transformers) at product companies. These specifically trap title+skill matchers. Known dangerous IDs: CAND_0039521, 0093547, 0095619, 0001610, 0037000, 0019480, 0055992, 0091534, 0071115, 0010770, 0013536, 0039754, 0093331, 0090900, 0095140.
**Defense:** a per-candidate internal-consistency check (yoe ≈ career span ≈ Σdurations; no expert@0-months) naturally drops them. No special-casing needed per spec, but DO compute it.

## 9. BEHAVIORAL SIGNALS = MODIFIER, not primary (23 in `redrob_signals`)
JD: "down-weight perfect-on-paper but unavailable." Treat as a **multiplier on top of fit score**, never as primary rank.
Population stats (verified): recruiter_response_rate med 0.44 (0.02–0.95); profile_completeness med 56.8; interview_completion med 0.62; offer_acceptance med −1 (most have no history, −1 sentinel); github_activity med −1 (64,637 have none, −1 sentinel — do NOT treat −1 as low score, treat as "unknown"); notice_period med 90d (JD wants ≤30, ≤30 buyable); connection_count med 335; saved_by_recruiters med 7; open_to_work true for 35,339; last_active spread over last ~6–7 months.
- **Availability signals (down-weight if bad):** stale last_active, low recruiter_response_rate, open_to_work=false, interview_completion low.
- **Quality-ish signals:** saved_by_recruiters_30d, profile_completeness, skill_assessment_scores (corroborate claimed skills), github_activity (only when ≥0).
- **TRAP signals (do not over-weight):** raw connection_count, profile_views, search_appearance (vanity); endorsements (can be inflated); expected_salary; github=−1 ≠ bad.
- **Notice period / location / relocation:** soft preferences (Noida/Pune/relocate-willing slight +).

## 10. CANDIDATE POOL SHAPE (verified)
75,113 India / 9,978 USA / rest AU,CA,UK,DE,SG,UAE. YOE 1.0–16.9 (med 6.8). Skills/cand 5–23 (med 9). Career entries 1–9 (med 2–3). Edu tiers: tier_3 53k, tier_4 52k, tier_2 28k, tier_1 7k (tier_1 = prestige; tiering is internal/"unknown" allowed).
**Title counts (relevant ones):** ML Engineer 167, AI Research Engineer 153 (RESEARCH=trap), Data Scientist 145, Senior SWE(ML) 142, Computer Vision Engineer 132 (CV=trap), Junior ML Engineer 131, AI Specialist 130, Recsys Engineer 26, Machine Learning Engineer 24, Applied ML Engineer 23, Search Engineer 23, AI Engineer 21, Senior Data Scientist 19, NLP Engineer 14, Senior NLP 6, Senior ML 6, Staff ML 6, Senior AI Engineer 4, Senior Applied Scientist 4, Lead AI Engineer 3. Adjacent: Data/Senior Data/Analytics/Backend Engineer, Data Analyst (~3,600). Everything else (Business Analyst, HR, Mechanical, Accountant, etc.) ~5,800 each = noise/stuffer hosts.
**~465 candidates have a strong AI title; ~310 are "genuinely strong"** (strong AI title + product company + 4–10 yrs + ≥2 real AI skills + passes consistency). The top-100 should come mostly from this ~310 plus the best **"plain-language Tier 5"** adjacents (Data/Backend Engineers whose career_history describes building recsys/search/ranking at product cos even without buzzwords). Example near-perfect: **CAND_0000031** (Recsys Engineer, Swiggy, 6.0y, vector-search skills, response 0.91, active 2026-05).

## 11. "PLAIN-LANGUAGE TIER 5" (JD-defined)
A top candidate may NOT use words "RAG"/"Pinecone" but whose career_history says they "built a recommendation system at a product company." Must be found by **reading career_history descriptions + summary**, not skill keywords. Mirror image of the stuffer. Reward these. (e.g. CAND_0000001: Backend/data eng, Milvus advanced, built streaming pipelines, honest summary about transitioning to ML — adjacency, weigh on substance.)

## 12. EVALUATION STAGES (survive ALL)
1. **Format validation** (auto) — spec §3. 2. **Scoring** — composite vs hidden GT; below cutoff = out. 3. **Code reproduction + honeypot check** — repo reproduced in Docker (5min/16GB/CPU/no-net); honeypot>10% top100 = DQ; fabricated/missing repo = DQ. 4. **Manual review** — reasoning quality (6 checks), methodology coherence, **git history authenticity (real iteration, not single dump)**, code quality. 5. **30-min defend-your-work interview** for top X — explain & defend architecture.
→ Implies: keep a **real git history with iterative commits**; write a coherent **methodology_summary**; make code clean & reproducible from ONE command; be able to defend every design choice. AI-assisted is fine & declared; AI-only "paste-and-pray" dies at 3–5.

## 13. REASONING COLUMN (Stage 4, 10 random rows checked)
Strongly recommended. Each must: cite **specific profile facts** (yoe, title, named skills, signal values); connect to **specific JD requirements**; **acknowledge concerns/gaps** honestly; **no hallucination** (only facts in the profile); be **varied** (not templated/name-insert); **tone matches rank** (no glowing rank-95 / critical rank-5). Generate reasoning FROM the same features that drove the rank, programmatically, with varied templates + real values. Plain, specific, honest > impressive.

## 14. ORGANIZER INTENT (inferred, evidence-backed)
Reward: engineers who **read profiles & reason about JD-intent gap**, build a **transparent, reproducible, consistency-aware ranker** under real latency constraints, and can defend it. Eliminate: keyword/embedding-only matchers (fooled by stuffers + AI-titled honeypots), LLM-per-candidate approaches (compute), AI-only paste jobs (Stages 3–5), and over-fitters gaming a leaderboard (there is none). Common competitor mistakes: (a) embed JD+profile, cosine rank → ranks stuffers & honeypots; (b) count AI skills → = sample_submission = fail; (c) ignore behavioral availability; (d) ignore honeypots → Stage-3 DQ; (e) templated/hallucinated reasoning → Stage-4 fail; (f) non-reproducible/over-budget code → Stage-3 DQ.

## 15. RECOMMENDED APPROACH (for the future build session — NOT yet built)
Multi-stage, rule-first, transparent, fast (~seconds for 100k on CPU):
1. **Filter/retrieve** candidate set to plausible fits (title in AI/ML/IR family OR career_history mentions ranking/search/recsys/embeddings/retrieval). Drop pure-CV/speech, pure-research, consulting-only-entire-career.
2. **Consistency gate** — drop/zero honeypots (yoe vs span vs Σduration; expert@0mo). Keeps top100 honeypot rate ≈0.
3. **Fit score** = weighted: title match · career-substance (descriptions mention retrieval/ranking/recsys/eval/embeddings/vectorDB) · product-vs-services · yoe-fit (peak 6–8, soft band) · skills (with **endorsement+duration+assessment trust**, so stuffed 0-duration skills don't count) · NLP/IR-not-CV · location/relocation.
4. **Behavioral modifier** (multiplicative, bounded, e.g. 0.7–1.1) on availability (last_active recency, response_rate, open_to_work, interview_completion); treat −1 sentinels as neutral.
5. **Rank top 100**, scores strictly non-increasing (add tiny epsilon or use candidate_id asc tie-break), generate per-candidate varied honest reasoning from the features used.
Keep XGBoost/LTR or local sentence-transformer embeddings only as *optional* re-rank within the filtered pool (precompute offline; CPU-fast at rank time) — but the **title/career/consistency rules are the backbone** that beats both traps.

## 16. OPEN QUESTIONS / TO VERIFY LATER
- Exact GT relevance-tier function is hidden — our tier mapping is a hypothesis; validate ordering logic against JD, not a fitted number.
- ~10 honeypots not caught by current signatures (we found ~70/80) — possibly company-founding-vs-tenure ("8yrs at a 3yr-old company") needing a company-founding table, or edu-timeline contradictions. Revisit before final.
- Confirm whether services-firm penalty should be "entire career" only (JD nuance: current-at-consulting OK if prior product experience).
- Whether `tier_1` education should be a real positive (JD never asks for pedigree → probably minor).
- Metadata required at submit: team, contacts, **GitHub repo (reachable)**, **sandbox link** (HF Spaces/Streamlit/Replit/Colab/Docker/Binder, runs ≤100 sample), AI-tools declaration, compute summary, methodology. Prepare these.
