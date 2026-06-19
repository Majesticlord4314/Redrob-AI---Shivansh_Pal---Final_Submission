"""Consistency gate = honeypot defense.

Only logically-impossible rules (low false-positive), with tolerance buffers
absorbing rounding / gaps / history-truncation. A hard_reject candidate is
forced out of the output set entirely. See ARCHITECTURE.md Stage B.
"""
from . import companies

REF_YEAR = 2026

# tolerance buffers (months)
BUF_DOC_VS_YOE = 14
BUF_DOC_VS_ELAPSED = 14
BUF_ROLE_VS_YOE = 6
BUF_YOE_VS_ELAPSED = 30
BUF_TENURE_VS_COMPANY = 12  # H6: absorbs founding-year uncertainty


def check(rec):
    """Return (hard_reject: bool, reasons: list[str], soft_penalty: float)."""
    reasons = []
    soft = 0.0
    yoe_m = rec["yoe"] * 12.0
    doc = rec["documented_months"]
    elapsed = rec["elapsed_months"]

    # H1: expert proficiency with zero months of use
    for s in rec["skills"]:
        if s.get("proficiency") == "expert" and int(s.get("duration_months", 0) or 0) == 0:
            reasons.append("H1:expert_skill_with_0_months")
            break

    # H2a: documented work exceeds stated total experience
    if doc > yoe_m + BUF_DOC_VS_YOE:
        reasons.append(f"H2a:documented({doc:.0f}m)>yoe({yoe_m:.0f}m)")

    # H2b: documented work exceeds calendar time since first job
    if elapsed is not None and doc > elapsed + BUF_DOC_VS_ELAPSED:
        reasons.append(f"H2b:documented({doc:.0f}m)>elapsed({elapsed:.0f}m)")

    # H3: a single role longer than the entire stated career
    for ch in rec["career"]:
        if ch["duration_months"] > yoe_m + BUF_ROLE_VS_YOE:
            reasons.append(f"H3:role({ch['duration_months']}m)>yoe({yoe_m:.0f}m)")
            break

    # H4: claims more experience than calendar since first job
    if elapsed is not None and yoe_m > elapsed + BUF_YOE_VS_ELAPSED:
        reasons.append(f"H4:yoe({yoe_m:.0f}m)>elapsed({elapsed:.0f}m)")

    # H5: date corruption
    for ch in rec["career"]:
        if ch["start"] and ch["end"] and ch["end"] < ch["start"]:
            reasons.append("H5:role_end_before_start")
            break
    for e in rec["education"]:
        try:
            if e.get("end_year") and e.get("start_year") and int(e["end_year"]) < int(e["start_year"]):
                reasons.append("H5:edu_end_before_start")
                break
        except (TypeError, ValueError):
            pass

    # H6: tenure at a real company exceeds the company's age (impossible).
    # Only the duration>age impossibility is used — the dataset does not respect
    # start-date vs founding, so "started before founding" is noise and NOT used.
    for ch in rec["career"]:
        max_t = companies.max_tenure_months(ch["company"], REF_YEAR)
        if max_t is not None and ch["duration_months"] > max_t + BUF_TENURE_VS_COMPANY:
            reasons.append(
                f"H6:tenure({ch['duration_months']}m)>{ch['company']}_age({max_t}m)")
            break

    hard_reject = len(reasons) > 0

    # --- soft anomalies (penalize, do not exclude) ---
    n_current = sum(1 for ch in rec["career"] if ch["is_current"])
    if n_current > 1:
        soft += 0.05
    for ch in rec["career"]:
        if ch["is_current"] and ch["end"] is not None:
            soft += 0.05
            break
    # mild over-direction span gap (elapsed >> yoe): legit gaps, tiny penalty
    if elapsed is not None and (elapsed - yoe_m) > 30 and yoe_m <= elapsed:
        soft += 0.03

    return hard_reject, reasons, min(soft, 0.5)
