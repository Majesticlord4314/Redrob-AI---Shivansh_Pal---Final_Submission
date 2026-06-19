"""Fit scoring (G1..G7) + title-gated career-substance mining.

V1 weights are sensible defaults, NOT tuned. The point of V1 is to produce a
believable top-100 to inspect, then evolve. See ARCHITECTURE.md Stage C/G.
"""
import re
from . import roles, companies, skills

# title-gated career substance: (build verb) x (relevant system object) [+ rigor]
_VERB = r"(built|build|building|ship|shipped|deploy|deployed|design|designed|develop|developed|implement|implemented|own|owned|led|architect)"
_OBJ = r"(recommend\w*|ranking|search|retrieval|relevance|personaliz\w*|matching|embedding|vector|semantic|nearest neighbor|recsys)"
_BUILD_RE = re.compile(_VERB + r"[^.]{0,60}?" + _OBJ, re.I)
_OBJ_RE = re.compile(_OBJ, re.I)
_RIGOR_RE = re.compile(r"(ndcg|mrr|\bmap\b|precision|recall|a/b|offline|online|at scale|real-time|production|latency)", re.I)

WEIGHTS = {
    "role": 0.30,
    "substance": 0.22,
    "domains": 0.20,
    "company": 0.13,
    "yoe": 0.10,
    "location": 0.05,
}

INDIA_HUBS = ("pune", "noida", "hyderabad", "delhi", "mumbai", "gurgaon", "gurugram",
              "bangalore", "bengaluru", "ncr", "chennai", "kolkata")


def yoe_fit(y):
    if 6 <= y <= 8:
        return 1.0
    if 5 <= y < 9:
        return 0.85
    if 4 <= y < 10:
        return 0.70
    if 3 <= y < 11:
        return 0.50
    if y < 3:
        return 0.30
    return 0.45  # >11


def substance(rec, fam):
    """0..1 evidence of building relevant systems. Title-gated."""
    if fam not in roles.TEXT_GATED_FAMILIES:
        return 0.0
    text = rec["text_blob"]
    build_hits = len(_BUILD_RE.findall(text))
    obj_hits = len(_OBJ_RE.findall(text))
    rigor = 1 if _RIGOR_RE.search(text) else 0
    score = min(build_hits * 0.4 + obj_hits * 0.12, 0.9) + rigor * 0.1
    return min(score, 1.0)


def location_fit(rec):
    loc = (rec["location"] or "").lower()
    relocate = bool(rec["signals"].get("willing_to_relocate"))
    if any(h in loc for h in ("pune", "noida")):
        return 1.0
    if any(h in loc for h in INDIA_HUBS):
        return 0.85
    if rec["country"] == "India":
        return 0.7
    if relocate:
        return 0.55
    return 0.35  # outside India, no relocate (JD: case-by-case, no visa)


def score(rec, hard_reject, soft_penalty):
    fam = roles.family(rec["title"])
    sk = skills.analyze(rec)

    g_role = roles.ROLE_BASE[fam]
    g_sub = substance(rec, fam)
    g_dom = sk["coverage"]
    g_comp = companies.arc_score(rec)
    g_yoe = yoe_fit(rec["yoe"])
    g_loc = location_fit(rec)

    fit = (WEIGHTS["role"] * g_role
           + WEIGHTS["substance"] * g_sub
           + WEIGHTS["domains"] * g_dom
           + WEIGHTS["company"] * g_comp
           + WEIGHTS["yoe"] * g_yoe
           + WEIGHTS["location"] * g_loc)

    # G6 exclusion penalties
    penalties = []
    if fam == "research" and g_sub < 0.30:
        fit -= 0.25
        penalties.append("research_only")
    if fam == "cv" and not sk["nlp_signal"]:
        fit -= 0.25
        penalties.append("cv_only")
    # stuffer guard: non-technical title leaning on AI skills -> already 0 via role,
    # but flag for diagnostics
    if fam == "nontech" and sk["n_ai_skills_raw"] >= 4:
        penalties.append("keyword_stuffer")

    fit = max(fit, 0.0)
    fit *= (1.0 - soft_penalty)

    if hard_reject:
        fit = 0.0

    return {
        "fit": fit,
        "family": fam,
        "g_role": g_role, "g_sub": g_sub, "g_dom": g_dom,
        "g_comp": g_comp, "g_yoe": g_yoe, "g_loc": g_loc,
        "trusted_domains": sorted(sk["trusted_domains"]),
        "must_have_hits": sk["must_have_hits"],
        "n_ai_skills_raw": sk["n_ai_skills_raw"],
        "penalties": penalties,
    }
