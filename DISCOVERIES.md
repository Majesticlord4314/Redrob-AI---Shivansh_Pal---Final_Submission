# DISCOVERIES.md — findings from actual ranking outputs

## V1 run (2026-06-19, 10.1s, 100k candidates)

### D1 — Top-100 is 100% core_ai/ds; plain-Tier5 adjacents never surface
- **Observation:** top-100 = 99 core_ai + 1 ds. Zero data_adjacent / Backend / Data Engineer despite the JD emphasizing "plain-language Tier 5" adjacents.
- **Hypothesis:** there are ~465 core_ai-titled candidates (~310 strong); they more than fill 100 slots, and ROLE_BASE gap (1.0 vs 0.45) means an adjacent can't out-score a core_ai. This is *probably correct behavior* for Stage-2 precision (core_ai at product cos with full domain coverage ARE the best fits), but risks missing a genuinely superb adjacent and is a Stage-5 talking point.
- **Proposed fix:** none for now. Later: spot-check the top ~30 data_adjacent candidates by final score to confirm none out-class our rank ~80–100 core_ai. If some do, let substance lift adjacents higher.
- **Confidence:** medium that current behavior is fine for score; high that it needs a defensibility note.
- **CONFIRMED (spot-check):** best data_adjacent fit = **0.603**; lowest core_ai in top-100 fit = **0.887**. Large clean gap → adjacents are nowhere near the cutoff; title-gate is safe for this dataset. Side-effect: top adjacents have g_sub≈0.1, so substance text mining does NOT actually detect plain-Tier5 signal — it just tracks "is core_ai" (which already has rich text). Reinforces D3.

### D2 — Top-10 scores are nearly tied → NDCG@10 ordering is partly arbitrary (BIGGEST ISSUE)
- **Observation:** top-100 final spread is only 0.127; **top-10 has just 7 unique values** (ties at 6/7 and 8/9/10, broken by candidate_id). NDCG@10 is 50% of the score and is order-sensitive.
- **Hypothesis:** within the strong pool, role/substance/domains/yoe are all saturated, so almost nothing differentiates the top — ordering is left to tiny company/behavioral deltas + alphabetical tie-break. We are likely leaving NDCG@10 points on the table.
- **Proposed fix (next iteration):** add finer, continuous quality signals that separate the very best: domain *depth* (count + quality beyond the 3 must-haves), skill *assessment scores*, endorsement depth, eval-rigor text signal, role precision (Recsys/Search/NLP Engineer at a product co + recsys/search skills = exact-match bonus). Goal: monotonic, well-separated top-10.
- **Confidence:** high that this is the highest-leverage improvement.

### D3 — Substance (G2, 22% weight) is saturated and non-discriminating
- **Observation:** g_sub = 1.00 for 95/100 of the top. The career-text keyword mining maxes out for essentially all core_ai engineers (descriptions are keyword-rich for real AI roles too).
- **Hypothesis:** as built, substance only separates *gated families with text* from *those without* — but every core_ai has rich text, so it's a near-constant in the top and wastes 22% of weight on ordering. It still does useful work for plain-Tier5 detection among adjacents (D1), just not among core_ai.
- **Proposed fix:** either (a) raise the bar so substance is a genuine 0..1 gradient (require build-verb+object+rigor combos, normalize differently), or (b) reduce its weight for core_ai and repurpose freed weight toward D2's discriminators. Lean (b)+(a).
- **Confidence:** high.

### D4 — Consistency gate rejected exactly 70; 0 reached top-100
- **Observation:** 70 hard-rejected (matches recon's ~70 clean-signature count). All 15 known AI-titled honeypots excluded. Honeypot rate in top-100 = 0%.
- **Hypothesis:** gate works as intended; Stage-3 DQ risk currently ~0. Remaining ~10 honeypots (founding-year pattern) are likely non-AI-titled and wouldn't reach top-100 anyway.
- **Proposed fix:** none now. H6 (founding-year) deferred; revisit only if a top-100 candidate looks suspicious.
- **Confidence:** high.

### D5 — CV-domain skills are common among top core_ai (random skill assignment)
- **Observation:** many top picks list `cv` in trusted domains (e.g. ranks 4,6,8 at CV/normal cos). Not penalized because they also have nlp_ir (not cv_only).
- **Hypothesis:** skills are randomly sprinkled, so CV skills appear on NLP engineers harmlessly. JD dislikes *CV-primary* people; these aren't. Minor.
- **Proposed fix:** optional tiny down-weight if cv present AND nlp_ir weak. Low priority.
- **Confidence:** medium; low impact.

### D6 — "Scorable (fit>0) = 99,930" is a meaningless number
- **Observation:** almost everyone gets fit>0 because company/yoe/location groups are nonzero even for nontech (role=0).
- **Hypothesis:** harmless — the huge role-weight gap keeps nontech far below the top — but it inflates the candidate list and the "scorable" log line is misleading.
- **Proposed fix:** for clarity/perf, could require role_base>0 or a min fit floor to enter the ranked set. Cosmetic; defer.
- **Confidence:** high (harmless).

### D7 — Ordering in the top is currently driven by company-arc + behavioral, not depth-of-fit
- **Observation:** within top-100, g_role/g_sub/g_dom/g_yoe medians are all ~1.00; only g_comp (0.55–0.90) and M (1.00–1.10) vary materially.
- **Hypothesis:** so the *de facto* ranking key right now is "which good company + how available," not "how deep an AI engineer." That may be acceptable but isn't clearly aligned with the hidden tiering; depth should matter more at the top (ties to D2/D3).
- **Proposed fix:** introduce depth discriminators (D2) so fit, not just company/availability, orders the top.
- **Confidence:** high.

### D8 — career_history DESCRIPTIONS are templated boilerplate, randomly assigned (MAJOR)
- **Observation:** while reading 104 profiles, the same description paragraphs recur verbatim across dozens of candidates and unrelated titles (e.g. "Developed a semantic search feature for an internal knowledge base of ~500K documents. Used sentence-transformers…", "My main project was a churn prediction model…", "Built computer vision models for our product's image moderation feature…"). A Recommendation Systems Engineer and an HR-adjacent role can carry the identical paragraph.
- **Hypothesis:** descriptions are drawn from a small fixed pool independent of the candidate → V1's `substance` text-mining (22% weight) is measuring **noise**, which is exactly why it saturated (D3). Free-text from descriptions is worthless as a quality signal and dangerous if trusted.
- **Proposed fix:** STOP mining career descriptions. Drop/repurpose the substance feature. Use the `summary` archetype instead (D9).
- **Confidence:** very high.

### D9 — `summary` is templated into ~4 quality ARCHETYPES that DO correlate with fit (MAJOR, actionable)
- **Observation:** summaries cluster into 4 generator templates: (1) "Senior AI engineer … focus on search, retrieval, and ranking … rebuilt the candidate-JD matching pipeline … 0.72→0.91 NDCG@10" [ELITE — mirrors the JD]; (2) "ML engineer … building ML-powered features in production … NLP, recommendation systems" [STRONG]; (3) "Data scientist / ML engineer … strongest at modeling and analysis … lighter on deep-learning" [MODERATE, DS-leaning]; (4) "Software / data professional … data pipelines … want to do more ML" [ADJACENT]. Strong fits get 1/2; DS-leaning get 3; transitioning adjacents get 4.
- **Also:** the summary states a self-reported years number that, for honeypots, contradicts profile `years_of_experience` (e.g. yoe=16.5 but summary "5.8 years") — the summary number ≈ the *real* (lower) experience. Corroborates H4; could add as a redundant honeypot check.
- **Hypothesis:** the generator's intended quality tier is encoded (or strongly correlated) in the summary archetype — and it's INDEPENDENT of V1's features (title/skills/company), so it's a good anchor for gold labels AND a strong new ranking feature.
- **Proposed fix:** add `summary_archetype` as a scoring feature (V2). Use it (gated by consistency) to order the top — honeypots use archetype 1/2 too, so consistency MUST precede it.
- **Confidence:** high. Caveat: it's a templated proxy, not proof of skill; weight it but don't let it dominate consistency/title.

### D10 — skills remain partly random; corroboration (duration/endorsement/assessment) is the only filter
- **Observation:** even strong candidates carry irrelevant skills (Accounting, Photoshop, Vue.js) alongside relevant ones; relevant skills vary in duration/endorsement.
- **Hypothesis:** raw skill presence stays noisy; the trust model (V1 already) is the right call. Keep trusted-domain coverage; don't count raw skills.
- **Confidence:** high (validates V1 D-stage design).

---
## Next action (per build philosophy: analyze before adding sophistication)
Priority order by impact/cost:
1. **D2/D3/D7 — top-end differentiation** (HIGH impact / LOW–MED cost) → implement next: continuous depth + role-precision + assessment-score signals; rebalance weight off saturated substance.
2. **D1 — adjacent spot-check** (MED impact / LOW cost) → audit top adjacents, decide if any belong.
3. Defer: H6 founding-year, CV down-weight, embeddings, reasoning gen, weight tuning, gold set.

---
## V2 run (2026-06-19)

### D11 — embeddings (TF-IDF) and ML (XGBoost LTR) do NOT beat the rule scorer
- **Observation:** TF-IDF(candidate text vs JD) Spearman with gold tier = 0.245; adding it to V2 → optimal blend weight 0. XGBoost LTR 5-fold OOF gold composite 0.9752 < V2 rules 0.9897.
- **Hypothesis:** confirmed — (a) the only semantic signal (summary archetype) is captured directly and better; TF-IDF drowns in templated-description noise (D8). (b) No real labels → ML overfits/underperforms and is indefensible at Stage 5.
- **Decision:** keep the rule scorer; no embeddings, no LTR. Revisit only if a future signal can't be expressed as a rule.
- **Confidence:** high (measured).

### D12 — archetype feature resolved the top-ordering problem (D2/D3/D7 closed)
- **Observation:** V2 (archetype + continuous curves, substance dropped) lifted gold composite 0.9534→0.9897, NDCG@10 0.964→1.000, Spearman 0.942→0.988; top-10 now 10 unique scores (was 7); senior_search archetype correctly tops the full-pool ranking.
- **Status:** D2/D3/D7/D8 addressed. Honeypot defense (D4) and title-gate (D1) unchanged and still clean (0 honeypots, 99 core_ai + 1 ds in top-100).
- **Confidence:** high.

### Open / deferred (low priority)
- Gold/scorer share the archetype signal (partial circularity) — acceptable; archetype is generator-intended. Could add a few hand-held-out labels later.
- Runtime 43s (fine). Company table has full top-100 coverage via industry fallback (verified: 0 unknown/fictional/nontech companies in top-100).
- Still deferred: H6 founding-year honeypots, reasoning generation, weight sensitivity sweep.

---
## V5 run (2026-06-19)

### D13 — founding-year honeypots: "start before founding" is NOISE; "tenure > company age" is the real signal
- **Observation:** flagging roles whose start_date precedes the company's founding flags **93 candidates** spread randomly across all titles (.NET, QA, Frontend, ML, DS…) — e.g. hundreds "started at CRED in 2016" (founded 2018). The generator assigned start dates WITHOUT respecting founding years → pure noise. Using it as a gate would have wrongly rejected ~91 legitimate candidates (incl. real AI engineers).
- **But:** flagging roles whose `duration_months` EXCEEDS the company's age (an absolute impossibility — you can't work somewhere longer than it has existed) flags exactly **8 NEW candidates**, all with ~49–54 months tenure at Sarvam AI / Krutrim (both founded 2023, ~36 months old), all AI-titled (CV/Applied ML/AI Specialist/DS/Senior SWE-ML). This is the spec's "8 yrs at a company founded 3 yrs ago" pattern.
- **Hypothesis:** the ~10 honeypots we were missing are this duration-vs-age class. 70 (H1–H5) + 8 (H6) = **78 ≈ stated ~80.**
- **Fix (shipped):** H6 = `duration_months > company_age + 12mo buffer` for real companies (founding table in `companies.py`). Did NOT ship "start before founding". Buffer absorbs founding-year uncertainty; the rule only fires on absolute impossibilities → 0 false-positive risk.
- **Verification:** 0 gold candidates affected; gold composite unchanged (0.9897); no regression; reproducible.
- **Confidence:** very high. Lesson: the obvious reading of the spec's founding hint (start-date) backfires; the defensible reading is tenure-vs-age.
