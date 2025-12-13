import os
import pytz
from datetime import datetime
import requests

IST = pytz.timezone("Asia/Kolkata")


def normalize_to_ist(dt_string):
    try:
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        dt_ist = dt.astimezone(IST)
        return dt_ist.strftime("%Y-%m-%d")
    except:
        return ""


def detect_authorship_issue(author):
    if not author:
        return "No Author"

    author_lower = author.lower()

    generic_authors = [
        "bureau",
        "staff",
        "team",
        "editorial",
        "news desk",
        "pti",
        "ani",
        "reuters"
    ]

    if any(g in author_lower for g in generic_authors):
        return "Generic / Agency"

    return "Named Author"


def fetch_news_combined(keywords, from_dt_utc, to_dt_utc, max_results=50):
    key = os.environ.get("NEWSAPI_KEY")
    articles = []

    if not key:
        return articles

    query = " OR ".join([f"\"{k}\"" for k in keywords])

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "from": from_dt_utc.isoformat(),
        "to": to_dt_utc.isoformat(),
        "pageSize": max_results,
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": key
    }

    resp = requests.get(url, params=params, timeout=20)
    data = resp.json()

    for item in data.get("articles", []):
        author = item.get("author", "") or ""

        articles.append({
            "date": normalize_to_ist(item.get("publishedAt", "")),
            "title": item.get("title", ""),
            "source": item.get("source", {}).get("name", ""),
            "author": author,
            "author_flag": detect_authorship_issue(author),
            "marked_ai": False,
            "url": item.get("url", "")
        })

    return articles
