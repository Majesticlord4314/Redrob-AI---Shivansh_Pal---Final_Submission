# ARCHITECTURE.md — Redrob Ranker: Design & Build Plan

> Source of truth: `HACKATHON_CONTEXT.md` + `RESEARCH_NOTES.md`. LIVING DOC — see V2 update below for what actually got built/changed after contact with outputs.

## ⟳ LIVING UPDATE — V2 built & measured (2026-06-19)
Architecture A (rule/feature, consistency-gated) was built and validated. Two output-driven changes from the original design:
- **DROPPED career-description "substance" mining.** Descriptions turned out to be **templated boilerplate randomly assigned across candidates/titles** (DISCOVERIES D8) → pure noise. Removed.
- **ADDED `summary_archetype` feature.** The `summary` field is templated into 4 quality archetypes (senior_search > ml_prod > ds > data) that encode the generator's intended quality and are independent of title/skills (D9). This became the key top-ordering signal.
- **Embeddings & LTR tested and REJECTED by measurement** (D11): TF-IDF Spearman vs gold 0.245 / zero blend gain; XGBoost OOF composite 0.9752 < rules 0.9897. Confirms Architecture-A choice; Architecture B/C stay shelved.
- **Measured (gold proxy, 104 hand-tiered):** composite 0.9534 (V1) → **0.9897** (V2); NDCG@10 0.964→1.000; Spearman 0.942→0.988. Full 100k run 43s, 0 honeypots, valid CSV.
- Current weights: role .26 / archetype .18 / domains .22 / company .16 / yoe .12 / location .06. Title-gate unchanged. Behavioral modifier unchanged.
- Consistency gate now H1–**H6**. H6 (D13) = tenure > real-company age (8 extra honeypots, total 78 ≈ stated ~80). The naive "start-date before founding" reading was tested and REJECTED (91 false positives — dataset ignores start-vs-founding); only the unambiguous tenure>age impossibility shipped.
- Shipped since: reasoning generation (Stage-4), weight sensitivity sweep (robust), Stage-3 packaging (Docker/README/sandbox/metadata).
- Deferred (low priority): plain-Tier5 adjacents (confirmed far below cutoff, D1).

Original design below remains the reference for rationale.

---

> Design phase notes. Source of truth: `HACKATHON_CONTEXT.md` + `RESEARCH_NOTES.md`. Grounded in a fresh scan: 63 distinct companies; `industry` is a clean product/services proxy; free-text relevance keywords appear on 25k non-AI titles → **career text must be title-gated** (a second trap).

## CORE DESIGN PRINCIPLES (non-negotiable)
1. **Title + career substance is primary; AI-skill count is bait; raw description keywords are also bait** (title-gate them).
2. **Consistency gate is a hard pre-filter** — honeypots can never reach the output set (Stage-3 DQ is binary).
3. **Behavioral signals are a bounded multiplier** (±~30%), never primary.
4. **Precision over recall** — we emit 100; optimize top-10 order above all.
5. **Everything explainable** — every score decomposes into named, defendable features (Stage 5).
6. **Trusted-domain-coverage, not skill-count** — a skill counts only when corroborated.
7. Scan is cheap (~2.3s/100k); **score everyone, take top-100** — no ANN needed.

---

# DELIVERABLE 1 — ARCHITECTURE PROPOSAL

## High-Level Pipeline
```
Raw Pool (100k JSONL)
  │  stream, parse, build compact feature record per candidate
  ▼
[A] Retrieval / Coarse scan        → score everyone (no recall loss)
  ▼
[B] Consistency Gate               → honeypot hard-reject + soft anomaly penalty
  ▼
[C] Career Understanding           → archetype: true-AI / fake-AI / stuffer / plain-Tier5 / adjacent / irrelevant
  ▼
[D] Skill Validation               → trusted-skill scores → trusted DOMAIN coverage
  ▼
[E] Company / Product-vs-Services  → company category + career-arc bonus/penalty
  ▼
[ ] Feature Extraction             → assemble feature groups G1..G8 per candidate
  ▼
[G] Scoring                        → fit_score = weighted Σ feature groups (gated to 0 if honeypot)
  ▼
[F] Behavioral Adjustment          → final = fit_score × bounded_modifier(M∈[0.6,1.1])
  ▼
Final Ranking                      → sort desc, take top 100, strictly-decreasing scores + tie-break
  ▼
Reasoning Generation               → per-candidate, from the features that drove the rank
  ▼
Submission                         → write CSV, run validate_submission.py
```
Note ordering: B and C–E all run per-candidate in one pass; logical order shown for clarity. F is applied after fit_score so it can only reorder within similar-fit bands.

## Data Flow (per stage)
| Stage | Inputs | Outputs | Complexity | Runtime | Memory | Failure modes |
|---|---|---|---|---|---|---|
| A Retrieval | raw JSONL lines | parsed compact record (title, yoe, dates, skills+meta, companies+industries, redrob subset, text blob) | O(N) stream | ~3–10 s | stream; keep ~100k compact records (~tens of MB) | OOM if whole objects retained (keep only needed fields); malformed JSON (skip+log) |
| B Consistency | dates, durations, yoe, skills, company table | `consistency: {hard_reject:bool, reasons[], soft_penalty:float}` | O(N·roles) | <2 s | negligible | false-positive on truncated senior history (mitigated: only logically-impossible rules); date parse errors |
| C Career | title, recent titles, title-gated text blob, skills | `archetype`, `role_fit∈0..1`, `system_building_evidence∈0..1`, exclusion flags | O(N·text) | ~5–15 s (regex) | negligible | text-noise FP (mitigated by title-gate); over-trusting title |
| D Skills | skills[{name,prof,endorse,dur}], skill_assessment_scores | `trusted_skill[]`, `domain_coverage{embeddings,vectordb,nlp_ir,ltr,llm,mlops,dataeng,cv}` | O(N·skills) | <3 s | small | counting stuffed skills (mitigated by trust factor) |
| E Company | current+history companies+industries, dates | `company_cat[]`, `arc_signal` (entire-services / current-services-prior-product / product-present / fictional) | O(N·roles) | <2 s | small lookup table | unmapped company (fallback to industry); fictional mishandling |
| Feature | all above | feature vector G1..G8 per candidate | O(N) | <1 s | small | feature leakage/NaN (default to neutral) |
| G Scoring | feature vector, weights, gate | `fit_score`, internal `est_tier 0..5` | O(N) | <1 s | small | weight miscalibration (validate on gold set) |
| F Behavioral | redrob subset, last_active vs ref date | `modifier∈[0.6,1.1]`, `final_score` | O(N) | <1 s | small | sentinel(−1) treated as bad (must be neutral); modifier too wide (cap it) |
| Rank | final_score, candidate_id | top-100 list | O(N log N) | <1 s | small | ties → enforce strict decrease + id-asc |
| Reasoning | per-candidate features | reasoning string | O(100) | <1 s | small | hallucination/templated (use only real fields, varied templates) |
| Submission | top-100 rows | CSV + validator pass | O(100) | <1 s | small | format violation (run validator) |
**Total budget:** ~20–40 s end-to-end for 100k on CPU — comfortably < 5 min, even with optional precomputed-embedding feature loaded.

---

## Stage A — Retrieval (design + alternatives)
**Question: scan all 100k or prefilter?** Scanning all is ~seconds; we only output 100; precision is paramount → no reason to risk recall loss.
- **A1 — Score everyone (RECOMMENDED).** Full pipeline on all 100k; take top-100. Pros: zero recall loss, simplest, most defensible, catches plain-language Tier-5s whose title isn't flagged. Cons: marginally more text-regex work (still <15 s).
- **A2 — Cheap prefilter then full score.** Keep only candidates with (technical-title-family OR ≥1 AI-domain skill OR title-gated description hit) → ~15–25k → full scoring. Pros: focuses compute, drops obvious noise early. Cons: a Tier-5 with an unflagged title + thin keywords could be dropped. Use only if runtime pressure appears.
- **A3 — Embedding ANN retrieval (REJECT).** Cosine top-K vs JD. Reintroduces the embedding bias that ranks stuffers/honeypots; needs precompute; unnecessary given cheap scan. ✗
**Recommendation: A1.** Retrieval "signals" are not used to *drop* anyone; the whole pool is scored and ranked. Memory bounded by keeping a compact per-candidate record (drop verbose unused fields after feature extraction) or a top-N heap.

## Stage B — Consistency Gate (honeypot defense)
Goal: guarantee ~0 honeypots in top-100 (Stage-3 DQ at >10%). Use only **logically-impossible** rules (low FP), with tolerance buffers absorbing rounding/gaps/history-truncation. Define `documented_months = Σ non-overlapping role durations`; `elapsed_months = (ref_date − earliest_start)`; `ref_date = 2026-06-19` (or max latest end).

**HARD REJECT (force est_tier=0, exclude from output):**
| ID | Rule | Confidence | Catches |
|---|---|---|---|
| H1 | any skill `proficiency==expert` AND `duration_months==0` | very high | 21 cands (expert@0) |
| H2a | `documented_months > yoe·12 + 14` (worked more months than stated total exp) | very high | sum>yoe set incl. CAND_0001610 |
| H2b | `documented_months > elapsed_months + 14` (worked more than calendar allows → overlap/padding) | very high | overlapping-employment fabrications |
| H3 | any single `role.duration_months > yoe·12 + 6` (one job > whole career) | very high | CAND_0037000 etc. |
| H4 | `yoe·12 > elapsed_months + 30` (claims more experience than time since first job) | high | span<<yoe set incl. CAND_0095619, 0055992, 0071115 |
| H5 | `end_date < start_date` on any role OR `edu.end_year < edu.start_year` | very high | date-corruption honeypots |
| H6 | real-company `role.start_date.year < founding_year − 1` (tenure precedes company) | high (needs table) | the missing ~10 ("8y at 3y-old company") |

**SOFT PENALTY (subtract from fit, do NOT exclude):**
- `2.5y < |elapsed − yoe| span gap (over-direction)` (elapsed >> yoe; could be legit gaps) → small penalty.
- multiple `is_current==true` roles, or `is_current==true` with non-null `end_date` → small penalty (data smell, not impossible).
- claimed yoe vs documented gap in 1.5–2.5y band → small penalty.

**IGNORE (verified normal, NOT honeypot signals):**
- `skill.duration_months > yoe` (29,816 — normal; skills predate/outside jobs).
- first job before college start_year (3,457 — normal).

**consistency_score:** `1.0` if clean; `1 − Σ soft_penalties` (floored ~0.5) if soft; **`hard_reject=True` ⇒ multiply final to 0 AND drop from candidate set.** FP mitigation: every hard rule is a logical impossibility with a buffer; truncated-history seniors fail none (their documented ≤ yoe ≤ elapsed). Defensibility: each rejection carries a human-readable reason string (also feeds nothing into reasoning of accepted candidates).

## Stage C — Career Understanding (most important stage)
Classify each candidate into an **archetype** using title family + title-gated text + skill corroboration + company. **Title family is computed first and gates everything text-based** (defeats the 25k-non-AI-title text-noise trap).

**Role families (from current_title + most-recent titles):**
- `CORE_AI` = ML/AI/Applied ML/Machine Learning/NLP/Recsys/Search Engineer + Senior/Staff/Lead variants + Senior SWE(ML).
- `DS` = Data Scientist, Senior Data Scientist, AI Specialist.
- `RESEARCH` = AI Research Engineer, Senior Applied Scientist  → JD-reject unless production evidence.
- `CV` = Computer Vision Engineer  → JD-reject unless NLP/IR evidence.
- `JUNIOR` = Junior ML Engineer (cap by yoe).
- `ADJACENT` = Data/Senior Data/Analytics/Backend Engineer, Data Analyst, (Senior) Software Engineer, Full Stack/DevOps/Cloud (weak).
- `NONTECH` = HR, Accountant, Mechanical/Civil Engineer, Sales, Marketing, Content, Graphic, Ops, BA, Customer Support, PM, QA → stuffer hosts.

**system_building_evidence ∈ 0..1** — mined ONLY when family ∈ {CORE_AI, DS, ADJACENT, RESEARCH, CV, JUNIOR}: look in `summary` + `career_history[].description` for *(build/ship/deploy/design verb) × (recommendation/ranking/search/retrieval/relevance/personalization/matching/embedding/vector/semantic) [+ production/real-time/at-scale/users/A-B/NDCG/MRR/MAP]*. For NONTECH family this is **forced to 0** regardless of text.

**Archetype decisions:**
- **TRUE_AI_ENGINEER** (tier 5/4): CORE_AI (or DS) + passes consistency + trusted AI-domain coverage (embeddings/vectordb/nlp_ir) + product/ai/neutral company + coherent system_building_evidence.
- **FAKE_AI_ENGINEER / honeypot** (tier 0): CORE_AI title but `hard_reject` → gated out.
- **KEYWORD_STUFFER** (tier 0/1): NONTECH family AND high AI-skill *count* AND low corroboration → strong negative; never ranked.
- **PLAIN_LANGUAGE_TIER5** (tier 4/3): ADJACENT family + product company + strong system_building_evidence + corroborated skills, even with few AI keywords (e.g. CAND_0000001-type, but must be product-co + real substance).
- **ADJACENT_MAYBE** (tier 2/3): technical adjacent with partial relevance.
- **EXCLUDED_DOMAIN**: RESEARCH/CV family with no production/NLP-IR evidence → tier ≤1.
- **IRRELEVANT** (tier 0): NONTECH without stuffing → not ranked.

Outputs: `archetype`, `role_fit∈0..1` (family base), `system_building_evidence∈0..1`, `exclusion_flags{research_only, cv_only, framework_only, no_recent_code}`.

## Stage D — Skill Validation (trust model)
**Per-skill trust:** `trust(s) = base(proficiency) × corroboration(s)` where
`corroboration = f(duration_months) · g(endorsements) · h(assessment_present_and_score)`, each saturating:
- `base`: beginner .25 / intermediate .5 / advanced .8 / expert 1.0 (but expert@0-dur → gate, see B).
- `f(duration)`: ramps 0→1 over ~0–24 months (0 months ⇒ ~0 trust).
- `g(endorsements)`: `log1p`-scaled, capped (so inflated endorsements can't dominate).
- `h(assessment)`: bonus if skill appears in `skill_assessment_scores` with a decent score; absence = neutral (not penalty).
**Believable expertise** = advanced/expert + duration ≥ ~12–24 mo + (endorsements or assessment) corroboration.
**Stuffed skills** (high proficiency, 0–low duration, no endorsements, no assessment) → trust ≈ 0 → contribute nothing; many such on a NONTECH title → stuffer flag.
**Domain coverage (the real feature):** map trusted skills to domains {embeddings, vector_db, nlp_ir, ltr_ranking, llm_finetune, mlops, data_eng, cv(neg)}. **Count DISTINCT trusted domains**, with must-have domains (embeddings + vector_db + nlp_ir) weighted highest. This is robust to keyword-count stuffing (which doesn't produce *coherent corroborated* domains) and rewards genuine depth.

## Stage E — Product-vs-Services Modeling
Only **63 companies** → hand-curated `company_table` (category + founding_year), with `industry` as fallback/secondary.
**Categories:** `services` {Infosys, Wipro, TCS, Cognizant, Capgemini, Accenture, HCL, Tech Mahindra, Mphasis, Mindtree, Genpact, Genpact AI}; `product` {Swiggy, Zomato, Razorpay, CRED, Ola, Meesho, PhonePe, Dream11, Flipkart, Unacademy, Nykaa, PolicyBazaar, BYJU'S, Paytm, Freshworks, upGrad, PharmEasy, InMobi, Zoho, Vedantu, Glance}; `ai_startup` {Sarvam AI, Krutrim, Aganitha, Wysa, Haptik, Verloop.io, Observe.AI, Rephrase.ai, Saarthi.ai, (Niramai, Mad Street Den = CV)}; `bigtech` {Meta, Apple, Adobe, Salesforce}; `fictional` {Wayne Enterprises, Initech, Pied Piper, Acme Corp, Globex Inc, Hooli, Dunder Mifflin, Stark Industries}.
**Career-arc rules (JD-grounded):**
- **Entire career services** (all roles ∈ services) → **strong penalty** (JD explicit reject).
- **Current services BUT prior product/ai in history** → **no/mild penalty** (JD: "that's fine").
- **product / ai_startup present** anywhere relevant → **bonus** (scaled by recency & role relevance).
- **bigtech** → product bonus, but cross-check RESEARCH exclusion (Meta/Apple research roles).
- **fictional** → **neutral** (no bonus/penalty); refine with `industry`: Manufacturing/Paper Products/Conglomerate ⇒ non-tech context (reinforces irrelevance for NONTECH), Software ⇒ neutral-tech.
**Recommendation:** services penalty applies on the **career arc**, not a single current employer; fictional = neutral; `industry` breaks ties when company unmapped.

## Stage F — Behavioral Modifier (bounded)
`final_score = fit_score × M`, `M = clamp(1.0 + Σ adj, 0.6, 1.1)` — capped so behavior can only reorder within similar fit bands, never lift a stuffer/adjacent above a true AI engineer.
**Adjustments (small, additive into M):**
- last_active recency: full credit if ≤90d; linear decay to a floor by ~270d (stale).
- recruiter_response_rate: ≥~0.5 slight +, ≤~0.1 slight −.
- open_to_work_flag false → small −.
- interview_completion_rate low → small −.
- small + for saved_by_recruiters_30d, profile_completeness, github_activity (only if ≥0).
**Saturation/limits:** total upside ≤ +0.10, downside ≤ −0.40 (dormant/unavailable hurt more than availability helps — matches JD "not actually available"). **Sentinels (−1 github/offer) = neutral, never penalized.** Vanity metrics (connection_count, profile_views, search_appearance) excluded.

## Stage G — Final Ranking & Score Composition
`fit_score = Σ_g w_g · group_score_g`, each group normalized 0..1; then gate & modify.
**Feature groups & relative importance (numbers chosen later — see method):**
- **G1 Role/Title fit** — CRITICAL
- **G2 Career substance / system-building evidence** (title-gated) — CRITICAL
- **G3 Company product-vs-services arc** — HIGH
- **G4 Trusted skill-domain coverage** — HIGH
- **G6 Domain-exclusion penalties** (CV-only, research-only, framework-only, no-recent-code) — HIGH (negative)
- **G5 Experience-years fit** (peak 6–8, plateau 5–9, soft decay outside) — MEDIUM
- **G7 Location/logistics** (Noida/Pune/relocate, notice ≤30) — LOW
- **G8 Education/pedigree** — IGNORE/LOW
Ordering: **G1 ≈ G2 > G4 ≈ G3 ≈ G6 > G5 > G7 > G8.** Then `final = fit_score · consistency_soft · M`, with `hard_reject ⇒ 0` and excluded from output.
**How to choose weights (no leaderboard, no labels):**
1. **Hand-label a gold set (~50–60)**: all 15 AI-titled honeypots (target tier 0), ~12 known stuffers (tier 0/1), ~15 strong fits incl. CAND_0000031/0000200/0001930 (tier 5/4), ~10 plain-Tier5/adjacents (tier 3/4), ~10 clear rejects (tier 0/1).
2. **Constraint satisfaction first**: pick weights so ordering invariants hold — every honeypot below every real fit; every stuffer below every adjacent; CAND_0000031-class at the very top; CV/research-only below true-AI.
3. **Coordinate/grid search** maximizing rank-correlation (Spearman / NDCG) against gold tiers.
4. **Ablation + sensitivity**: weights must be robust to ±20% perturbation and each group must measurably help (drop-one test).
5. **Keep round, interpretable numbers** for Stage-5 defensibility. Never tune to a single number.
**est_tier mapping (for self-eval NDCG):** fit bands → tier 5..0 (5=TRUE_AI top, 4=strong/plain-Tier5, 3=relevant adjacent, 2=tangential tech, 1=weak, 0=irrelevant/stuffer/honeypot).

---

# DELIVERABLE 2 — FEATURE INVENTORY
| Feature | Purpose | Expected Importance | Overfit Risk | Honeypot Interaction |
|---|---|---|---|---|
| role_family(current_title) | primary relevance gate | **Critical** | Low | AI-titled honeypots share it → MUST pair w/ consistency |
| recent_title_trend | confirm current trajectory, catch title-chase | High | Low | low |
| system_building_evidence (title-gated text) | find true-AI & plain-Tier5; reject stuffers | **Critical** | Med (text patterns) | text-noise FP if not title-gated |
| trusted_domain_coverage (embeddings/vectordb/nlp_ir) | real depth vs keyword count | High | Low | defeats stuffers; honeypots may still have it → rely on gate |
| must_have_domains_present | embeddings+vectorDB+NLP/IR present & trusted | High | Low | low |
| company_arc (product/services/ai/fictional) | JD product>services intent | High | Low | low |
| entire_career_services_flag | JD explicit reject | High (neg) | Low | low |
| yoe_fit (peak 6–8) | seniority band | Medium | Low | honeypots have impossible yoe → gate handles |
| consistency_hard_reject | honeypot kill-switch | **Critical** (gate) | Low (logical rules) | THE defense |
| consistency_soft_penalty | minor anomalies | Medium | Low | catches near-misses |
| cv_only_flag / research_only_flag | JD exclusions | High (neg) | Low | low |
| framework_only_flag (recent LangChain, no prior ML) | JD exclusion | Medium (neg) | Med (hard to detect) | low |
| no_recent_code_flag (18mo+ non-IC) | JD exclusion | Medium (neg) | Med | low |
| skill_corroboration (endorse×dur×assessment) | trust filter | High | Low | expert@0 → gate |
| ai_skill_count_raw | **bait — diagnostic only** | **Ignore** (never positive) | High | the stuffer trap itself |
| behavioral_modifier (availability) | down-weight unavailable | Medium (×) | Low | low |
| last_active_recency | availability | Medium | Low | low |
| recruiter_response_rate | availability | Low/Med | Low | low |
| location/relocate/notice | logistics nudge | Low | Low | low |
| education_tier / grade | pedigree | **Ignore/Low** | Med (distractor) | low |
| connection_count / profile_views / search_appearance | vanity | **Ignore** | High | low |
| endorsements_raw (alone) | inflatable | **Ignore** (only via corroboration) | High | stuffers inflate |
| github_activity (≥0 only) | OSS signal | Low | Med (−1 sentinel trap) | low |

**Categories:** Critical = {role_family, system_building_evidence, consistency_hard_reject}. High = {trusted_domain_coverage, must_have_domains, company_arc, entire_services_flag, cv/research flags, skill_corroboration}. Medium = {yoe_fit, soft_penalty, framework/no-code flags, behavioral_modifier, last_active}. Low = {response_rate, location/notice, github}. Ignore = {ai_skill_count_raw, vanity metrics, endorsements_alone, education_pedigree}.

---

# DELIVERABLE 3 — ARCHITECTURE ALTERNATIVES
| | **A: Pure Rule/Feature** | **B: Rule + Precomputed Embeddings** | **C: Rule + Learning-to-Rank** |
|---|---|---|---|
| Idea | Gated weighted-feature scorer (this doc) | A + offline local sentence-transformer JD↔profile similarity as ONE low-weight feature within filtered pool | A's features → XGBoost/LightGBM ranker trained on self-labeled gold |
| Pros | transparent, fast, dodges both traps, trivial to defend & reason; no precompute | adds nuance for plain-Tier5 borderline cases | can capture feature interactions; "ML" narrative |
| Cons | weights hand-tuned; may miss subtle text fit | embeddings polluted by 25k text-noise; precompute infra; small gain | **no real labels** → trained on our own rules = circular/overfit; hard to defend; honeypot leakage if features incomplete |
| Complexity | Low | Medium | High |
| Stage-3 risk (repro/honeypot) | **Low** (fast, gate built-in) | Med (precompute reproducibility, model file) | Med-High (model artifact, runtime, gate must still front it) |
| Stage-4 risk (review) | **Low** (clean code, clear methodology) | Low-Med | **High** (reviewers distrust circular self-labeled LTR; git/methodology scrutiny) |
| Stage-5 risk (defense) | **Low** (explain every rule) | Low-Med | High ("what are your labels?" is hard to answer) |
| Expected score | High & stable | High, marginally higher *if* embeddings help borderline | Variable; high variance, overfit downside |

**Choice: Architecture A (pure rule/feature), with B's embedding feature kept as an OPTIONAL, low-weight, precomputed add-on enabled only after A is validated.**
**Defense:** A directly encodes the JD's stated intent, structurally immune to both traps (title-gate + corroboration + consistency gate), runs in seconds, and is fully explainable in the Stage-5 interview — which is exactly what the organizers say they reward. C's fatal flaw is the absence of ground-truth labels (no leaderboard); any LTR is trained on our own heuristics, adding overfit + circularity + a defense liability for near-zero upside. B's embeddings risk re-importing the text-noise/stuffer bias and add reproducibility surface for a marginal gain; demote to optional tie-breaker.

---

# DELIVERABLE 4 — IMPLEMENTATION ROADMAP
| Phase | Purpose | Dependencies | Effort | Validation tests |
|---|---|---|---|---|
| **0 Repo & harness** | git repo, `rank.py` skeleton, `requirements.txt` (pinned), Dockerfile, CLI `--candidates --out`, README, metadata.yaml; **commit iteratively from here** | — | 0.5 d | `python rank.py` runs end-to-end on sample_candidates; validator passes on a dummy 100 |
| **1 Data loader** | stream JSONL → compact record; date parsing; sentinel handling (−1=unknown) | P0 | 0.5 d | re-derive pool stats (titles/countries/yoe) match recon numbers; 100k parses; mem < 1 GB |
| **2 Consistency engine** | implement B (H1–H6 + soft); reason strings | P1, company table (P5a) | 1 d | flags all 15 known AI-titled honeypots; ~70 total; ~0 FP on hand-checked seniors |
| **3 Company table** (P5a) | 63-company category+founding map; industry fallback | P1 | 0.5 d | every dataset company mapped or industry-fallback; spot-check categories |
| **4 Career/title engine** | role families, title-gated text mining, archetype, exclusion flags | P1 | 1.5 d | CAND_0000031→TRUE_AI; CAND_0000001→plain-Tier5; stuffers→stuffer; 25k text-noise non-AI titles NOT promoted |
| **5 Skill trust + domains** | trust model, domain coverage | P1 | 1 d | stuffed expert@0 → trust~0; real fits show embeddings+vectordb+nlp_ir coverage |
| **6 Behavioral modifier** | bounded M∈[0.6,1.1]; sentinel-safe | P1 | 0.5 d | M never lifts adjacent above true-AI; −1 neutral; dormant down-weighted |
| **7 Scoring + weights** | groups G1–G8; gold-set weight calibration | P2,4,5,6, gold set (P8) | 1.5 d | invariants hold on gold; sensitivity ±20% stable |
| **8 Gold set + self-eval** | hand-label ~50–60; NDCG@10/50, MAP, P@10 harness; audits | P1 | 1 d | metrics computed; audits (below) green |
| **9 Reasoning generator** | varied honest templates from real features incl. concerns | P7 | 1 d | passes the 6 Stage-4 checks on 10 random rows; no hallucination; tone matches rank |
| **10 Submission + validate** | CSV writer, strict-decreasing scores, tie-break, run validator | P7,9 | 0.5 d | `validate_submission.py` passes; manual top-100 eyeball |
| **11 Sandbox + repro** | HF Space/Streamlit on ≤100 sample; Docker run; full 100k timing | all | 1 d | runs <5 min/16 GB/CPU/no-net in clean container |
| **12 (optional) Embedding feature** | precompute local emb, add low-weight G2' | P7 validated | 1 d | only if it improves gold NDCG without breaking invariants |

---

# DELIVERABLE 5 — VALIDATION FRAMEWORK (label-free)
**Self-eval harness:** build a **gold set** (~50–60 hand-labeled tiers spanning all archetypes incl. all 15 AI-titled honeypots). Compute our internal NDCG@10/50, MAP, P@10 against gold; track across weight changes. (This is a proxy for the hidden GT, not the GT.)
**Mandatory audits (must all pass before each submission):**
1. **Honeypot audit** — 0 of the ~70 known-impossible IDs in top-100 (target 0; hard ceiling <11). Re-run consistency on top-100; any hard_reject present = bug.
2. **Keyword-stuffer audit** — 0 NONTECH-title candidates in top-100; flag any top-100 candidate whose score leaned on uncorroborated AI skills.
3. **Top-100 inspection** — eyeball every top-100: title, company-arc, yoe, trusted domains, availability; each must have a defensible reason.
4. **Top-10 deep review** — manually confirm each top-10 is a genuine TRUE_AI/plain-Tier5 at product/ai co, consistent, available; confirm ordering matches intuition (NDCG@10 = 50% of score).
5. **Reasoning validation** — sample 10 rows: specific facts ✓, JD connection ✓, honest concerns where gaps ✓, no hallucinated skills ✓, varied ✓, tone-matches-rank ✓.
6. **Sanity checks** — scores strictly decreasing; 100 unique ranks/ids; all ids exist; no NONTECH in top-100; CAND_0000031-class near top; no CV-only/research-only in top-10.
7. **Sensitivity** — perturb weights ±20%; top-10 should be stable (high churn = fragile).
8. **Reproducibility** — fresh clone + Docker → identical CSV within budget.
**Pre-submission checklist:** validator passes · honeypot audit 0 · stuffer audit 0 · top-10 hand-approved · reasoning 6-checks pass · strict-decreasing scores · runs <5min/16GB/CPU/no-net in container · metadata.yaml + README + sandbox live · git history shows real iteration.

---

# DELIVERABLE 6 — MISSING INFORMATION (ranked by expected score impact)
1. **Company founding-year table** (real cos) — unlocks honeypot rule H6 (the missing ~10) → protects Stage-3 DQ. **High impact, low effort** (≤30 companies). *Risk: FP on fictional cos — exclude them.*
2. **Title normalization map** (raw title → role family + seniority) — drives G1 (Critical). **High impact, low effort** (~50 titles, all enumerated).
3. **Product-vs-services company table** — drives G3 + entire-services reject. **High impact, low effort** (63 cos, drafted in Stage E).
4. **Skill→domain ontology** (which skills = embeddings/vectordb/nlp_ir/cv/...) — drives G4 trusted coverage. **High impact, medium effort** (≤133 skills, enumerable).
5. **Career-substance phrase patterns** (build×object×production lexicon) — drives G2 (Critical) + plain-Tier5 detection. **High impact, medium effort**; must be title-gated.
6. **Gold-label set** — needed to calibrate/validate weights without a leaderboard. **High impact, medium effort** (manual).
7. **Hidden GT relevance-tier function** — unknowable; reconstruct from JD. **High impact, not obtainable** → mitigate via gold set + invariants.
8. **CV/speech/robotics & research lexicons** — for exclusion flags G6. **Medium impact, low effort.**
9. **Framework-only / no-recent-code detection heuristics** — JD exclusions, hard to detect reliably. **Low-medium impact, medium effort.**
10. **Tenure/overlap parser** for accurate non-overlapping documented_months — sharpens consistency. **Medium impact, low-medium effort.**

---

# DELIVERABLE 7 — FINAL RECOMMENDATION
1. **Build Architecture A** — a gated, transparent, weighted-feature ranker: stream all 100k → **consistency hard-gate** (honeypots out) → **archetype classification** (title-gated career understanding) → **trusted skill-domain coverage** + **company product-vs-services arc** + **yoe-fit** + **exclusion penalties** → **fit_score** → **bounded behavioral modifier** → top-100 with strict-decreasing scores → feature-grounded reasoning. Keep an optional precomputed-embedding tie-breaker (B) in reserve, added only if it improves the gold-set NDCG without breaking invariants.
2. **Why it wins:** it encodes the JD's literal intent (product-applied AI engineers who shipped ranking/search/recsys, consistent and available), is **structurally immune to both planted traps** (title-gate + corroboration beat keyword/text stuffing; consistency gate beats honeypots), runs in **seconds on CPU** (Stage-3 safe), and is **fully explainable** (Stage-4/5 safe) — precisely the engineer the organizers say they reward. It optimizes the score where it matters: a clean, correctly-ordered top-10.
3. **Biggest risks:** (a) consistency-gate **false positives** removing real seniors with gaps — mitigated by logical-impossibility-only rules + buffers; (b) **weight miscalibration** without true labels — mitigated by gold set + invariants + sensitivity; (c) **plain-Tier5 recall** (missing adjacent gems with thin signals); (d) Stage-4/5 **process** failures (flat git history, weak reasoning) — mitigated by iterative commits + the reasoning generator.
4. **Biggest uncertainties:** exact hidden GT tiering (we approximate); the ~10 uncaught honeypots (need founding table); whether organizers weight DS/adjacent as tier-3 "relevant"; how strict the services penalty should be on mixed careers.
5. **Implement first:** Phase 0 (repo + iterative git) → Phase 1 (loader) → **Phase 2 + 3 (consistency engine + company/founding table)** — the honeypot defense is the highest-leverage, DQ-preventing component and validates immediately against the 15 known IDs. Then Phase 4 (career engine), the single most important scoring stage.
