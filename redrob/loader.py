"""Stream candidates.jsonl into compact records with derived fields.

V1: keep it simple. Parse dates, compute career-span / documented-months, and
pull only the fields the ranker needs. Everything else is dropped to keep memory
low (we never need the whole 487MB in RAM at once).
"""
import json
from datetime import date

REF_DATE = date(2026, 6, 19)  # "today" per challenge context


def _pdate(s):
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return None


def _months_between(d1, d2):
    """Approx whole months from d1 (earlier) to d2 (later)."""
    if d1 is None or d2 is None:
        return None
    return (d2 - d1).days / 30.44


def load(path):
    """Yield compact candidate dicts."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                c = json.loads(line)
            except json.JSONDecodeError:
                continue
            yield _compact(c)


def _compact(c):
    p = c.get("profile", {})
    rs = c.get("redrob_signals", {})
    career = c.get("career_history", []) or []

    starts = [_pdate(ch.get("start_date")) for ch in career]
    ends = [_pdate(ch.get("end_date")) for ch in career]
    starts_v = [d for d in starts if d]
    earliest_start = min(starts_v) if starts_v else None
    # latest activity = today if any current role, else latest end
    latest_end = max([d for d in ends if d], default=None)

    documented_months = sum(int(ch.get("duration_months", 0) or 0) for ch in career)
    elapsed_months = _months_between(earliest_start, REF_DATE)

    text_parts = [p.get("summary", "") or ""]
    for ch in career:
        text_parts.append(ch.get("description", "") or "")
    text_blob = " \n ".join(text_parts).lower()

    return {
        "candidate_id": c.get("candidate_id"),
        "name": p.get("anonymized_name", ""),
        "title": p.get("current_title", "") or "",
        "headline": p.get("headline", "") or "",
        "summary": p.get("summary", "") or "",
        "yoe": float(p.get("years_of_experience", 0) or 0),
        "location": p.get("location", "") or "",
        "country": p.get("country", "") or "",
        "current_company": p.get("current_company", "") or "",
        "current_industry": p.get("current_industry", "") or "",
        "career": [
            {
                "company": ch.get("company", "") or "",
                "title": ch.get("title", "") or "",
                "industry": ch.get("industry", "") or "",
                "start": _pdate(ch.get("start_date")),
                "end": _pdate(ch.get("end_date")),
                "duration_months": int(ch.get("duration_months", 0) or 0),
                "is_current": bool(ch.get("is_current")),
            }
            for ch in career
        ],
        "education": c.get("education", []) or [],
        "skills": c.get("skills", []) or [],
        "assessments": rs.get("skill_assessment_scores", {}) or {},
        "signals": rs,
        # derived
        "earliest_start": earliest_start,
        "latest_end": latest_end,
        "documented_months": documented_months,
        "elapsed_months": elapsed_months,
        "text_blob": text_blob,
    }
