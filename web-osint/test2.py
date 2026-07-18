import os
import re
import json
import time
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

SERPAPI_KEY = os.getenv("SERPAPI_KEY")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}

# --- Regex patterns -------------------------------------------------

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

# Loosely matches international/US style phone numbers
PHONE_RE = re.compile(
    r"(\+?\d{1,3}[\s.-]?)?(\(?\d{2,4}\)?[\s.-]?){2,4}\d{3,4}"
)

# Common social profile / username patterns
SOCIAL_RE = {
    "twitter_x": re.compile(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]{2,30})"),
    "instagram": re.compile(r"instagram\.com/([A-Za-z0-9_.]{2,30})"),
    "facebook": re.compile(r"facebook\.com/([A-Za-z0-9_.]{2,50})"),
    "linkedin": re.compile(r"linkedin\.com/(?:in|company)/([A-Za-z0-9_-]{2,60})"),
    "github": re.compile(r"github\.com/([A-Za-z0-9_-]{2,39})"),
    "telegram": re.compile(r"t\.me/([A-Za-z0-9_]{3,32})"),
}

ADDRESS_HINTS = re.compile(
    r"\b\d{1,5}\s+[A-Za-z0-9.\s]{3,40}"
    r"(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?|Lane|Ln\.?|"
    r"Drive|Dr\.?|Court|Ct\.?|Way|Suite|Floor)\b[A-Za-z0-9,.\s]{0,60}",
    re.IGNORECASE,
)


# --- Search ----------------------------------------------------------

def google_search(query, num_results=10):
    url = "https://serpapi.com/search"
    params = {
        "engine": "google",
        "q": query,
        "num": num_results,
        "hl": "en",
        "gl": "us",
        "api_key": SERPAPI_KEY,
    }
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    results = []
    for i, item in enumerate(data.get("organic_results", []), start=1):
        results.append({
            "rank": i,
            "title": item.get("title"),
            "url": item.get("link"),
            "displayed_link": item.get("displayed_link"),
            "snippet": item.get("snippet"),
        })
    return results


# --- Page scraping -----------------------------------------------------

def fetch_page(url, timeout=15):
    """Fetch a page and return (html_text, plain_text) or (None, None) on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        resp.raise_for_status()
    except requests.RequestException as e:
        return None, None, str(e)

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    # Strip script/style so we don't pull junk out of JS blobs
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    return html, text, None


def extract_contacts(html, text):
    emails = sorted(set(EMAIL_RE.findall(text)))
    # PHONE_RE has groups, so use finditer to get full matches instead of findall
    phones = sorted(set(
        m.group(0).strip()
        for m in PHONE_RE.finditer(text)
        if len(re.sub(r"\D", "", m.group(0))) >= 7
    ))

    socials = {}
    for platform, pattern in SOCIAL_RE.items():
        matches = sorted(set(pattern.findall(html or "")))
        if matches:
            socials[platform] = matches

    addresses = sorted(set(m.strip() for m in ADDRESS_HINTS.findall(text)))

    return {
        "emails": emails,
        "phones": phones,
        "addresses": addresses,
        "socials": socials,
    }


def scrape_url(url):
    domain = urlparse(url).netloc
    html, text, error = fetch_page(url)

    if error:
        return {
            "url": url,
            "domain": domain,
            "status": "failed",
            "error": error,
        }

    contacts = extract_contacts(html, text)
    return {
        "url": url,
        "domain": domain,
        "status": "ok",
        **contacts,
    }


# --- Pipeline ----------------------------------------------------------

def search_and_scrape(query, num_results=10, delay=1.5):
    search_results = google_search(query, num_results=num_results)

    enriched = []
    for item in search_results:
        url = item.get("url")
        if not url:
            continue

        scraped = scrape_url(url)
        enriched.append({**item, "contacts": scraped})

        time.sleep(delay)  # be polite, avoid hammering sites

    return enriched


if __name__ == "__main__":
    query = input("Search Query: ")
    n = input("Number of results (default 10): ").strip()
    num_results = int(n) if n else 10

    data = search_and_scrape(query, num_results=num_results)
    print(json.dumps(data, indent=2, ensure_ascii=False))

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print("\nSaved to results.json")