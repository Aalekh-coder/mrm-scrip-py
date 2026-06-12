import re
import json
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin


EMAIL_REGEX = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)

PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,4}[\s\-]?)?"
    r"(?:\(?\d{2,5}\)?[\s\-]?)?"
    r"\d{3,5}[\s\-]?\d{3,5}[\s\-]?\d{2,5}"
)

PINCODE_REGEX = re.compile(r"\b\d{6}\b")

# Address noise patterns to strip out after extraction
ADDRESS_NOISE_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),  # emails
    re.compile(r"(?:\+?\d[\s\-]?){8,15}"),                            # phone numbers
    re.compile(r"https?://\S+"),                                        # URLs
    re.compile(r"©.*", re.IGNORECASE),                                  # copyright lines
    re.compile(r"(follow us|subscribe|cookie|privacy policy|terms|all rights reserved).*", re.IGNORECASE),
]

# Words that suggest a line is address content
ADDRESS_KEYWORDS = re.compile(
    r"\b(street|st\.|road|rd\.|avenue|ave\.|sector|block|floor|plot|nagar|"
    r"colony|phase|opposite|near|above|behind|landmark|lane|marg|chowk|"
    r"building|tower|complex|house|office|suite|district|taluka|village|"
    r"post box|p\.?o\.?\s*box|p\.?o\.\s*\-)\b",
    re.IGNORECASE,
)

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
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except Exception:
        return ""


def clean_phone(phone):
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 8 or len(digits) > 15:
        return None
    return digits


def extract_emails(text):
    emails = set()
    for email in EMAIL_REGEX.findall(text):
        email = email.lower().strip()
        # Skip image filenames and common false positives
        if email and not email.endswith((".png", ".jpg", ".gif", ".svg", ".webp")):
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


def clean_address_candidate(raw: str) -> str | None:
    """
    Strip noise (emails, phones, URLs, legal boilerplate) from a raw
    address candidate and return only the address portion, or None if
    what remains doesn't look like an address.
    """
    text = raw

    # Remove noise patterns
    for pattern in ADDRESS_NOISE_PATTERNS:
        text = pattern.sub("", text)

    # Collapse extra whitespace
    text = re.sub(r"\s{2,}", " ", text).strip()

    # Drop short leftovers
    if len(text) < 20:
        return None

    # Must contain at least one address-like keyword or a pincode
    if not ADDRESS_KEYWORDS.search(text) and not PINCODE_REGEX.search(text):
        return None

    return text


def extract_address_candidates(text: str) -> set:
    """
    Find address blocks by locating 6-digit pincodes and extracting
    a window around them, then clean and validate each candidate.
    """
    addresses = set()

    for match in PINCODE_REGEX.finditer(text):
        # Widen the window to capture multi-line addresses
        start = max(0, match.start() - 200)
        end = min(len(text), match.end() + 80)

        raw = text[start:end]
        raw = " ".join(raw.split())  # normalise whitespace

        cleaned = clean_address_candidate(raw)
        if cleaned:
            addresses.add(cleaned)

    return addresses


def extract_footer_text(soup: BeautifulSoup) -> str:
    """
    Pull visible text from footer-like elements: <footer>, elements
    with footer/contact in their id or class, and common footer divs.
    """
    footer_texts = []

    # Semantic <footer> tag
    for footer in soup.find_all("footer"):
        footer_texts.append(footer.get_text(" ", strip=True))

    # Elements whose id or class suggests footer / contact info
    for tag in soup.find_all(True):
        tag_id = " ".join(tag.get("id", "").lower().split())
        tag_class = " ".join(tag.get("class", [])).lower()
        combined = tag_id + " " + tag_class

        if any(kw in combined for kw in ("footer", "contact-info", "contact_info", "address", "reach-us")):
            footer_texts.append(tag.get_text(" ", strip=True))

    return " ".join(footer_texts)


def find_important_pages(base_url, soup):
    pages = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].lower()
        if any(word in href for word in IMPORTANT_PAGE_KEYWORDS):
            full_url = urljoin(base_url, href)
            pages.add(full_url)
    return pages


def process_page(url: str) -> dict:
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

    # Full page text (for emails / phones)
    full_text = soup.get_text(" ", strip=True)

    result["emails"].update(extract_emails(full_text))
    result["phones"].update(extract_phones(full_text))
    result["socials"].update(extract_socials(soup))

    # mailto: links
    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").strip().lower()
            if email:
                result["emails"].add(email)

    # --- Address extraction: footer + full page ---
    footer_text = extract_footer_text(soup)
    combined_for_address = footer_text + " " + full_text
    result["addresses"].update(extract_address_candidates(combined_for_address))

    return result


def extract_contact_details(domain: str) -> dict:
    base_url = normalize_domain(domain)

    final = {
        "emails": set(),
        "phones": set(),
        "socials": set(),
        "addresses": set(),
    }

    homepage_html = fetch_html(base_url)
    if not homepage_html:
        return {"error": "Unable to fetch website"}

    homepage_soup = BeautifulSoup(homepage_html, "lxml")

    pages_to_crawl = {base_url}
    pages_to_crawl.update(find_important_pages(base_url, homepage_soup))

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
    print(json.dumps(result, indent=2, ensure_ascii=False))