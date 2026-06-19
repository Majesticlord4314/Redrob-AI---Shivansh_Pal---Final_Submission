"""Title -> role family. Drives the primary relevance signal (G1) and gates
career-text mining (so non-technical titles can't be promoted by sprinkled
keywords). See ARCHITECTURE.md Stage C.
"""

CORE_AI = {
    "ML Engineer", "Machine Learning Engineer", "AI Engineer", "Senior AI Engineer",
    "Lead AI Engineer", "Applied ML Engineer", "Senior Machine Learning Engineer",
    "Staff Machine Learning Engineer", "NLP Engineer", "Senior NLP Engineer",
    "Recommendation Systems Engineer", "Search Engineer", "Senior Software Engineer (ML)",
}
DS = {"Data Scientist", "Senior Data Scientist", "AI Specialist"}
RESEARCH = {"AI Research Engineer", "Senior Applied Scientist"}
CV = {"Computer Vision Engineer"}
JUNIOR = {"Junior ML Engineer"}
# data-adjacent: can become "plain-language Tier 5" via career substance
DATA_ADJACENT = {
    "Data Engineer", "Senior Data Engineer", "Analytics Engineer", "Backend Engineer",
    "Data Analyst", "Software Engineer", "Senior Software Engineer",
}
# other technical: weak relevance
OTHER_TECH = {
    "Full Stack Developer", "Cloud Engineer", "DevOps Engineer", "Java Developer",
    ".NET Developer", "Mobile Developer", "Frontend Engineer", "QA Engineer",
}

# base role_fit per family (0..1)
ROLE_BASE = {
    "core_ai": 1.00,
    "ds": 0.72,
    "junior": 0.55,
    "data_adjacent": 0.45,
    "research": 0.40,
    "cv": 0.35,
    "other_tech": 0.18,
    "nontech": 0.00,
}

# families whose career text we trust enough to mine (title-gate)
TEXT_GATED_FAMILIES = {"core_ai", "ds", "junior", "data_adjacent", "research", "cv"}


def family(title):
    t = (title or "").strip()
    if t in CORE_AI:
        return "core_ai"
    if t in DS:
        return "ds"
    if t in RESEARCH:
        return "research"
    if t in CV:
        return "cv"
    if t in JUNIOR:
        return "junior"
    if t in DATA_ADJACENT:
        return "data_adjacent"
    if t in OTHER_TECH:
        return "other_tech"
    return "nontech"
