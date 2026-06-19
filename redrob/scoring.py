"""Fit scoring (V2).

Changes from V1 (driven by DISCOVERIES D2/D3/D7/D8/D9):
- DROP career-description "substance" mining: descriptions are templated noise (D8).
- ADD summary_archetype: the generator's intended-quality proxy, independent of
  title/skills (D9). Gated by consistency so honeypots (which use the elite
  archetype) still can't surface.
- Continuous YOE curve and finer domain/company gradients to separate the top
  (fixes the near-tie compression that capped NDCG@10).

Weights are sensible defaults validated on the gold set, not blindly tuned.
"""
import math
from . import roles, companies, skills, summary

WEIGHTS = {
    "role": 0.26,
    "archetype": 0.18,
    "domains": 0.22,
    "company": 0.16,
    "yoe": 0.12,
    "location": 0.06,
}

ARCHETYPE_SCORE = {
    "senior_search": 1.00,
    "ml_prod": 0.75,
    "ds": 0.45,
    "data": 0.30,
    "other": 0.15,
}

INDIA_HUBS = ("pune", "noida", "hyderabad", "delhi", "mumbai", "gurgaon", "gurugram",
              "bangalore", "bengaluru", "ncr", "chennai", "kolkata")


def yoe_fit(y):
    """Continuous bell centered on 7 (JD ideal 6-8, band 5-9), floored."""
    return max(0.30, math.exp(-((y - 7.0) ** 2) / (2 * 2.2 ** 2)))


def location_fit(rec):
    loc = (rec["location"] or "").lower()
    relocate = bool(rec["signals"].get("willing_to_relocate"))
    if any(h in loc for h in ("pune", "noida")):
        return 1.0
    if any(h in loc for h in INDIA_HUBS):
        return 0.85
    if rec["country"] == "India":
        return 0.70
    if relocate:
        return 0.55
    return 0.35


def score(rec, hard_reject, soft_penalty):
    fam = roles.family(rec["title"])
    sk = skills.analyze(rec)
    arch = summary.archetype(rec["summary"])

    g_role = roles.ROLE_BASE[fam]
    g_arch = ARCHETYPE_SCORE[arch]
    g_dom = sk["coverage"]
    g_comp = companies.arc_score(rec)
    g_yoe = yoe_fit(rec["yoe"])
    g_loc = location_fit(rec)

    fit = (WEIGHTS["role"] * g_role
           + WEIGHTS["archetype"] * g_arch
           + WEIGHTS["domains"] * g_dom
           + WEIGHTS["company"] * g_comp
           + WEIGHTS["yoe"] * g_yoe
           + WEIGHTS["location"] * g_loc)

    penalties = []
    if fam == "research":
        fit -= 0.25
        penalties.append("research_only")
    if fam == "cv" and not sk["nlp_signal"]:
        fit -= 0.25
        penalties.append("cv_only")
    if fam == "nontech" and sk["n_ai_skills_raw"] >= 4:
        penalties.append("keyword_stuffer")

    fit = max(fit, 0.0)
    fit *= (1.0 - soft_penalty)
    if hard_reject:
        fit = 0.0

    return {
        "fit": fit,
        "family": fam,
        "archetype": arch,
        "g_role": g_role, "g_arch": g_arch, "g_dom": g_dom,
        "g_comp": g_comp, "g_yoe": g_yoe, "g_loc": g_loc,
        "trusted_domains": sorted(sk["trusted_domains"]),
        "must_have_hits": sk["must_have_hits"],
        "n_ai_skills_raw": sk["n_ai_skills_raw"],
        "penalties": penalties,
    }
