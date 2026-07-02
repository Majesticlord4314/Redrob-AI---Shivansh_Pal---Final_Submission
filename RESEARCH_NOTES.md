# RESEARCH_NOTES.md — Redrob Ranking Challenge (raw exploration log)

Verbose, skeptical notes from the reconnaissance pass on 2026-06-19. Pairs with the dense `HACKATHON_CONTEXT.md`. Nothing here is built yet; these are observations, hypotheses, and traps.

---
## A. RAW OBSERVATIONS (measured on the full 100,000-row candidates.jsonl)

- File: `candidates.jsonl` 487,259,903 bytes, 100,000 lines, one JSON object/line. Streams in ~2.3s with plain Python — full-file scans are cheap; memory not a concern if streaming.
- `sample_candidates.json` = first 50 records pretty-printed (CAND_0000001..0000050).
- Country: India 75,113 · USA 9,978 · Australia 2,579 · Canada 2,506 · UK 2,472 · Germany 2,469 · Singapore 2,453 · UAE 2,430.
- YOE: min 1.0, median 6.8, max 16.9 (schema allows 0–50, data caps ~17).
- Skills/candidate: 5–23, median 9. Career entries: 1–9 (median ~2–3), dist {1:18508, 2:24186, 3:22126, 4:17131, 5:11469, 6:5196, 7:1218, 8:152, 9:14}.
- Education tier: tier_3 53,220 · tier_4 51,885 · tier_2 27,821 · tier_1 6,852 (candidates can have multiple edu rows). `unknown` allowed by schema.
- Skill proficiency mix: intermediate 470,309 · beginner 379,097 · advanced 109,585 · **expert only 1,311** (expert is rare and meaningful).
- Behavioral medians: recruiter_response_rate 0.44 · profile_completeness 56.8 · interview_completion 0.62 · offer_acceptance −1 (sentinel-dominated) · github_activity −1 (64,637 have none) · notice_period 90d · connection_count 335 · saved_by_recruiters_30d 7. open_to_work true 35,339/100k. last_active spread Dec'25–May'26 (~13k/month) — essentially everyone "active" in last 7 months; the JD's "hasn't logged in 6 months" applies only to a tail.
- Companies: mix of REAL Indian product cos (Swiggy, Zomato, Razorpay, CRED, Ola, Meesho, PhonePe, Dream11, Flipkart, Unacademy, Nykaa, PolicyBazaar, BYJU'S, Wysa, Haptik, Verloop.io, Observe.AI, Sarvam AI, Krutrim), REAL services/consulting (TCS, Infosys, Wipro, Cognizant, Tech Mahindra, Mphasis, Mindtree, Genpact, "Genpact AI"), REAL bigtech (Meta, Apple, Adobe, Salesforce), and FICTIONAL placeholders (Stark Industries, Wayne Enterprises, Hooli, Pied Piper, Initech, Globex Inc, Acme Corp, Dunder Mifflin). 31,155 candidates currently at a consulting/services firm.

## B. TITLE LANDSCAPE (the real signal)
Counts of every relevant title (rest are ~5,800-each generic noise roles):
```
167 ML Engineer            153 AI Research Engineer*   145 Data Scientist
142 Senior SWE (ML)        132 Computer Vision Eng*    131 Junior ML Engineer
130 AI Specialist           26 Recsys Engineer          24 Machine Learning Eng
 23 Applied ML Engineer     23 Search Engineer          21 AI Engineer
 19 Senior Data Scientist   14 NLP Engineer              6 Senior NLP / 6 Senior ML / 6 Staff ML
  4 Senior AI Engineer       4 Senior Applied Scientist* 3 Lead AI Engineer
adjacent: Data Eng 744, Senior Data Eng 687, Analytics Eng 764, Backend Eng 704, Data Analyst 728
```
`*` = JD-named REJECT archetypes (AI Research Engineer & Senior Applied Scientist = "pure research"; Computer Vision Engineer = "CV without NLP/IR"). Do NOT auto-promote these on title alone — read career_history; only keep if they show production ranking/search/NLP deployment.

## C. THE KEYWORD-STUFFER MECHANISM (confirmed)
- Skills are drawn from a fixed vocabulary of **133 distinct names**. The ~55 most common (HTML, Databricks, Redux, Terraform, Angular, Figma, Salesforce CRM, Sales, Accounting, Kafka, Excel...) each appear ~12,000× → roughly uniform random sprinkling across all candidates.
- "AI core" skills split into two frequency tiers:
  - **Tier-A (~5,000 each):** Information Retrieval, LLMs, Recommendation Systems, Semantic Search, Sentence Transformers, Embeddings, Vector Search, Pinecone, FAISS, RAG, Fine-tuning LLMs.
  - **Tier-B (~1,400 each):** QLoRA, Weaviate, Milvus, Learning to Rank, BM25, PyTorch, TensorFlow, Qdrant, PEFT, LoRA, NLP, Elasticsearch, OpenSearch.
- Per-candidate count of AI-relevant skills is **bimodal**: 75,251 have 0; then a deliberate cluster — 6:1,186 / 7:1,268 / 8:1,180 / 9:1,133 / 10:440 / 11:32 / 12:3. The 6–12 cluster (~6,000) = **keyword stuffers**, and most wear NON-AI titles.
- **`sample_submission.csv` proves it**: its top-100 are HR Managers/Accountants/Content Writers/Graphic Designers/Mechanical Engineers each described as having "8–9 AI core skills". Real AI/ML engineers appear LOWER with FEWER listed AI skills (AI Engineer w/ 3, ML Engineer w/ 3–4, Data Scientist w/ 3). Its `score` column is a fake linear ramp `1.0 − 0.008·(rank−1)` carrying zero information. → It is a planted "wrong answer". Anyone who copies its philosophy loses.
- **Implication:** number-of-AI-skills is at best neutral and on a non-AI title is a *negative* (stuffing). Trust skills only when corroborated by `endorsements`, `duration_months`, `skill_assessment_scores`, AND a matching title/career.

## D. HONEYPOT DEEP DIVE (the Stage-3 kill switch)
Spec: ~80 honeypots, "subtly impossible", forced to tier 0; **>10% in top 100 = disqualified**. Examples given: "8 yrs experience at a company founded 3 yrs ago"; "'expert' in 10 skills with 0 years used".

Signatures I measured (clean, low-false-positive; union ≈ **70** candidates):
| signature | count | meaning |
|---|---|---|
| expert proficiency w/ `duration_months==0` | 21 cands (84 skill instances, 3–5 each) | matches spec example exactly |
| Σ(career duration_months) > yoe·12 + 14 | 24 | worked more months than the career allows |
| any single role longer than total yoe (+6mo) | 21 | one job > whole career (subset of above) |
| earliest-start→today span > yoe + 2.5y | 3 | dates imply longer career than claimed |
| earliest-start→today span < yoe − 2.5y | 25 | claims 15–16 yrs but dates show 4–8 (inflated seniority) |

Noisy signatures I tried and REJECTED as honeypot detectors (too many normal hits): `skill duration > yoe` (29,816 — normal; people use skills before/outside jobs) and `first job before college start_year` (3,457 — normal). Don't use these as DQ rules.

**The dangerous subset: 15 honeypots wear AI/data titles.** Verbatim examples (these will sink a title+skill matcher):
- CAND_0039521 — Search Engineer @ Salesforce, claims 3.0y but career=59mo; skills RAG/Weaviate/Qdrant/Sentence Transformers/Embeddings/Semantic Search/BM25 (perfect). MOST dangerous.
- CAND_0093547 — Senior ML Engineer @ PhonePe, 2.9y but 74mo career + a 43mo single role; RAG/Milvus/FAISS/LTR/Weaviate/IR.
- CAND_0095619 — NLP Engineer @ Nykaa, claims 15.6y but ONE 50mo role; Pinecone/LTR/NLP/Weaviate/IR/BM25/Sentence Transformers/Elasticsearch.
- CAND_0001610 — ML Engineer @ Dream11, 3.0y vs 61mo career; Pinecone/Milvus/Sentence Transformers/IR/NLP/FAISS.
- CAND_0037000 — Search Engineer @ Unacademy, 2.7y vs 75mo + 48mo role; Embeddings/Semantic Search/FAISS/Pinecone/BM25/Sentence Transformers.
- CAND_0019480 — NLP Engineer @ Meesho, 2.8y vs 87mo career.
- CAND_0055992 — AI Engineer @ CRED, claims 16.9y, span 6.7y.
- CAND_0091534 — AI Engineer @ Flipkart, 16.6y, span 7.3y.
- CAND_0071115 — Recsys Engineer @ Meta, 16.5y, span 5.7y.
- CAND_0010770 — Recsys Engineer @ Aganitha, 15.2y, span 7.2y.
- CAND_0013536 — Applied ML Engineer @ Haptik, 14.1y, span 4.7y; perfect vector skills.
- CAND_0039754 — Senior Applied Scientist @ Meta, 16.2y, span 8.1y.
- CAND_0093331 — NLP Engineer @ Genpact AI, 16.1y, span 7.2y.
- CAND_0090900 — Senior Data Engineer @ PolicyBazaar, claims 11.7y but ONE 9mo role.
- CAND_0095140 — Backend Engineer @ Razorpay, 5.0y, expert@0-months trigger; IR/Milvus/Vector Search.

**Detector that catches all of them with ~0 false positives:** require internal consistency — `yoe ≈ career_span ≈ Σ non-overlapping durations` (tolerance ~±2.5y / +14mo) AND no `expert`@`duration_months==0`. A ranker that enforces this naturally pushes honeypots out of the top 100. Spec literally says "you don't need to special-case them" — but we will compute the check defensively because the DQ is binary and brutal.

**Still missing ~10 honeypots** (found ~70 of stated ~80). Untested patterns to revisit: (1) tenure at a REAL young company exceeding its founding age — would need a company-founding lookup table (Sarvam AI ~2023, Krutrim ~2023, CRED 2018, Meesho 2015, etc.); the "8yrs at 3yr-old company" example points here. (2) education timeline contradictions (degree end_year after a senior role start; impossibly fast promotions). (3) overlapping non-current employment. Build a founding-year table for the ~30 real companies before finalizing if we want to push the catch rate up — but beware false positives on fictional companies (no founding date).

## E. GENUINE FITS (the answer pool)
- ~465 candidates hold a strong AI title; ~310 pass a "genuinely strong" gate (strong AI title + product company + 4–10y + ≥2 real AI skills + consistency). Top-100 should be drawn mostly from these ~310 plus the strongest "plain-language Tier 5" adjacents.
- Exemplar near-perfect: **CAND_0000031** — Recommendation Systems Engineer @ Swiggy, 6.0y, skills Embeddings/FAISS/IR/Pinecone/Sentence Transformers, recruiter_response 0.91, active 2026-05-24. Hits: recsys at product co, vector retrieval, ideal yoe, highly available. This is what rank-1 looks like.
- Other strong samples: CAND_0000200 (ML Eng @ Aganitha, RAG/FAISS/Vector Search), CAND_0001930 (Senior SWE(ML) @ Dream11, Embeddings/Milvus/NLP), CAND_0000981 & 0001131 (ML Eng @ Wysa).

## F. "PLAIN-LANGUAGE TIER 5" (the inverse of stuffers)
JD: a Tier-5 candidate may never write "RAG"/"Pinecone" but their **career_history description** says they built a recommendation/search/ranking system at a product company → they're a fit. Must mine free text in `summary` + `career_history[].description`. CAND_0000001 is the archetype of an adjacent honest profile: Backend/data engineer at Mindtree, advanced Milvus (35mo), built streaming pipelines + worked with DS teams, summary openly says "building competence on the ML side / transitioning toward AI/ML". Reads as a genuine adjacency, NOT a stuffer (its AI claims are backed by duration/endorsements and an honest narrative). The scoring should reward narrative substance, not keyword presence.

## G. SUSPICIOUS / SKEPTICAL FINDINGS
- The `tier` field on education ("internal tiering for institution prestige") is suspicious bait — the JD never asks for pedigree and even disparages Google/Meta-comfort-seekers. Weight pedigree near-zero; possibly a distractor field.
- `github_activity_score = -1` for 64,637 candidates is a **sentinel for "no GitHub linked," not a low score.** Treating −1 as a bad score would wrongly tank 65% of the pool. Same for `offer_acceptance_rate = -1` (no offer history). Handle sentinels explicitly.
- `connection_count`, `profile_views_received_30d`, `search_appearance_30d` are vanity metrics — easy to over-weight, weakly tied to hireability. Likely included partly as distractor signals.
- `endorsements` can be high on stuffed skills → not trustworthy alone; combine with `duration_months` + `skill_assessment_scores`.
- Fictional companies (Stark/Wayne/Hooli/Pied Piper/Initech/Globex/Acme/Dunder Mifflin) — should they count as "product" or "services"? Ambiguous; treat as neutral (neither services-penalty nor product-bonus) unless the role/industry says otherwise.
- "Genpact AI" is a services firm wearing an AI hat — treat as services for the consulting penalty.
- Scores in submission must be non-increasing AND ties broken by candidate_id ascending (the validator enforces tie-break ordering, lines 136–144). Safer to emit strictly decreasing scores to avoid any tie-break edge cases.

## H. EVALUATION REVERSE-ENGINEERING NOTES
- `composite = 0.50·NDCG@10 + 0.30·NDCG@50 + 0.15·MAP + 0.05·P@10`. 80% of weight is on NDCG (order- & position-sensitive, log discount). → Ordering the **top 10 correctly** is the single highest-leverage thing; getting a clearly-relevant candidate into rank 1–3 over rank 8–10 matters a lot.
- MAP (15%) rewards relevant items appearing early across all relevance levels; P@10 (5%) just needs 10 tier-3+ in the top 10.
- Recall barely matters (only top-100 submitted; metrics cap at @10/@50). → **Be aggressive: a small, clean, high-precision top set wins.** Padding ranks 51–100 with "maybes" costs little but also gains little; still fill them with the next-best real fits, never honeypots/stuffers.
- No public split / no live leaderboard → cannot overfit to feedback; must reason about the GT, not fit to it. The GT relevance-tier function is hidden; our job is to reconstruct the organizers' notion of fit from the JD.

## I. STAGE-SURVIVAL NOTES
- A submission can score well at Stage 2 yet die at: Stage 3 (honeypot>10% OR non-reproducible/over-budget code OR missing repo), Stage 4 (templated/hallucinated reasoning, flat single-commit git history, code = just LLM API calls), Stage 5 (can't defend architecture).
- → Practical musts for the build phase: real **iterative git history**; **one-command reproduce** (`python rank.py --candidates ... --out ...`) under 5min/16GB/CPU/no-net; pinned `requirements.txt`; `submission_metadata.yaml` in repo; a **sandbox link** (HF Spaces/Streamlit/Replit/Colab/Docker/Binder running a ≤100-candidate sample); honest AI-tools declaration; ≤200-word methodology that matches the code; and a human who can explain every component.

## J. STRATEGY BRAINSTORM (analysis only — not chosen yet)
- **Pure embedding cosine (JD vs profile):** fast, simple — but ranks stuffers + AI-titled honeypots high → fails traps & Stage 3. ✗
- **AI-skill keyword count:** = sample_submission = guaranteed fail. ✗
- **Pure LLM re-rank per candidate:** best quality in theory but violates compute/no-network; even local LLM can't do 100k in 5min CPU. ✗ for ranking step (could be used offline to *label* a small set, risky).
- **Learning-to-rank (XGBoost):** good IF we had labels; we don't (no leaderboard/GT). Could self-label via rules then fit — circular, overfit risk, hard to defend. Use at most as a re-ranker over rule features. ⚠
- **Rule-based / weighted-feature ranker (title + career-substance + product-vs-services + yoe-fit + corroborated-skills + NLP-not-CV + location) × bounded behavioral availability modifier, gated by a consistency/honeypot filter:** transparent, fast, defendable, dodges both traps, easy reasoning generation. Strongest backbone. ✓ (recommended)
- **Hybrid: rule backbone + optional local sentence-transformer embedding similarity (precomputed offline) as one feature among many, restricted to the filtered pool:** adds nuance for plain-language Tier-5 detection without letting embeddings dominate. ✓ if time allows.
- **Anomaly/consistency detection as a standalone layer:** essential as a *gate* (honeypots), not as the primary ranker.
Risk axes per strategy — overfit risk highest for LTR/embedding-tuned; honeypot risk highest for embedding/keyword; runtime risk highest for LLM/embedding-at-rank-time (mitigate by precompute).

## K. IDEAL vs REJECT PROFILE (structured)
**IDEAL (→ tier 5/4):** current/recent title in {ML/AI/Applied ML/Machine Learning/NLP/Recsys/Search Engineer, Senior SWE(ML)}; OR adjacent (Data/Backend Eng) whose career_history describes building ranking/search/recsys/retrieval; 5–9y (peak 6–8), ≥4y applied ML; at PRODUCT companies (Swiggy/Flipkart/CRED/PhonePe/Dream11/Razorpay/Meesho/Nykaa/etc.); skills incl. embeddings + a vector DB/hybrid search, corroborated by duration/endorsement/assessment; NLP/IR (not CV/speech-only); evaluation awareness a plus; consistent profile (passes honeypot gate); available (recent last_active, decent response_rate, open_to_work); in/near Noida-Pune or willing to relocate a slight plus; notice ≤30d a slight plus.
**REJECT (→ tier 0–1):** non-AI title regardless of skill list (stuffer); AI Research Engineer / Senior Applied Scientist / academic with no production; Computer Vision/Speech/Robotics without NLP/IR; entire career at consulting/services; title-chaser (≤~1.5y tenures climbing titles); only-recent LangChain/OpenAI wrapper work with no prior ML; 18mo+ no hands-on code; ANY honeypot/inconsistent profile (hard zero); unavailable (stale + low response + not open).

## L. TODO BEFORE BUILDING
1. Build company-founding-year table for ~30 real firms → catch remaining ~10 honeypots (tenure > company age). Watch false positives on fictional companies.
2. Define product-vs-services company list (and decide fictional-company handling = neutral).
3. Mine `career_history[].description` / `summary` for retrieval/ranking/recsys/search/eval keywords to find plain-language Tier-5s and to validate AI-titled candidates.
4. Decide sentinel handling (−1 github/offer = unknown=neutral).
5. Decide consistency tolerances (start ±2.5y span, +14mo Σduration, expert@0mo).
6. Confirm score emission strictly decreasing; reasoning generator with varied honest templates pulling real field values.
7. Set up repo with iterative commits + one-command reproduce + sandbox.
