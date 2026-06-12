import re
import json
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

EMAIL_REGEX = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
)

PHONE_REGEX = re.compile(
    r"(?:\+?\d{1,4}[\s\-]?)?"
    r"(?:\(?\d{2,5}\)?[\s\-]?)?"
    r"\d{3,5}[\s\-]?\d{3,5}[\s\-]?\d{2,5}"
)

PINCODE_REGEX = re.compile(r"\b\d{6}\b")

ADDRESS_NOISE_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?:\+?\d[\s\-]?){8,15}"),
    re.compile(r"https?://\S+"),
    re.compile(r"©.*", re.IGNORECASE),
    re.compile(
        r"(follow us|subscribe|cookie|privacy policy|terms|all rights reserved).*",
        re.IGNORECASE,
    ),
]

ADDRESS_KEYWORDS = re.compile(
    r"\b(street|st\.|road|rd\.|avenue|ave\.|sector|block|floor|plot|nagar|"
    r"colony|phase|opposite|near|above|behind|landmark|lane|marg|chowk|"
    r"building|tower|complex|house|office|suite|district|taluka|village|"
    r"post box|p\.?o\.?\s*box|p\.?o\.\s*\-)\b",
    re.IGNORECASE,
)



SOCIAL_PLATFORMS = {
    "facebook.com": {
        "reject": re.compile(
            r"/(sharer|login|share|dialog|plugins|watch|groups|events|pages/create)",
            re.IGNORECASE,
        ),
        "require": re.compile(r"facebook\.com/[A-Za-z0-9_.]+/?$"),
    },
    "instagram.com": {
        "reject": re.compile(
            r"/(p/|reel/|explore/|accounts/|stories/|tv/)", re.IGNORECASE
        ),
        "require": re.compile(r"instagram\.com/[A-Za-z0-9_.]+/?#?$"),
    },
    "x.com": {
        "reject": re.compile(
            r"/(intent|share|home|hashtag|search|login|signup|i/|compose)",
            re.IGNORECASE,
        ),
        "require": re.compile(r"x\.com/[A-Za-z0-9_]+/?$"),
    },
    "twitter.com": {
        "reject": re.compile(
            r"/(intent|share|home|hashtag|search|login|signup|i/|compose)",
            re.IGNORECASE,
        ),
        "require": re.compile(r"twitter\.com/[A-Za-z0-9_]+/?$"),
    },
    "youtube.com": {
        "reject": re.compile(
            r"/(watch|playlist|redirect|results|shorts/[^@]|feed|gaming|premium|"
            r"reporthistory|account|signin|logout)",
            re.IGNORECASE,
        ),
        "require": re.compile(
            r"youtube\.com/(channel/|@|user/)[A-Za-z0-9_\-]+/?$"
        ),
    },
    "wa.me": {
        "reject": re.compile(r"^$"),   # nothing to reject — all wa.me links are valid
        "require": re.compile(r"wa\.me/\d+"),
    },
    "api.whatsapp.com": {
        "reject": re.compile(r"^$"),
        "require": re.compile(r"api\.whatsapp\.com/send"),
    },
    "linkedin.com": {
        # Only keep company profile pages (in.linkedin.com/company/X or linkedin.com/company/X)
        # Strip out everything else: jobs, signup, login, legal, posts, showcase,
        # psettings, pub, uas, learning, /in/ personal profiles, etc.
        "reject": re.compile(
            r"/(jobs/|signup|login|legal|learning|posts/|psettings|pub/|uas/|"
            r"top-content|games|accessibility|redir/|showcase/|feed/|in/[^c])",
            re.IGNORECASE,
        ),
        "require": re.compile(
            r"linkedin\.com/company/[A-Za-z0-9_\-]+/?(\?.*)?$"
        ),
    },
}


def is_valid_social_url(href: str) -> bool:
    """Return True only if href is a clean social profile/channel URL."""
    href = href.strip()
    for domain, rules in SOCIAL_PLATFORMS.items():
        if domain in href:
            if not rules["require"].search(href):
                return False
            if rules["reject"].search(href):
                return False
            return True
    return False


# ---------------------------------------------------------------------------
# Pages to crawl
# ---------------------------------------------------------------------------

# Primary targets — contact & about pages only
PRIMARY_PAGE_KEYWORDS = ["contact", "contact-us", "about", "about-us"]

# Fallback targets — nav links and footer links
FALLBACK_PAGE_KEYWORDS = ["reach-us", "support", "help", "company", "team"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def normalize_domain(domain: str) -> str:
    domain = domain.strip()
    if not domain.startswith(("http://", "https://")):
        domain = "https://" + domain
    return domain


def fetch_html(url: str) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        response.raise_for_status()
        return response.text
    except Exception:
        return ""


def clean_phone(phone: str):
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 9 or len(digits) > 15:
        return None
    return digits


def extract_emails(text: str) -> set:
    emails = set()
    for email in EMAIL_REGEX.findall(text):
        email = email.lower().strip()
        if email and not email.endswith((".png", ".jpg", ".gif", ".svg", ".webp")):
            emails.add(email)
    return emails


def extract_phones(text: str) -> set:
    phones = set()
    for match in PHONE_REGEX.findall(text):
        phone = clean_phone(match)
        if phone:
            phones.add(phone)
    return phones


def extract_socials(soup: BeautifulSoup) -> set:
    socials = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if is_valid_social_url(href):
            # Normalise: strip query params for non-linkedin links
            parsed = urlparse(href)
            if "linkedin.com" not in href:
                href = parsed._replace(query="", fragment="").geturl()
            socials.add(href)
    return socials


def clean_address_candidate(raw: str):
    text = raw
    for pattern in ADDRESS_NOISE_PATTERNS:
        text = pattern.sub("", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = text.strip(" ,;:-")
    if len(text) < 20:
        return None
    if not ADDRESS_KEYWORDS.search(text) and not PINCODE_REGEX.search(text):
        return None
    return text


def extract_address_candidates(text: str) -> set:
    addresses = set()
    for fragment in re.split(r"\n+|\bGet directions\b", text, flags=re.IGNORECASE):
        fragment = " ".join(fragment.split())
        if not fragment:
            continue

        matches = list(PINCODE_REGEX.finditer(fragment))
        if len(matches) != 1:
            continue

        match = matches[0]
        start = max(0, match.start() - 160)
        end = min(len(fragment), match.end() + 70)
        raw = fragment[start:end]
        cleaned = clean_address_candidate(raw)
        if cleaned and len(cleaned) <= 220:
            addresses.add(cleaned)
    return addresses


def extract_footer_nav_text(soup: BeautifulSoup) -> str:
    """Pull text from <footer>, <nav>, and elements whose id/class suggests footer."""
    parts = []

    for tag in soup.find_all(["footer", "nav"]):
        parts.append(tag.get_text("\n", strip=True))

    for tag in soup.find_all(True):
        tag_id = tag.get("id", "").lower()
        tag_class = " ".join(tag.get("class", [])).lower()
        combined = tag_id + " " + tag_class
        if any(kw in combined for kw in ("footer", "contact-info", "contact_info", "address", "reach-us")):
            parts.append(tag.get_text("\n", strip=True))

    return "\n".join(parts)


def find_pages_by_keywords(base_url: str, soup: BeautifulSoup, keywords: list) -> set:
    pages = set()
    for tag in soup.find_all("a", href=True):
        href = tag["href"].lower()
        if any(word in href for word in keywords):
            pages.add(urljoin(base_url, href))
    return pages


def is_empty_result(result: dict) -> bool:
    return not any(result[k] for k in ("emails", "phones", "socials", "addresses"))


# ---------------------------------------------------------------------------
# Page processor
# ---------------------------------------------------------------------------

def process_page(url: str, include_footer: bool = False) -> dict:
    result = {"emails": set(), "phones": set(), "socials": set(), "addresses": set()}

    html = fetch_html(url)
    if not html:
        return result

    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text("\n", strip=True)

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

    # Address: always include footer text on contact/about pages;
    # on fallback pages use footer+nav text only
    if include_footer:
        footer_text = extract_footer_nav_text(soup)
        address_source = footer_text + "\n" + full_text
    else:
        address_source = full_text

    result["addresses"].update(extract_address_candidates(address_source))
    return result


def merge(final: dict, data: dict):
    for key in ("emails", "phones", "socials", "addresses"):
        final[key].update(data[key])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def extract_contact_details(domain: str) -> dict:
    base_url = normalize_domain(domain)

    final = {"emails": set(), "phones": set(), "socials": set(), "addresses": set()}

    # Step 1 — fetch homepage to discover links
    homepage_html = fetch_html(base_url)
    if not homepage_html:
        return {"error": "Unable to fetch website"}

    homepage_soup = BeautifulSoup(homepage_html, "lxml")

    # Always scan the homepage first so partial results still get the site's
    # own contact blocks even when contact/about pages only expose some fields.
    merge(final, process_page(base_url, include_footer=True))

    # Step 2 — crawl contact + about pages only
    primary_pages = find_pages_by_keywords(base_url, homepage_soup, PRIMARY_PAGE_KEYWORDS)

    print(f"[Primary] Found {len(primary_pages)} page(s): contact / about")
    for page in primary_pages:
        print("  Scanning:", page)
        merge(final, process_page(page, include_footer=True))

    # Step 3 — also scan a small set of fallback pages from nav/footer.
    fallback_pages = find_pages_by_keywords(base_url, homepage_soup, FALLBACK_PAGE_KEYWORDS)
    if fallback_pages:
        print(f"[Fallback] Found {len(fallback_pages)} page(s): nav/footer")
    for page in fallback_pages:
        print("  Scanning (fallback):", page)
        merge(final, process_page(page, include_footer=True))

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