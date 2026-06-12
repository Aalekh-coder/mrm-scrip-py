
import re
import io
import os
import json
import struct
import zipfile
import requests
import xml.etree.ElementTree as ET

from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DOCUMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".ppt", ".pptx", ".txt", ".csv", ".json",
    ".odt", ".ods", ".odp", ".rtf",
}

# Common paths where documents are publicly exposed
COMMON_EXPOSED_PATHS = [
    "/sitemap.xml",
    "/robots.txt",
    "/uploads/",
    "/docs/",
    "/documents/",
    "/files/",
    "/reports/",
    "/assets/",
    "/downloads/",
    "/media/",
    "/static/",
    "/public/",
    "/wp-content/uploads/",
    "/wp-content/plugins/",
    "/sites/default/files/",
    "/.well-known/",
    "/backup/",
    "/data/",
]

EMAIL_REGEX = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_REGEX = re.compile(r"(?:\+?\d[\s\-]?){8,13}")

MAX_FILE_SIZE_MB = 20  # skip files larger than this
MAX_PAGES_TO_CRAWL = 50
REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch(url: str, stream: bool = False):
    try:
        r = requests.get(
            url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
            allow_redirects=True, stream=stream,
        )
        if r.status_code == 200:
            return r
    except Exception:
        pass
    return None


def head(url: str):
    try:
        r = requests.head(
            url, headers=HEADERS, timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        return r
    except Exception:
        return None


def normalize(domain: str) -> str:
    domain = domain.strip()
    if not domain.startswith(("http://", "https://")):
        domain = "https://" + domain
    return domain.rstrip("/")


def same_domain(url: str, base: str) -> bool:
    base_host = urlparse(base).netloc.lower().lstrip("www.")
    url_host = urlparse(url).netloc.lower().lstrip("www.")
    return url_host == base_host or url_host.endswith("." + base_host)


def is_document_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in DOCUMENT_EXTENSIONS)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def crawl_for_document_links(base_url: str) -> set:
    """
    Crawl up to MAX_PAGES_TO_CRAWL HTML pages on the domain and collect
    every link that points to a document file.
    """
    visited = set()
    to_visit = {base_url}
    doc_urls = set()

    while to_visit and len(visited) < MAX_PAGES_TO_CRAWL:
        url = to_visit.pop()
        if url in visited:
            continue
        visited.add(url)

        r = fetch(url)
        if not r:
            continue

        content_type = r.headers.get("Content-Type", "")
        if "html" not in content_type:
            continue

        soup = BeautifulSoup(r.text, "lxml")

        for tag in soup.find_all("a", href=True):
            href = tag["href"].strip()
            if not href or href.startswith(("#", "mailto:", "javascript:")):
                continue

            full = urljoin(url, href)
            if not same_domain(full, base_url):
                continue

            if is_document_url(full):
                doc_urls.add(full)
            elif full not in visited:
                to_visit.add(full)

    return doc_urls


def probe_common_paths(base_url: str) -> set:
    """
    Probe well-known exposed paths for documents or directory listings.
    Also parse sitemap.xml and robots.txt for additional URLs.
    """
    found = set()

    for path in COMMON_EXPOSED_PATHS:
        url = base_url + path
        r = fetch(url)
        if not r:
            continue

        content_type = r.headers.get("Content-Type", "")

        # Directory listing (Apache/Nginx style)
        if "html" in content_type:
            soup = BeautifulSoup(r.text, "lxml")
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                full = urljoin(url, href)
                if is_document_url(full) and same_domain(full, base_url):
                    found.add(full)

        # sitemap.xml
        if "xml" in content_type or path.endswith(".xml"):
            try:
                root = ET.fromstring(r.text)
                ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
                for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
                    if loc.text and is_document_url(loc.text.strip()):
                        found.add(loc.text.strip())
            except ET.ParseError:
                pass

        # robots.txt — look for Disallow/Allow paths pointing to docs
        if path == "/robots.txt" and "text" in content_type:
            for line in r.text.splitlines():
                line = line.strip()
                if line.lower().startswith(("disallow:", "allow:")):
                    part = line.split(":", 1)[1].strip()
                    if part and any(part.lower().endswith(ext) for ext in DOCUMENT_EXTENSIONS):
                        found.add(urljoin(base_url, part))

    return found


# ---------------------------------------------------------------------------
# File download (size-limited)
# ---------------------------------------------------------------------------

def download_file(url: str):
    """Download up to MAX_FILE_SIZE_MB; return bytes or None."""
    r = fetch(url, stream=True)
    if not r:
        return None

    content_length = int(r.headers.get("Content-Length", 0))
    if content_length > MAX_FILE_SIZE_MB * 1024 * 1024:
        return None  # too large

    chunks = []
    total = 0
    for chunk in r.iter_content(chunk_size=65536):
        total += len(chunk)
        if total > MAX_FILE_SIZE_MB * 1024 * 1024:
            return None
        chunks.append(chunk)

    return b"".join(chunks)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

def extract_contacts_from_text(text: str) -> dict:
    emails = set(EMAIL_REGEX.findall(text.lower()))
    raw_phones = PHONE_REGEX.findall(text)
    phones = set()
    for p in raw_phones:
        digits = re.sub(r"\D", "", p)
        if 10 <= len(digits) <= 15:
            phones.add(digits)
    return {"emails": sorted(emails), "phones": sorted(phones)}


# ---------------------------------------------------------------------------
# Metadata extractors — one per file type
# ---------------------------------------------------------------------------

def extract_pdf_metadata(data: bytes) -> dict:
    meta = {}
    text_sample = ""

    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(io.BytesIO(data))
        info = reader.metadata or {}

        field_map = {
            "/Author":       "author",
            "/Creator":      "creator_tool",
            "/Producer":     "producer",
            "/Title":        "title",
            "/Subject":      "subject",
            "/Keywords":     "keywords",
            "/CreationDate": "created",
            "/ModDate":      "modified",
        }
        for pdf_key, our_key in field_map.items():
            val = info.get(pdf_key)
            if val:
                meta[our_key] = str(val).strip()

        # Extract first ~3000 chars of text for contact mining
        pages_text = []
        for i, page in enumerate(reader.pages):
            if i >= 5:
                break
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:
                pass
        text_sample = " ".join(pages_text)

    except ImportError:
        # Fallback: raw byte scan for metadata markers
        raw = data.decode("latin-1", errors="replace")
        for marker in ("/Author", "/Creator", "/Producer", "/Title"):
            m = re.search(re.escape(marker) + r"\s*\(([^)]{1,200})\)", raw)
            if m:
                meta[marker.lstrip("/").lower()] = m.group(1).strip()
        text_sample = raw[:5000]

    except Exception:
        pass

    contacts = extract_contacts_from_text(text_sample)
    if contacts["emails"]:
        meta["emails_in_document"] = contacts["emails"]
    if contacts["phones"]:
        meta["phones_in_document"] = contacts["phones"]

    return meta


def _parse_ooxml_core_props(zf: zipfile.ZipFile) -> dict:
    """Parse docProps/core.xml from an OOXML zip (docx/xlsx/pptx)."""
    meta = {}
    try:
        with zf.open("docProps/core.xml") as f:
            root = ET.parse(f).getroot()

        ns = {
            "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
            "dc": "http://purl.org/dc/elements/1.1/",
            "dcterms": "http://purl.org/dc/terms/",
        }
        field_map = {
            "dc:creator":          "author",
            "cp:lastModifiedBy":   "last_modified_by",
            "dc:title":            "title",
            "dc:subject":          "subject",
            "dc:description":      "description",
            "cp:keywords":         "keywords",
            "dcterms:created":     "created",
            "dcterms:modified":    "modified",
            "cp:revision":         "revision",
        }
        for tag_path, key in field_map.items():
            prefix, local = tag_path.split(":")
            el = root.find(f"{{{ns[prefix]}}}{local}")
            if el is not None and el.text:
                meta[key] = el.text.strip()
    except Exception:
        pass
    return meta


def _parse_ooxml_app_props(zf: zipfile.ZipFile) -> dict:
    """Parse docProps/app.xml — reveals creating application + version."""
    meta = {}
    try:
        with zf.open("docProps/app.xml") as f:
            root = ET.parse(f).getroot()
        ns = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
        for tag in ("Application", "AppVersion", "Company", "Manager"):
            el = root.find(f"{{{ns}}}{tag}")
            if el is not None and el.text:
                meta[tag.lower()] = el.text.strip()
    except Exception:
        pass
    return meta


def _extract_text_from_ooxml(zf: zipfile.ZipFile, xml_paths: list) -> str:
    """Extract plain text from given XML parts inside the zip."""
    texts = []
    for path in xml_paths:
        try:
            with zf.open(path) as f:
                root = ET.parse(f).getroot()
            texts.append(" ".join(root.itertext()))
        except Exception:
            pass
    return " ".join(texts)


def extract_docx_metadata(data: bytes) -> dict:
    meta = {}
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        meta.update(_parse_ooxml_core_props(zf))
        meta.update(_parse_ooxml_app_props(zf))
        text = _extract_text_from_ooxml(zf, ["word/document.xml"])
        contacts = extract_contacts_from_text(text)
        if contacts["emails"]:
            meta["emails_in_document"] = contacts["emails"]
        if contacts["phones"]:
            meta["phones_in_document"] = contacts["phones"]
    except Exception:
        pass
    return meta


def extract_xlsx_metadata(data: bytes) -> dict:
    meta = {}
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        meta.update(_parse_ooxml_core_props(zf))
        meta.update(_parse_ooxml_app_props(zf))
        sheet_paths = [n for n in zf.namelist() if n.startswith("xl/worksheets/sheet")]
        text = _extract_text_from_ooxml(zf, sheet_paths[:5])
        contacts = extract_contacts_from_text(text)
        if contacts["emails"]:
            meta["emails_in_document"] = contacts["emails"]
        if contacts["phones"]:
            meta["phones_in_document"] = contacts["phones"]
    except Exception:
        pass
    return meta


def extract_pptx_metadata(data: bytes) -> dict:
    meta = {}
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        meta.update(_parse_ooxml_core_props(zf))
        meta.update(_parse_ooxml_app_props(zf))
        slide_paths = sorted(n for n in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml", n))
        text = _extract_text_from_ooxml(zf, slide_paths[:10])
        contacts = extract_contacts_from_text(text)
        if contacts["emails"]:
            meta["emails_in_document"] = contacts["emails"]
        if contacts["phones"]:
            meta["phones_in_document"] = contacts["phones"]
    except Exception:
        pass
    return meta


def extract_legacy_office_metadata(data: bytes) -> dict:
    """
    Best-effort metadata from legacy .doc/.xls/.ppt (OLE2 Compound Document).
    Scans for printable strings near property markers — no external library needed.
    """
    meta = {}
    try:
        text = data.decode("latin-1", errors="replace")
        for label in ("Author", "LastAuthor", "AppName", "Title", "Subject", "Keywords", "Company"):
            # OLE2 stores these as length-prefixed or null-terminated strings
            pattern = re.compile(re.escape(label) + r".{0,4}([A-Za-z0-9 ._@\-]{3,80})")
            m = pattern.search(text)
            if m:
                val = m.group(1).strip()
                if val:
                    meta[label.lower()] = val

        contacts = extract_contacts_from_text(text[:10000])
        if contacts["emails"]:
            meta["emails_in_document"] = contacts["emails"]
        if contacts["phones"]:
            meta["phones_in_document"] = contacts["phones"]
    except Exception:
        pass
    return meta


def extract_text_metadata(data: bytes) -> dict:
    """For .txt / .csv / .json — just mine contacts."""
    meta = {}
    try:
        text = data.decode("utf-8", errors="replace")
        contacts = extract_contacts_from_text(text)
        if contacts["emails"]:
            meta["emails_in_document"] = contacts["emails"]
        if contacts["phones"]:
            meta["phones_in_document"] = contacts["phones"]
    except Exception:
        pass
    return meta


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def extract_metadata(url: str, data: bytes) -> dict:
    path = urlparse(url).path.lower()
    ext = os.path.splitext(path)[1]

    if ext == ".pdf":
        return extract_pdf_metadata(data)
    elif ext == ".docx":
        return extract_docx_metadata(data)
    elif ext == ".xlsx":
        return extract_xlsx_metadata(data)
    elif ext == ".pptx":
        return extract_pptx_metadata(data)
    elif ext in (".doc", ".xls", ".ppt"):
        return extract_legacy_office_metadata(data)
    elif ext in (".txt", ".csv", ".json", ".rtf"):
        return extract_text_metadata(data)
    else:
        return {}


# ---------------------------------------------------------------------------
# HTTP-level metadata (from response headers)
# ---------------------------------------------------------------------------

def http_metadata(url: str, response) -> dict:
    meta = {
        "url": url,
        "file_name": os.path.basename(urlparse(url).path),
        "extension": os.path.splitext(urlparse(url).path)[1].lower(),
    }

    headers = response.headers if response else {}

    if "Content-Type" in headers:
        meta["content_type"] = headers["Content-Type"]
    if "Content-Length" in headers:
        try:
            meta["size_bytes"] = int(headers["Content-Length"])
            meta["size_kb"] = round(meta["size_bytes"] / 1024, 1)
        except ValueError:
            pass
    if "Last-Modified" in headers:
        meta["last_modified"] = headers["Last-Modified"]
    if "Server" in headers:
        meta["server"] = headers["Server"]
    if "X-Powered-By" in headers:
        meta["powered_by"] = headers["X-Powered-By"]

    return meta


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def scrape_documents(domain: str) -> dict:
    base_url = normalize(domain)
    domain_label = urlparse(base_url).netloc

    print(f"\n{'='*60}")
    print(f"  Target : {base_url}")
    print(f"{'='*60}\n")

    # --- Discovery ---
    print("[1/3] Crawling pages for document links...")
    crawled_docs = crawl_for_document_links(base_url)
    print(f"      Found {len(crawled_docs)} document link(s) via crawl")

    print("[2/3] Probing common exposed paths...")
    probed_docs = probe_common_paths(base_url)
    print(f"      Found {len(probed_docs)} document link(s) via path probing")

    all_doc_urls = crawled_docs | probed_docs
    print(f"\n      Total unique documents to process: {len(all_doc_urls)}\n")

    # --- Download + extract ---
    print("[3/3] Downloading and extracting metadata...\n")
    results = []
    skipped = []

    for url in sorted(all_doc_urls):
        print(f"  → {url}")

        # HEAD first to check size and get HTTP metadata without full download
        head_resp = head(url)
        base_meta = http_metadata(url, head_resp)

        size_bytes = base_meta.get("size_bytes", 0)
        if size_bytes > MAX_FILE_SIZE_MB * 1024 * 1024:
            print(f"    ⚠ Skipped (too large: {size_bytes // (1024*1024)} MB)")
            skipped.append({"url": url, "reason": "file too large"})
            continue

        data = download_file(url)
        if not data:
            print(f"    ⚠ Skipped (download failed or too large)")
            skipped.append({"url": url, "reason": "download failed"})
            continue

        # Update size from actual download if HEAD didn't have it
        if "size_bytes" not in base_meta:
            base_meta["size_bytes"] = len(data)
            base_meta["size_kb"] = round(len(data) / 1024, 1)

        doc_meta = extract_metadata(url, data)
        combined = {**base_meta, **doc_meta}
        results.append(combined)

        # Print summary
        interesting = {k: v for k, v in doc_meta.items() if v}
        if interesting:
            for k, v in interesting.items():
                print(f"    {k}: {v}")
        else:
            print(f"    (no metadata extracted)")

    # --- Summary report ---
    report = {
        "domain": domain_label,
        "scanned_at": datetime.utcnow().isoformat() + "Z",
        "total_documents_found": len(all_doc_urls),
        "total_processed": len(results),
        "total_skipped": len(skipped),
        "documents": results,
        "skipped": skipped,
    }

    # Aggregate all leaked emails/phones across all documents
    all_emails = set()
    all_phones = set()
    all_authors = set()
    all_tools = set()

    for doc in results:
        all_emails.update(doc.get("emails_in_document", []))
        all_phones.update(doc.get("phones_in_document", []))
        for field in ("author", "last_modified_by"):
            if doc.get(field):
                all_authors.add(doc[field])
        for field in ("creator_tool", "producer", "application"):
            if doc.get(field):
                all_tools.add(doc[field])

    report["summary"] = {
        "unique_emails_leaked": sorted(all_emails),
        "unique_phones_leaked": sorted(all_phones),
        "authors_found": sorted(all_authors),
        "software_versions_leaked": sorted(all_tools),
    }

    return report


def print_report(report: dict):
    sep = "=" * 60
    thin = "-" * 60

    print(f"\n{sep}")
    print(f"  Domain   : {report['domain']}")
    print(f"  Scanned  : {report['scanned_at']}")
    print(f"  Found    : {report['total_documents_found']}  |  "
          f"Processed: {report['total_processed']}  |  "
          f"Skipped: {report['total_skipped']}")
    print(sep)

    # --- Per-document details ---
    for i, doc in enumerate(report["documents"], 1):
        print(f"\n[{i}] {doc.get('file_name', 'unknown')}  ({doc.get('extension', '').upper().lstrip('.')})")
        print(f"    URL          : {doc.get('url', '')}")

        if doc.get("size_kb"):
            print(f"    Size         : {doc['size_kb']} KB")
        if doc.get("content_type"):
            print(f"    Content-Type : {doc['content_type']}")
        if doc.get("last_modified"):
            print(f"    Last-Modified: {doc['last_modified']}")
        if doc.get("server"):
            print(f"    Server       : {doc['server']}")
        if doc.get("powered_by"):
            print(f"    Powered-By   : {doc['powered_by']}")

        # Document-internal metadata
        internal_fields = [
            ("title",            "Title"),
            ("author",           "Author"),
            ("last_modified_by", "Last Modified By"),
            ("subject",          "Subject"),
            ("keywords",         "Keywords"),
            ("description",      "Description"),
            ("created",          "Created"),
            ("modified",         "Modified"),
            ("revision",         "Revision"),
            ("creator_tool",     "Creator Tool"),
            ("producer",         "Producer"),
            ("application",      "Application"),
            ("appversion",       "App Version"),
            ("company",          "Company"),
            ("manager",          "Manager"),
        ]
        for key, label in internal_fields:
            if doc.get(key):
                print(f"    {label:<18}: {doc[key]}")

        if doc.get("emails_in_document"):
            print(f"    Emails found : {', '.join(doc['emails_in_document'])}")
        if doc.get("phones_in_document"):
            print(f"    Phones found : {', '.join(doc['phones_in_document'])}")

    # --- Skipped files ---
    if report["skipped"]:
        print(f"\n{thin}")
        print("  Skipped files:")
        for s in report["skipped"]:
            print(f"    ✗ {s['url']}  ({s['reason']})")

    # --- Aggregated summary ---
    s = report["summary"]
    print(f"\n{sep}")
    print("  SUMMARY")
    print(sep)

    if s["unique_emails_leaked"]:
        print("  Emails leaked across all documents:")
        for e in s["unique_emails_leaked"]:
            print(f"    • {e}")
    else:
        print("  Emails leaked       : none found")

    if s["unique_phones_leaked"]:
        print("  Phones leaked across all documents:")
        for p in s["unique_phones_leaked"]:
            print(f"    • {p}")
    else:
        print("  Phones leaked       : none found")

    if s["authors_found"]:
        print("  Authors / editors found:")
        for a in s["authors_found"]:
            print(f"    • {a}")
    else:
        print("  Authors found       : none found")

    if s["software_versions_leaked"]:
        print("  Software versions leaked:")
        for t in s["software_versions_leaked"]:
            print(f"    • {t}")
    else:
        print("  Software versions   : none found")

    print(f"{sep}\n")


if __name__ == "__main__":
    domain = input("Enter domain: ").strip()
    if not domain:
        print("No domain entered.")
        exit(1)

    report = scrape_documents(domain)
    print_report(report)