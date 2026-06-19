"""Summary archetype detection.

The dataset's `summary` field is templated into ~4 generator archetypes that
correlate with intended candidate quality (see DISCOVERIES D9). Career-history
*descriptions* are noise (D8) and are NOT used. This module reads only the
profile summary.

Archetypes (best -> weakest):
  senior_search : "Senior AI engineer ... focus on search, retrieval, and ranking"
  ml_prod       : "ML engineer ... building ML-powered features in production ... NLP, recommendation systems"
  ds            : "Data scientist / ML engineer ... strongest at the modeling and analysis side"
  data          : "Software / data professional ... data pipelines, backend systems ... do more of the ML"
  other         : anything else
"""
import re

_SENIOR_SEARCH = re.compile(r"focus on search, retrieval, and ranking|rebuilt the candidate-jd matching", re.I)
_ML_PROD = re.compile(r"building ml-powered features in production|strong background in nlp, recommendation systems", re.I)
_DS = re.compile(r"data scientist\s*/\s*ml engineer|strongest at the modeling and analysis", re.I)
_DATA = re.compile(r"software\s*/\s*data professional|data pipelines, backend systems", re.I)

# self-reported years inside the summary, e.g. "with 6.8 years of experience"
_YEARS = re.compile(r"with\s+([0-9]+(?:\.[0-9]+)?)\s+years", re.I)

RANK = {"senior_search": 4, "ml_prod": 3, "ds": 2, "data": 1, "other": 0}


def archetype(summary):
    s = summary or ""
    if _SENIOR_SEARCH.search(s):
        return "senior_search"
    if _ML_PROD.search(s):
        return "ml_prod"
    if _DS.search(s):
        return "ds"
    if _DATA.search(s):
        return "data"
    return "other"


def stated_years(summary):
    m = _YEARS.search(summary or "")
    return float(m.group(1)) if m else None
