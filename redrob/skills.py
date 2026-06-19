"""Skill trust model + trusted-domain coverage (G4).

A skill counts only when corroborated by duration / endorsements / assessment,
so keyword stuffing (high proficiency, 0 duration, no endorsement) earns ~0.
The real feature is how many distinct *trusted* domains a candidate covers,
with embeddings + vector_db + nlp_ir as the JD must-haves.
"""
from math import log1p

DOMAIN = {
    # embeddings
    "Embeddings": "embeddings", "Sentence Transformers": "embeddings",
    "BGE": "embeddings", "E5": "embeddings",
    # vector db / hybrid search
    "Pinecone": "vector_db", "FAISS": "vector_db", "Milvus": "vector_db",
    "Qdrant": "vector_db", "Weaviate": "vector_db", "Elasticsearch": "vector_db",
    "OpenSearch": "vector_db", "Vector Search": "vector_db",
    # nlp / ir
    "NLP": "nlp_ir", "Information Retrieval": "nlp_ir", "Semantic Search": "nlp_ir",
    "BM25": "nlp_ir", "LLMs": "nlp_ir", "RAG": "nlp_ir",
    # ranking / recsys
    "Learning to Rank": "ranking", "Recommendation Systems": "ranking",
    # llm tuning
    "Fine-tuning LLMs": "llm", "LoRA": "llm", "QLoRA": "llm", "PEFT": "llm",
    # ml core
    "PyTorch": "ml_core", "TensorFlow": "ml_core", "Statistical Modeling": "ml_core",
    # data engineering
    "Spark": "data_eng", "Airflow": "data_eng", "Kafka": "data_eng", "dbt": "data_eng",
    "Snowflake": "data_eng", "BigQuery": "data_eng", "Databricks": "data_eng",
    "Hadoop": "data_eng", "Apache Beam": "data_eng", "Apache Flink": "data_eng",
    "ETL": "data_eng",
    # computer vision / speech (negative domains for this JD)
    "Image Classification": "cv", "GANs": "cv", "Object Detection": "cv",
    "OpenCV": "cv", "Speech Recognition": "speech", "TTS": "speech",
}

MUST_HAVE = {"embeddings", "vector_db", "nlp_ir"}
BASE = {"beginner": 0.25, "intermediate": 0.5, "advanced": 0.8, "expert": 1.0}
TRUST_THRESHOLD = 0.45


def _trust(skill, assessments):
    base = BASE.get(skill.get("proficiency"), 0.3)
    dur = int(skill.get("duration_months", 0) or 0)
    dur_factor = min(dur / 12.0, 1.0)
    trust = base * (0.3 + 0.7 * dur_factor)
    if int(skill.get("endorsements", 0) or 0) >= 5:
        trust *= 1.10
    name = skill.get("name")
    if name in assessments and (assessments.get(name) or 0) >= 50:
        trust *= 1.15
    return min(trust, 1.0)


def analyze(rec):
    """Return dict with trusted domains and coverage features."""
    assessments = rec["assessments"]
    trusted_domains = set()
    cv_signal = False
    nlp_signal = False
    for s in rec["skills"]:
        dom = DOMAIN.get(s.get("name"))
        if dom is None:
            continue
        if _trust(s, assessments) >= TRUST_THRESHOLD:
            trusted_domains.add(dom)
            if dom == "cv":
                cv_signal = True
            if dom in ("nlp_ir", "ranking", "embeddings"):
                nlp_signal = True

    must_have_hits = len(trusted_domains & MUST_HAVE)
    relevant = {"embeddings", "vector_db", "nlp_ir", "ranking", "llm"}
    n_relevant_trusted = len(trusted_domains & relevant)

    # assessment corroboration: relevant skills with a real Redrob assessment score
    assess_hits = 0
    for s in rec["skills"]:
        if DOMAIN.get(s.get("name")) in relevant:
            nm = s.get("name")
            if nm in assessments and (assessments.get(nm) or 0) >= 50:
                assess_hits += 1
    assess_factor = min(assess_hits / 2.0, 1.0)

    # finer, continuous coverage: must-haves dominate, breadth + assessment add depth
    cov = 0.55 * (must_have_hits / 3.0) + 0.30 * min(n_relevant_trusted / 5.0, 1.0) + 0.15 * assess_factor
    cov = min(cov, 1.0)

    return {
        "trusted_domains": trusted_domains,
        "must_have_hits": must_have_hits,
        "n_relevant_trusted": n_relevant_trusted,
        "assess_factor": assess_factor,
        "coverage": cov,
        "cv_signal": cv_signal,
        "nlp_signal": nlp_signal,
        "n_ai_skills_raw": sum(1 for s in rec["skills"] if DOMAIN.get(s.get("name")) in relevant),
    }
