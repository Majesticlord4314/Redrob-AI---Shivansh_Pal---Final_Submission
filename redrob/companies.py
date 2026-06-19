"""Company -> category, plus a career-arc signal (G3).

63 distinct companies in the data -> hand table is tractable. Unmapped names
fall back to the `industry` field. See ARCHITECTURE.md Stage E.
"""

SERVICES = {
    "Infosys", "Wipro", "TCS", "Cognizant", "Capgemini", "Accenture", "HCL",
    "Tech Mahindra", "Mphasis", "Mindtree", "Genpact", "Genpact AI",
}
PRODUCT = {
    "Swiggy", "Zomato", "Razorpay", "CRED", "Ola", "Meesho", "PhonePe", "Dream11",
    "Flipkart", "Unacademy", "Nykaa", "PolicyBazaar", "BYJU'S", "Paytm", "Freshworks",
    "upGrad", "PharmEasy", "InMobi", "Zoho", "Vedantu", "Glance",
}
AI_STARTUP = {
    "Sarvam AI", "Krutrim", "Aganitha", "Wysa", "Haptik", "Verloop.io", "Observe.AI",
    "Rephrase.ai", "Saarthi.ai", "Niramai", "Mad Street Den",
}
BIGTECH = {"Meta", "Apple", "Adobe", "Salesforce", "Google", "Microsoft", "Amazon"}
FICTIONAL = {
    "Wayne Enterprises", "Initech", "Pied Piper", "Acme Corp", "Globex Inc", "Hooli",
    "Dunder Mifflin", "Stark Industries",
}

SERVICES_INDUSTRY = {"IT Services", "Consulting", "AI Services"}
PRODUCT_INDUSTRY = {
    "Software", "Fintech", "E-commerce", "Food Delivery", "EdTech", "SaaS", "AI/ML",
    "AdTech", "Transportation", "Insurance Tech", "HealthTech", "Gaming",
    "Conversational AI", "Voice AI", "HealthTech AI", "Internet", "Media",
    "Consumer Electronics",
}
NONTECH_INDUSTRY = {"Manufacturing", "Paper Products", "Conglomerate"}

GOOD = {"product", "ai_startup", "bigtech"}


def category(company, industry=""):
    if company in SERVICES:
        return "services"
    if company in AI_STARTUP:
        return "ai_startup"
    if company in PRODUCT:
        return "product"
    if company in BIGTECH:
        return "bigtech"
    if company in FICTIONAL:
        return "fictional"
    # fallback to industry
    if industry in SERVICES_INDUSTRY:
        return "services"
    if industry in PRODUCT_INDUSTRY:
        return "product"
    if industry in NONTECH_INDUSTRY:
        return "nontech"
    return "unknown"


def arc_score(rec):
    """0..1 company/career-arc fit. Strong penalty for entire-career services."""
    cats = []
    for ch in rec["career"]:
        cats.append(category(ch["company"], ch["industry"]))
    cur = category(rec["current_company"], rec["current_industry"])
    if not cats:
        cats = [cur]

    all_services = all(c == "services" for c in cats)
    has_good = any(c in GOOD for c in cats)

    if all_services:
        return 0.10
    if cur in {"ai_startup"}:
        return 0.90
    if cur in {"product", "bigtech"}:
        return 0.80
    if has_good:  # prior product/ai, current is services/other -> JD says "fine"
        return 0.55
    # fictional / nontech / unknown only
    return 0.40
