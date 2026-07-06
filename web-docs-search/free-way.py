"""
Domain Document Scraper v5 — Multi-Engine
==========================================
Tries 3 search engines in order until one works:
  1. googlesearch-python  (fastest, may get blocked)
  2. Bing HTML scrape     (reliable, no CAPTCHA usually)
  3. DuckDuckGo HTML      (fallback)

Install:
    pip install googlesearch-python requests beautifulsoup4 lxml

Usage:
    python doc_scraper.py
"""

import json, time, sys, re, random
from datetime import datetime
from urllib.parse import urlparse, unquote, quote_plus

# ── dependency check ────────────────────────────────────────────────────────
MISSING = []
try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    MISSING.append("requests beautifulsoup4 lxml")

if MISSING:
    print(f"Install missing packages:  pip install {' '.join(MISSING)}")
    sys.exit(1)

try:
    from googlesearch import search as gsearch
    GOOGLE_LIB = True
except ImportError:
    GOOGLE_LIB = False

# ── CONFIG ──────────────────────────────────────────────────────────────────

RESULTS_PER_TYPE = 10
PAUSE_SECONDS    = 5      # wait between each filetype query
                          # raise to 10-15 if you keep getting blocked

FILE_TYPES = [
    "pdf", "docx", "doc",
    "xlsx", "xls",
    "pptx", "ppt",
    "csv", "txt",
    "odt", "ods", "odp",
]

TYPE_LABELS = {
    "pdf":  "PDF Document",      "docx": "Word Document",
    "doc":  "Word Document",     "xlsx": "Excel Spreadsheet",
    "xls":  "Excel Spreadsheet", "pptx": "PowerPoint",
    "ppt":  "PowerPoint",        "csv":  "CSV File",
    "txt":  "Text File",         "odt":  "OpenDocument Text",
    "ods":  "OpenDocument Spreadsheet", "odp": "OpenDocument Presentation",
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

SKIP = [
    "google.com", "bing.com", "duckduckgo.com", "yahoo.com",
    "youtube.com", "facebook.com", "twitter.com", "instagram.com",
    "amazon.com", "wikipedia.org", "reddit.com", "microsoft.com",
]

# ── helpers ──────────────────────────────────────────────────────────────────

def normalize(domain):
    domain = domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    return domain.rstrip("/")

def get_ext(url):
    try:
        path = urlparse(url).path
        if "." in path:
            e = path.rsplit(".", 1)[-1].lower().split("?")[0]
            return e if len(e) <= 5 else ""
    except Exception:
        pass
    return ""

def get_filename(url):
    try:
        name = urlparse(url).path.split("/")[-1]
        return unquote(name) if name else ""
    except Exception:
        return ""

def should_skip(url):
    return any(s in url for s in SKIP)

def headers():
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
    }

# ── Engine 1: googlesearch-python ────────────────────────────────────────────

def engine_google(query, num):
    if not GOOGLE_LIB:
        return None, "googlesearch-python not installed"
    try:
        results = list(gsearch(query, num_results=num, sleep_interval=2, lang="en"))
        if results:
            return results, None
        return None, "no results"
    except Exception as e:
        return None, str(e)

# ── Engine 2: Bing HTML scrape ───────────────────────────────────────────────

def engine_bing(query, num):
    """
    Scrape Bing search results HTML — Bing is much more tolerant than Google.
    Bing also supports site: and filetype: operators.
    """
    urls    = []
    seen    = set()
    session = requests.Session()

    for page in range(0, min(num, 30), 10):
        try:
            url  = f"https://www.bing.com/search?q={quote_plus(query)}&first={page+1}&count=10"
            resp = session.get(url, headers=headers(), timeout=12)

            if resp.status_code != 200:
                break

            soup = BeautifulSoup(resp.text, "lxml")

            # Bing result links are in <a> inside <li class="b_algo">
            for li in soup.select("li.b_algo"):
                a = li.find("a", href=True)
                if not a:
                    continue
                href = a["href"].strip()
                if not href.startswith("http"):
                    continue
                if should_skip(href):
                    continue
                if href in seen:
                    continue
                seen.add(href)
                urls.append(href)
                if len(urls) >= num:
                    break

            if len(urls) >= num:
                break

            time.sleep(random.uniform(1.5, 3))

        except Exception as e:
            return None, str(e)

    if urls:
        return urls, None
    return None, "no results from Bing"

# ── Engine 3: DuckDuckGo HTML lite ──────────────────────────────────────────

def engine_ddg(query, num):
    """
    DuckDuckGo lite HTML endpoint — very lightweight, rarely blocks.
    """
    urls    = []
    seen    = set()
    session = requests.Session()

    try:
        url  = f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}"
        resp = session.post(
            "https://lite.duckduckgo.com/lite/",
            data={"q": query, "s": "0", "o": "json", "dc": "1", "v": "l", "api": "d.js"},
            headers={**headers(), "Content-Type": "application/x-www-form-urlencoded"},
            timeout=12
        )

        soup = BeautifulSoup(resp.text, "lxml")

        # DDG lite puts results in <a class="result-link">
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # unwrap DDG redirect
            if "uddg=" in href:
                m = re.search(r"uddg=([^&]+)", href)
                if m:
                    href = unquote(m.group(1))
            if not href.startswith("http"):
                continue
            if should_skip(href):
                continue
            if href in seen:
                continue
            seen.add(href)
            urls.append(href)
            if len(urls) >= num:
                break

    except Exception as e:
        return None, str(e)

    if urls:
        return urls, None
    return None, "no results from DDG"

# ── Multi-engine search ──────────────────────────────────────────────────────

ENGINES = [
    ("Google",     engine_google),
    ("Bing",       engine_bing),
    ("DuckDuckGo", engine_ddg),
]

def search_filetype(domain, filetype, num):
    query = f"site:{domain} filetype:{filetype}"

    for engine_name, engine_fn in ENGINES:
        results, err = engine_fn(query, num)
        if results:
            return results, query, engine_name
        # small pause before trying next engine
        time.sleep(1)

    return [], query, "none"


# ── main ─────────────────────────────────────────────────────────────────────

def scrape_domain_docs(domain, results_per_type=RESULTS_PER_TYPE):
    clean  = normalize(domain)
    docs   = []
    bytype = {}
    seen   = set()
    engine_used = None

    print(f"\n🔍 Domain : {clean}")
    print(f"   Limit  : {results_per_type} per type")
    print(f"   Engines: Google → Bing → DuckDuckGo (auto-fallback)")
    print("-" * 58)

    for ft in FILE_TYPES:
        print(f"  [{ft.upper():5s}] Searching ...", end=" ", flush=True)

        urls, query, eng = search_filetype(clean, ft, results_per_type)
        added = 0

        if urls:
            if engine_used != eng:
                engine_used = eng

            label = TYPE_LABELS.get(ft, ft.upper())
            bytype.setdefault(label, [])

            for url in urls:
                if url in seen:
                    continue
                seen.add(url)

                ext  = get_ext(url) or ft
                lbl  = TYPE_LABELS.get(ext, label)
                name = get_filename(url) or url.split("/")[-1]

                bytype.setdefault(lbl, []).append({
                    "file_name": name,
                    "url":       url,
                    "query":     query,
                    "engine":    eng,
                })
                docs.append({
                    "file_name": name,
                    "file_type": lbl,
                    "extension": ext,
                    "url":       url,
                    "query":     query,
                    "engine":    eng,
                })
                added += 1

        status = f"✅ {added} found  [{eng}]" if added else "— none"
        print(status)

        time.sleep(PAUSE_SECONDS + random.uniform(0, 2))

    print("-" * 58)
    print(f"  ✅ Total unique documents: {len(docs)}\n")

    return {
        "searched_domain":  clean,
        "search_time":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_documents":  len(docs),
        "by_type":          bytype,
        "all_documents":    docs,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("╔════════════════════════════════════════════════╗")
    print("║   Domain Document Scraper v5                   ║")
    print("║   Google → Bing → DuckDuckGo  (auto-fallback) ║")
    print("╚════════════════════════════════════════════════╝")

    domain = input("\nEnter domain (e.g. who.int): ").strip()
    if not domain:
        print("No domain entered.")
        sys.exit(0)

    save = input("Save to JSON file? (Y/n): ").strip().lower()

    result = scrape_domain_docs(domain)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if save != "n":
        slug = result["searched_domain"].replace(".", "_")
        path = f"docs_{slug}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved → {path}")