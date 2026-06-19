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

# Founding years for REAL companies (conservative/earliest-plausible where unsure).
# Used ONLY for the H6 honeypot check: tenure that EXCEEDS a company's age is an
# absolute impossibility. NOTE: the dataset does NOT respect start-dates vs founding
# (start-before-founding is pervasive noise), so we never use that; only the
# duration > company-age impossibility, which is unambiguous. Fictional companies
# are intentionally absent (never flagged).
FOUNDING = {
    "Swiggy": 2014, "Zomato": 2008, "Razorpay": 2014, "CRED": 2018, "Ola": 2010,
    "Meesho": 2015, "PhonePe": 2015, "Dream11": 2008, "Flipkart": 2007,
    "Unacademy": 2015, "Nykaa": 2012, "PolicyBazaar": 2008, "BYJU'S": 2011,
    "Paytm": 2010, "Freshworks": 2010, "upGrad": 2015, "PharmEasy": 2015,
    "InMobi": 2007, "Zoho": 1996, "Vedantu": 2011, "Glance": 2019,
    "Sarvam AI": 2023, "Krutrim": 2023, "Aganitha": 2016, "Wysa": 2016,
    "Haptik": 2013, "Verloop.io": 2016, "Observe.AI": 2017, "Rephrase.ai": 2019,
    "Saarthi.ai": 2017, "Niramai": 2016, "Mad Street Den": 2013, "Yellow.ai": 2016,
    "Locobuzz": 2015, "Meta": 2004, "Apple": 1976, "Adobe": 1982, "Salesforce": 1999,
    "Netflix": 1997, "Microsoft": 1975, "Amazon": 1994, "Google": 1998,
    "LinkedIn": 2003, "Uber": 2009, "TCS": 1968, "Infosys": 1981, "Wipro": 1945,
    "Cognizant": 1994, "Accenture": 1989, "Capgemini": 1967, "Tech Mahindra": 1986,
    "HCL": 1976, "Genpact": 1997, "Mphasis": 1998, "Mindtree": 1999,
}


def max_tenure_months(company, ref_year):
    """Largest plausible tenure (months) at a real company, or None if unknown."""
    fy = FOUNDING.get(company)
    if fy is None:
        return None
    return max(0, (ref_year - fy) * 12)


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
