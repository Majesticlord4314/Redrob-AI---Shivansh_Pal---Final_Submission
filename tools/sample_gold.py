#!/usr/bin/env python3
"""Sample a stratified gold set for measurement and dump readable profiles.

Strata cover every archetype so the eval set exercises the hard cases:
honeypots, keyword stuffers, strong fits, services-only, DS, research, CV,
adjacents (plain-Tier5 candidates), juniors, pure nontech.
Writes:
  gold/gold_pool.jsonl   - full records of sampled candidates
  gold/gold_review.txt   - human-readable profiles for labeling
"""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from redrob import loader, consistency, scoring, roles, skills

DATA = sys.argv[1] if len(sys.argv) > 1 else "../India_runs_data_and_ai_challenge/candidates.jsonl"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gold")
os.makedirs(OUT, exist_ok=True)
random.seed(42)

KNOWN_HONEYPOTS = {"CAND_0039521","CAND_0093547","CAND_0095619","CAND_0001610","CAND_0037000",
    "CAND_0019480","CAND_0055992","CAND_0091534","CAND_0071115","CAND_0010770","CAND_0013536",
    "CAND_0039754","CAND_0093331","CAND_0090900","CAND_0095140"}

buckets = {k: [] for k in [
    "honeypot","strong_core_product","core_services","ds","research","cv",
    "adjacent_product","stuffer","junior","nontech_plain"]}

records = {}
for rec in loader.load(DATA):
    cid = rec["candidate_id"]
    hard, reasons, soft = consistency.check(rec)
    fam = roles.family(rec["title"])
    sk = skills.analyze(rec)
    from redrob import companies
    cur_cat = companies.category(rec["current_company"], rec["current_industry"])
    records[cid] = rec

    if cid in KNOWN_HONEYPOTS:
        buckets["honeypot"].append(cid); continue
    if hard:
        continue
    if fam == "core_ai" and cur_cat in ("product","ai_startup","bigtech") and 5 <= rec["yoe"] <= 9 and sk["must_have_hits"] >= 2:
        buckets["strong_core_product"].append(cid)
    elif fam == "core_ai" and cur_cat == "services":
        buckets["core_services"].append(cid)
    elif fam == "ds":
        buckets["ds"].append(cid)
    elif fam == "research":
        buckets["research"].append(cid)
    elif fam == "cv":
        buckets["cv"].append(cid)
    elif fam == "data_adjacent" and cur_cat in ("product","ai_startup","bigtech") and sk["must_have_hits"] >= 2:
        buckets["adjacent_product"].append(cid)
    elif fam == "junior":
        buckets["junior"].append(cid)
    elif fam == "nontech" and sk["n_ai_skills_raw"] >= 6:
        buckets["stuffer"].append(cid)
    elif fam == "nontech" and sk["n_ai_skills_raw"] == 0:
        buckets["nontech_plain"].append(cid)

QUOTA = {"honeypot":15,"strong_core_product":22,"core_services":10,"ds":10,"research":8,
         "cv":8,"adjacent_product":10,"stuffer":10,"junior":6,"nontech_plain":5}

picked = []
for b, q in QUOTA.items():
    pool = buckets[b]
    random.shuffle(pool)
    chosen = pool[:q]
    for cid in chosen:
        picked.append((cid, b))

with open(os.path.join(OUT, "gold_pool.jsonl"), "w") as f:
    for cid, b in picked:
        r = records[cid]
        f.write(json.dumps({"candidate_id": cid, "bucket": b}) + "\n")

def fmt(rec, bucket):
    L = []
    L.append(f"### {rec['candidate_id']}  [bucket={bucket}]")
    L.append(f"  title={rec['title']} | yoe={rec['yoe']} | {rec['current_company']} ({rec['current_industry']}) | {rec['location']},{rec['country']}")
    L.append(f"  headline: {rec['headline']}")
    for ch in rec["career"]:
        L.append(f"   - {ch['title']} @ {ch['company']} ({ch['industry']}) {ch['duration_months']}m {'CUR' if ch['is_current'] else ''}")
        desc = (ch_desc := next((c.get('description','') for c in []), '')) # placeholder
    # descriptions from raw
    sig = rec["signals"]
    sklist = [f"{s['name']}({s['proficiency'][:3]},{s.get('duration_months',0)}m,e{s.get('endorsements',0)})" for s in rec["skills"]]
    L.append("  skills: " + ", ".join(sklist))
    L.append(f"  signals: last_active={sig.get('last_active_date')} resp={sig.get('recruiter_response_rate')} otw={sig.get('open_to_work_flag')} saved={sig.get('saved_by_recruiters_30d')} gh={sig.get('github_activity_score')} notice={sig.get('notice_period_days')}")
    return "\n".join(L)

# need raw descriptions -> reload raw for picked ids
picked_ids = {cid for cid, _ in picked}
raw = {}
with open(DATA) as f:
    for line in f:
        if not line.strip(): continue
        c = json.loads(line)
        if c["candidate_id"] in picked_ids:
            raw[c["candidate_id"]] = c

with open(os.path.join(OUT, "gold_review.txt"), "w") as f:
    for cid, b in picked:
        rec = records[cid]; c = raw[cid]
        f.write(f"### {cid}  [bucket={b}]\n")
        p = c["profile"]
        f.write(f"  title={p['current_title']} | yoe={p['years_of_experience']} | {p['current_company']} ({p['current_industry']}) | {p['location']},{p['country']}\n")
        f.write(f"  summary: {p.get('summary','')[:400]}\n")
        for ch in c["career_history"]:
            f.write(f"   - {ch['title']} @ {ch['company']} ({ch['industry']}) {ch['duration_months']}m {'CUR' if ch.get('is_current') else ''}\n")
            f.write(f"       {(ch.get('description','') or '')[:280]}\n")
        sklist = [f"{s['name']}({s['proficiency'][:3]},{s.get('duration_months',0)}m,e{s.get('endorsements',0)})" for s in c["skills"]]
        f.write("  skills: " + ", ".join(sklist) + "\n")
        sig = c["redrob_signals"]
        f.write(f"  signals: last_active={sig.get('last_active_date')} resp={sig.get('recruiter_response_rate')} otw={sig.get('open_to_work_flag')} saved={sig.get('saved_by_recruiters_30d')} gh={sig.get('github_activity_score')} notice={sig.get('notice_period_days')} complete={sig.get('profile_completeness_score')}\n")
        f.write("\n")

print(f"picked {len(picked)} candidates across {len(QUOTA)} buckets")
from collections import Counter
print(Counter(b for _, b in picked))
