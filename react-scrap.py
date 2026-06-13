# pip install playwright && playwright install chromium
from playwright.sync_api import sync_playwright

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    )
}

def fetch_html_react(url: str) -> str:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers(HEADERS)
            page.goto(url, wait_until="networkidle", timeout=20000)
            # Wait a bit more for lazy-rendered content
            page.wait_for_timeout(2000)
            html = page.content()
            browser.close()
            return html
    except Exception:
        return ""
    

value = fetch_html("https://promozionebranding.com")

print(value)