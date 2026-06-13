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

PINCODE_REGEX = re.compile(r"\b[1-9]\d{4,5}\b")

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
        "reject": re.compile(r"^$"),
        "require": re.compile(r"wa\.me/\d+"),
    },
    "api.whatsapp.com": {
        "reject": re.compile(r"^$"),
        "require": re.compile(r"api\.whatsapp\.com/send"),
    },
    "linkedin.com": {
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
# Document file types to report (no download — link-only)
# ---------------------------------------------------------------------------

DOCUMENT_EXTENSIONS = re.compile(
    r"\.(pdf|docx?|xlsx?|pptx?|ppt|xls|csv|txt|rtf|odt|ods|odp)$",
    re.IGNORECASE,
)

# Human-readable label for each extension group
EXT_TYPE_MAP = {
    "pdf":  "PDF",
    "doc":  "Word Document",
    "docx": "Word Document",
    "xls":  "Excel Spreadsheet",
    "xlsx": "Excel Spreadsheet",
    "ppt":  "Presentation",
    "pptx": "Presentation",
    "csv":  "CSV",
    "txt":  "Text File",
    "rtf":  "Rich Text",
    "odt":  "OpenDocument Text",
    "ods":  "OpenDocument Spreadsheet",
    "odp":  "OpenDocument Presentation",
}


# ---------------------------------------------------------------------------
# Pages to crawl
# ---------------------------------------------------------------------------

PRIMARY_PAGE_KEYWORDS  = ["contact", "contact-us", "about", "about-us"]
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
            parsed = urlparse(href)
            if "linkedin.com" not in href:
                href = parsed._replace(query="", fragment="").geturl()
            socials.add(href)
    return socials


def clean_address_candidate(raw: str):
    text = raw
    for pattern in ADDRESS_NOISE_PATTERNS:
        text = pattern.sub("", text)
    text = re.sub(r",\s*,", ",", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = text.strip(" ,;:-")
    if len(text) < 20:
        return None
    if not ADDRESS_KEYWORDS.search(text) and not PINCODE_REGEX.search(text):
        return None
    return text


def extract_address_candidates(text: str) -> set:
    addresses = set()
    lines = text.splitlines()

    for i, line in enumerate(lines):
        for match in PINCODE_REGEX.finditer(line):
            start_idx = match.start()
            prefix = line[max(0, start_idx - 10):start_idx].lower()
            if any(kw in prefix for kw in ["imts", "roll", "ref", "id"]):
                continue

            addr_lines = []
            for j in range(i, max(-1, i - 10), -1):
                curr_line = lines[j].strip()
                if not curr_line:
                    continue
                if len(curr_line) > 200:
                    break

                lower_line = curr_line.lower()
                if any(kw in lower_line for kw in [
                    "phone", "email", "working hours", "follow us",
                    "website", "links", "copyright", "lunch break",
                    "visit us",
                ]):
                    break

                if any(kw == lower_line for kw in [
                    "home", "courses", "services", "blog", "gallery",
                    "careers", "about us", "contact us", "our media",
                    "quick links", "find us", "get in touch",
                ]):
                    break

                if j != i and PINCODE_REGEX.search(curr_line):
                    break

                addr_lines.insert(0, curr_line)
                if lower_line == "address":
                    if addr_lines and addr_lines[0].lower() == "address":
                        addr_lines.pop(0)
                    break
                if len(addr_lines) >= 5:
                    break

            if addr_lines:
                full_addr = ", ".join(addr_lines)
                cleaned = clean_address_candidate(full_addr)
                if cleaned and len(cleaned) <= 250:
                    addresses.add(cleaned)
    return addresses


def extract_footer_nav_text(soup: BeautifulSoup) -> str:
    parts = []
    for tag in soup.find_all(["footer", "nav"]):
        parts.append(tag.get_text("\n", strip=True))
    for tag in soup.find_all(True):
        tag_id    = tag.get("id", "").lower()
        tag_class = " ".join(tag.get("class", [])).lower()
        combined  = tag_id + " " + tag_class
        if any(kw in combined for kw in (
            "footer", "contact-info", "contact_info", "address", "reach-us"
        )):
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
# Document link discovery (no download — link collection only)
# ---------------------------------------------------------------------------

def get_extension(url: str) -> str:
    path = urlparse(url).path
    m = DOCUMENT_EXTENSIONS.search(path)
    return m.group(1).lower() if m else ""


def discover_document_links(base_url: str, soup: BeautifulSoup) -> list:
    """
    Collect all publicly linked document URLs from a page.
    Returns list of dicts: {url, fileType, linkedText}.
    No files are downloaded.
    """
    seen = set()
    records = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        path = urlparse(href).path
        if not DOCUMENT_EXTENSIONS.search(path):
            continue

        abs_url = urljoin(base_url, href)
        if abs_url in seen:
            continue
        seen.add(abs_url)

        ext       = get_extension(abs_url)
        file_type = EXT_TYPE_MAP.get(ext, ext.upper())
        link_text = tag.get_text(strip=True) or ""

        record = {
            "url":      abs_url,
            "fileType": file_type,
        }
        if link_text:
            record["linkedText"] = link_text

        records.append(record)

    return records


# ---------------------------------------------------------------------------
# Page processor
# ---------------------------------------------------------------------------

def process_page(url: str, include_footer: bool = False) -> dict:
    result = {
        "emails":    set(),
        "phones":    set(),
        "socials":   set(),
        "addresses": set(),
        "doc_links": [],
    }

    html = fetch_html(url)
    if not html:
        return result

    soup = BeautifulSoup(html, "lxml")
    full_text = soup.get_text("\n", strip=True)

    result["emails"].update(extract_emails(full_text))
    result["phones"].update(extract_phones(full_text))
    result["socials"].update(extract_socials(soup))
    result["doc_links"].extend(discover_document_links(url, soup))

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").strip().lower()
            if email:
                result["emails"].add(email)

    if include_footer:
        footer_text    = extract_footer_nav_text(soup)
        address_source = footer_text + "\n" + full_text
    else:
        address_source = full_text

    result["addresses"].update(extract_address_candidates(address_source))
    return result


def merge(final: dict, data: dict):
    for key in ("emails", "phones", "socials", "addresses"):
        final[key].update(data[key])
    # Deduplicate doc_links by URL
    seen_urls = {d["url"] for d in final["doc_links"]}
    for doc in data["doc_links"]:
        if doc["url"] not in seen_urls:
            seen_urls.add(doc["url"])
            final["doc_links"].append(doc)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def extract_contact_details(domain: str) -> dict:
    base_url = normalize_domain(domain)

    final = {
        "emails":    set(),
        "phones":    set(),
        "socials":   set(),
        "addresses": set(),
        "doc_links": [],
    }

    # Step 1 — homepage
    homepage_html = fetch_html(base_url)
    if not homepage_html:
        return {"error": "Unable to fetch website"}

    homepage_soup = BeautifulSoup(homepage_html, "lxml")
    merge(final, process_page(base_url, include_footer=True))

    # Step 2 — contact / about pages
    primary_pages = find_pages_by_keywords(base_url, homepage_soup, PRIMARY_PAGE_KEYWORDS)
    print(f"[Primary] Found {len(primary_pages)} page(s): contact / about")
    for page in primary_pages:
        print("  Scanning:", page)
        merge(final, process_page(page, include_footer=True))

    # Step 3 — fallback nav/footer pages
    fallback_pages = find_pages_by_keywords(base_url, homepage_soup, FALLBACK_PAGE_KEYWORDS)
    if fallback_pages:
        print(f"[Fallback] Found {len(fallback_pages)} page(s): nav/footer")
    for page in fallback_pages:
        print("  Scanning (fallback):", page)
        merge(final, process_page(page, include_footer=True))

    # Group discovered documents by type
    doc_links = final["doc_links"]
    grouped   = {}
    for doc in doc_links:
        ft = doc["fileType"]
        grouped.setdefault(ft, []).append({
            k: v for k, v in doc.items() if k != "fileType"
        })

    print(f"[Documents] Discovered {len(doc_links)} publicly linked file(s)")

    return {
        "emails":      sorted(final["emails"]),
        "phones":      sorted(final["phones"]),
        "socialLinks": sorted(final["socials"]),
        "addresses":   sorted(final["addresses"]),
        "exposedDocuments": {
            "totalFound": len(doc_links),
            "byType": grouped,
        },
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    domain = input("Enter domain: ").strip()
    result = extract_contact_details(domain)
    print("\n" + json.dumps(result, indent=2, ensure_ascii=False))