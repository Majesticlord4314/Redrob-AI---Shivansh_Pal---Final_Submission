"""Bounded behavioral modifier (Stage F).

final = fit * M, M in [0.6, 1.1]. Unavailability hurts more than availability
helps (matches JD "not actually available"). Sentinels (-1) are neutral.
"""
from datetime import date

REF_DATE = date(2026, 6, 19)


def _pdate(s):
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def modifier(rec):
    s = rec["signals"]
    adj = 0.0
    notes = []

    # last-active recency
    la = _pdate(s.get("last_active_date"))
    if la:
        days = (REF_DATE - la).days
        if days > 90:
            pen = min((days - 90) / 180.0, 1.0) * 0.25
            adj -= pen
            if pen > 0.05:
                notes.append(f"stale_{days}d")

    rr = s.get("recruiter_response_rate")
    if isinstance(rr, (int, float)):
        if rr >= 0.5:
            adj += 0.03
        elif rr <= 0.10:
            adj -= 0.10
            notes.append("low_response")

    if s.get("open_to_work_flag") is False:
        adj -= 0.05
        notes.append("not_open")

    ic = s.get("interview_completion_rate")
    if isinstance(ic, (int, float)) and ic < 0.40:
        adj -= 0.05

    if (s.get("saved_by_recruiters_30d") or 0) >= 15:
        adj += 0.03
    if (s.get("profile_completeness_score") or 0) >= 80:
        adj += 0.02
    gh = s.get("github_activity_score", -1)
    if isinstance(gh, (int, float)) and gh >= 40:  # >=0 only; -1 sentinel ignored
        adj += 0.03

    m = max(0.6, min(1.0 + adj, 1.1))
    return m, notes
