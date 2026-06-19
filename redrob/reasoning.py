"""Feature-grounded reasoning generation for the submission `reasoning` column.

Designed against the Stage-4 manual-review checks (HACKATHON_CONTEXT.md §13):
- references SPECIFIC profile facts (title, yoe, company, named skills, signal values)
- connects to SPECIFIC JD requirements (retrieval/ranking/recsys, product>services, yoe band)
- ACKNOWLEDGES concerns honestly where present
- NO hallucination: every fact is read from the record; skills mentioned are only
  ones actually in the profile and trusted
- VARIED: phrasing is selected deterministically per candidate_id (reproducible)
- TONE matches RANK: top ranks lead with strengths + minor caveat; lower ranks are
  more qualified and let the concern explain the lower placement
"""
import hashlib
from datetime import date
from . import companies

REF = date(2026, 6, 19)

DOM_PHRASE = {
    "embeddings": "embeddings",
    "vector_db": "vector search",
    "nlp_ir": "retrieval/NLP",
    "ranking": "ranking & recsys",
    "llm": "LLM fine-tuning",
}
DOM_ORDER = ["nlp_ir", "ranking", "embeddings", "vector_db", "llm"]

ARCH_FLAVOR = {
    "senior_search": "self-describes a search/retrieval/ranking focus",
    "ml_prod": "ships ML-powered product features",
    "ds": "leans modeling/analytics over systems",
    "data": "data/infra background moving toward ML",
    "other": "",
}


def _pick(options, cid, salt=0):
    # stable across processes (Python's built-in hash() is per-process randomized)
    h = int(hashlib.md5(f"{cid}:{salt}".encode()).hexdigest()[:8], 16)
    return options[h % len(options)]


def _months_since(d):
    try:
        return (REF - date.fromisoformat(d)).days // 30
    except Exception:
        return None


def _dom_phrase(domains):
    ordered = [DOM_PHRASE[d] for d in DOM_ORDER if d in domains]
    ordered = ordered[:3]
    if not ordered:
        return ""
    if len(ordered) == 1:
        return ordered[0]
    return ", ".join(ordered[:-1]) + " and " + ordered[-1]


def _skill_list(trusted_relevant, cid):
    names = [nm for (nm, _prof, _dom) in trusted_relevant][:4]
    if not names:
        return ""
    # vary count 2-3 deterministically
    k = 2 + (_pick([0, 1], cid, 7))
    return ", ".join(names[:max(2, min(k, len(names)))])


def _concerns(rec, sc):
    """Return list of (severity, text). severity: 1 mild .. 3 strong."""
    out = []
    s = rec["signals"]
    rr = s.get("recruiter_response_rate")
    if isinstance(rr, (int, float)) and rr <= 0.20:
        out.append((2, f"recruiter response rate is low ({rr:.0%})"))
    mo = _months_since(s.get("last_active_date"))
    if mo is not None and mo >= 5:
        out.append((2, f"last active ~{mo} months ago"))
    if s.get("open_to_work_flag") is False:
        out.append((1, "not flagged open-to-work"))
    npd = s.get("notice_period_days")
    if isinstance(npd, (int, float)) and npd >= 90:
        out.append((1, f"{int(npd)}-day notice period"))

    mh = sc["must_have_hits"]
    if mh < 3:
        have = set(sc["trusted_domains"])
        miss = [DOM_PHRASE[d] for d in ("embeddings", "vector_db", "nlp_ir") if d not in have]
        if miss:
            out.append((2, f"no verified {' or '.join(miss)} skill"))
    y = rec["yoe"]
    if y < 5:
        out.append((1, f"slightly junior at {y:.1f}y"))
    elif y > 9:
        out.append((1, f"toward the senior end at {y:.0f}y"))

    cur_cat = companies.category(rec["current_company"], rec["current_industry"])
    if cur_cat == "services":
        out.append((2, "currently at a services firm (product exposure is historical)"))
    elif sc["g_comp"] <= 0.55:
        out.append((1, "product-company exposure is mostly in past roles"))
    return out


def generate(rec, sc, rank):
    cid = rec["candidate_id"]
    title = rec["title"]
    company = rec["current_company"]
    y = rec["yoe"]
    domains = set(sc["trusted_domains"])
    skills = _skill_list(sc["trusted_relevant"], cid)
    domp = _dom_phrase(domains)
    flavor = ARCH_FLAVOR.get(sc["archetype"], "")

    leads = [
        f"{title} at {company}, {y:.0f} yrs' experience",
        f"{y:.1f}-year {title} currently at {company}",
        f"{company} {title} with ~{y:.0f} years in applied ML",
        f"{title} ({y:.1f}y) at {company}",
    ]
    lead = _pick(leads, cid, 1)

    if skills and domp:
        strengths = [
            f"brings verified {domp} depth ({skills})",
            f"hands-on with {skills}, covering {domp}",
            f"maps to the JD's retrieval/ranking core via {skills}",
            f"strong on {domp}; trusted skills include {skills}",
        ]
    elif domp:
        strengths = [f"covers {domp}", f"shows {domp} depth"]
    else:
        strengths = ["adjacent technical profile with partial overlap"]
    strength = _pick(strengths, cid, 2)
    if flavor and (_pick([0, 1], cid, 5) == 0):
        strength = strength + f"; {flavor}"

    concerns = _concerns(rec, sc)
    concerns.sort(reverse=True)  # strongest first

    # tone by rank band
    if rank <= 15:
        body = f"{lead}; {strength}."
        if concerns:
            body += f" Minor concern: {concerns[0][1]}."
    elif rank <= 50:
        body = f"{lead}; {strength}."
        if concerns:
            body += f" Tradeoff: {concerns[0][1]}."
    else:
        if concerns:
            c = "; ".join(t for _sev, t in concerns[:2])
            body = f"{lead}; solid fit ({strength}), placed here due to {c}."
        else:
            body = f"{lead}; {strength} — a borderline top-100 inclusion."
    return body
