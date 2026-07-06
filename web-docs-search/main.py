import json
import time
import sys
import re
import random
from urllib.parse import urlparse, unquote

try:
    import requests
except ImportError:
    print("Install with:  pip install requests")
    sys.exit(1)



SERPAPI_KEY      = "c4c3d45597f73f0c10649f77fd02ecda35ea8a58bff0c9878288ef8f1dd0f2c8"  
RESULTS_PER_TYPE = 10    # max results per file type (1 API call = 10 results)
PAUSE_SECONDS    = 1     # seconds between API calls (SerpApi has no strict limit)

FILE_TYPES = [
    "pdf", "docx", "doc",
    "xlsx", "xls",
    "pptx", "ppt",
    "csv", "txt",
    "odt", "ods", "odp",
]

TYPE_LABELS = {
    "pdf":  "PDF Document",
    "docx": "Word Document",
    "doc":  "Word Document (Legacy)",
    "xlsx": "Excel Spreadsheet",
    "xls":  "Excel Spreadsheet (Legacy)",
    "pptx": "PowerPoint Presentation",
    "ppt":  "PowerPoint (Legacy)",
    "csv":  "CSV File",
    "txt":  "Text File",
    "odt":  "OpenDocument Text",
    "ods":  "OpenDocument Spreadsheet",
    "odp":  "OpenDocument Presentation",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalize(domain: str) -> str:
    domain = domain.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    return domain.rstrip("/")


def get_ext(url: str) -> str:
    try:
        path = urlparse(url).path
        if "." in path:
            ext = path.rsplit(".", 1)[-1].lower().split("?")[0]
            return ext if len(ext) <= 5 else ""
    except Exception:
        pass
    return ""


def get_filename(url: str) -> str:
    try:
        name = urlparse(url).path.split("/")[-1]
        return unquote(name) if name else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# SerpApi call
# ---------------------------------------------------------------------------

def serpapi_search(query: str, api_key: str, num: int = 10) -> tuple:
    """
    Call SerpApi Google Search endpoint.
    Returns (list_of_urls, error_string_or_None)
    """
    params = {
        "engine":  "google",
        "q":       query,
        "num":     num,
        "hl":      "en",
        "gl":      "us",
        "api_key": api_key,
    }

    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params=params,
            timeout=20,
        )

        if resp.status_code == 401:
            return [], "Invalid API key — check SERPAPI_KEY"

        if resp.status_code == 429:
            return [], "Monthly limit reached — upgrade plan or wait"

        if resp.status_code != 200:
            return [], f"HTTP {resp.status_code}"

        data = resp.json()

        # SerpApi error field
        if "error" in data:
            return [], data["error"]

        # Extract URLs from organic_results
        urls = []
        for result in data.get("organic_results", []):
            link = result.get("link", "")
            if link and link.startswith("http"):
                urls.append(link)

        return urls, None

    except requests.exceptions.ConnectionError:
        return [], "No internet connection"
    except Exception as e:
        return [], str(e)


# ---------------------------------------------------------------------------
# Core scraper
# ---------------------------------------------------------------------------

def scrape_domain_docs(domain: str, api_key: str = None) -> dict:
    """
    Main function — searches Google via SerpApi for all file types.

    Returns:
    {
        "searched_domain": "who.int",
        "search_time":     "2024-06-15 14:00:00",
        "total_documents": 47,
        "api_calls_used":  12,
        "by_type": {
            "PDF Document": [
                {
                    "file_name": "annual-report.pdf",
                    "url":       "https://www.who.int/docs/annual-report.pdf",
                    "query":     "site:who.int filetype:pdf"
                }
            ]
        },
        "all_documents": [ ... ]
    }
    """
    key = api_key or SERPAPI_KEY

    if not key or key == "YOUR_API_KEY_HERE":
        print("\n❌  No API key set!")
        print("   1. Go to https://serpapi.com and sign up free")
        print("   2. Copy your API key")
        print("   3. Paste it in SERPAPI_KEY at the top of this script")
        sys.exit(1)

    clean      = normalize(domain)
    all_docs   = []
    by_type    = {}
    seen_urls  = set()
    api_calls  = 0

    print(f"\n🔍 Domain     : {clean}")
    print(f"   Engine     : SerpApi → Google (no CAPTCHA)")
    print(f"   File types : {len(FILE_TYPES)}")
    print(f"   API calls  : up to {len(FILE_TYPES)} (1 per type)")
    print("-" * 58)

    for ft in FILE_TYPES:
        print(f"  [{ft.upper():5s}] Searching ...", end=" ", flush=True)

        query = f"site:{clean} filetype:{ft}"
        urls, err = serpapi_search(query, key, RESULTS_PER_TYPE)
        api_calls += 1

        if err:
            print(f"⚠️  {err}")
            # stop entirely if API key is bad
            if "Invalid API key" in err or "limit reached" in err:
                break
            time.sleep(PAUSE_SECONDS)
            continue

        added = 0
        if urls:
            label = TYPE_LABELS.get(ft, ft.upper())

            for url in urls:
                if url in seen_urls:
                    continue
                seen_urls.add(url)

                ext      = get_ext(url) or ft
                lbl      = TYPE_LABELS.get(ext, label)
                filename = get_filename(url) or url.split("/")[-1]

                by_type.setdefault(lbl, []).append({
                    "file_name": filename,
                    "url":       url,
                    "query":     query,
                })
                all_docs.append({
                    "file_name": filename,
                    "file_type": lbl,
                    "extension": ext,
                    "url":       url,
                    "query":     query,
                })
                added += 1

        print(f"✅ {added} found" if added else "— none")
        time.sleep(PAUSE_SECONDS)

    print("-" * 58)
    print(f"  ✅ Total documents : {len(all_docs)}")
    print(f"  📊 API calls used  : {api_calls}\n")

    return {
        "searched_domain": clean,
        "total_documents": len(all_docs),
        "api_calls_used":  api_calls,
        "by_type":         by_type,
        "all_documents":   all_docs,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════╗")
    print("║   Domain Document Scraper v6 — SerpApi      ║")
    print("║   Real Google results, zero CAPTCHA          ║")
    print("╚══════════════════════════════════════════════╝")

    # Allow passing API key at runtime instead of hardcoding
    api_key = SERPAPI_KEY
    if api_key == "YOUR_API_KEY_HERE":
        api_key = input("\nPaste your SerpApi key (https://serpapi.com): ").strip()

    domain = input("Enter domain (e.g. who.int): ").strip()
    if not domain:
        print("No domain entered.")
        sys.exit(0)

    save = input("Save to JSON file? (Y/n): ").strip().lower()

    result = scrape_domain_docs(domain, api_key=api_key)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    if save != "n":
        slug = result["searched_domain"].replace(".", "_")
        path = f"docs_{slug}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved → {path}")