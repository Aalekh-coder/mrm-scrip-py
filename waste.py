import re
import json
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


EMAIL_REGEX = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)

PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,4}[\s\-]?)?"
    r"(?:\(?\d{2,5}\)?[\s\-]?)?"
    r"\d{3,5}[\s\-]?\d{3,5}[\s\-]?\d{2,5}"
)

PINCODE_REGEX = re.compile(r"\b\d{6}\b")


SOCIAL_DOMAINS = [
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "pinterest.com",
    "t.me",
]


IMPORTANT_PAGE_KEYWORDS = [
    "contact",
    "contact-us",
    "about",
    "about-us",
    "support",
    "help",
    "reach-us",
    "company",
    "team",
]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}


def normalize_domain(domain: str):
    domain = domain.strip()

    if not domain.startswith(("http://", "https://")):
        domain = "https://" + domain

    return domain


def fetch_html(url: str):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=True,
        )

        response.raise_for_status()

        return response.text

    except Exception:
        return ""


def clean_phone(phone):
    digits = re.sub(r"\D", "", phone)

    if len(digits) < 8:
        return None

    if len(digits) > 15:
        return None

    return digits


def extract_emails(text):
    emails = set()

    for email in EMAIL_REGEX.findall(text):
        email = email.lower().strip()

        if email:
            emails.add(email)

    return emails


def extract_phones(text):
    phones = set()

    for match in PHONE_REGEX.findall(text):
        phone = clean_phone(match)

        if phone:
            phones.add(phone)

    return phones


def extract_socials(soup):
    socials = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()

        for domain in SOCIAL_DOMAINS:
            if domain in href:
                socials.add(href)

    return socials


def extract_address_candidates(text):
    addresses = set()

    for match in PINCODE_REGEX.finditer(text):
        start = max(0, match.start() - 120)
        end = min(len(text), match.end() + 120)

        candidate = text[start:end]
        candidate = " ".join(candidate.split())

        if len(candidate) > 30:
            addresses.add(candidate)

    return addresses


def find_important_pages(base_url, soup):
    pages = set()

    for tag in soup.find_all("a", href=True):
        href = tag["href"].lower()

        if any(word in href for word in IMPORTANT_PAGE_KEYWORDS):
            full_url = urljoin(base_url, href)
            pages.add(full_url)

    return pages


def process_page(url):
    result = {
        "emails": set(),
        "phones": set(),
        "socials": set(),
        "addresses": set(),
    }

    html = fetch_html(url)

    if not html:
        return result

    soup = BeautifulSoup(html, "lxml")

    text = soup.get_text(" ", strip=True)

    result["emails"].update(extract_emails(text))
    result["phones"].update(extract_phones(text))
    result["socials"].update(extract_socials(soup))
    result["addresses"].update(extract_address_candidates(text))

    # mailto links
    for tag in soup.find_all("a", href=True):
        href = tag["href"]

        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").strip()

            if email:
                result["emails"].add(email.lower())

    return result


def extract_contact_details(domain):
    base_url = normalize_domain(domain)

    final = {
        "emails": set(),
        "phones": set(),
        "socials": set(),
        "addresses": set(),
    }

    homepage_html = fetch_html(base_url)

    if not homepage_html:
        return {
            "error": "Unable to fetch website"
        }

    homepage_soup = BeautifulSoup(homepage_html, "lxml")

    pages_to_crawl = {base_url}

    pages_to_crawl.update(
        find_important_pages(
            base_url,
            homepage_soup,
        )
    )

    for page in pages_to_crawl:
        print("Scanning:", page)

        data = process_page(page)

        final["emails"].update(data["emails"])
        final["phones"].update(data["phones"])
        final["socials"].update(data["socials"])
        final["addresses"].update(data["addresses"])

    return {
        "emails": sorted(final["emails"]),
        "phones": sorted(final["phones"]),
        "socialLinks": sorted(final["socials"]),
        "addresses": sorted(final["addresses"]),
    }


if __name__ == "__main__":
    domain = input("Enter domain: ")

    result = extract_contact_details(domain)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
    )