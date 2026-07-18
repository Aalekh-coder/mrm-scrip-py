/**
 * tinyfish-scrape.js
 *
 * 1. Uses TinyFish Search API to get the top 10 results for a query.
 * 2. Uses TinyFish Agent API (run-sse) to visit each result URL and extract:
 *    - email addresses
 *    - phone numbers
 *    - location / address
 *    - links to documents (pdf, ppt/pptx, doc/docx)
 * 3. Prints the combined output as JSON.
 *
 * Requirements: Node.js 18+ (built-in fetch), a TinyFish API key.
 *   export TINYFISH_API_KEY="sk-tinyfish-..."
 *
 * Run:
 *   node tinyfish-scrape.js "your search query"
 */

const TINYFISH_API_KEY = "sk-tinyfish-VfA8OyE4M9N6-1Om_qxUav7HtYpcZOzA";
const SEARCH_URL = "https://api.search.tinyfish.ai";
const AGENT_URL = "https://agent.tinyfish.ai/v1/automation/run-sse";

const RESULT_COUNT = 10;   // how many search results to process
const CONCURRENCY = 2;     // parallel agent runs (match your plan's limit)

if (!TINYFISH_API_KEY) {
  console.error("Missing TINYFISH_API_KEY environment variable.");
  process.exit(1);
}

/** Step 1: get top N Google-style search results via TinyFish Search API */
async function getTopSearchResults(query, count = RESULT_COUNT) {
  const url = `${SEARCH_URL}?query=${encodeURIComponent(query)}`;
  const res = await fetch(url, {
    headers: { "X-API-Key": TINYFISH_API_KEY },
  });

  if (!res.ok) {
    throw new Error(`Search API failed: ${res.status} ${await res.text()}`);
  }

  const data = await res.json();

  // Response shape can vary slightly; normalize common cases.
  const results = data.results || data.items || data;
  if (!Array.isArray(results)) {
    throw new Error("Unexpected search response shape: " + JSON.stringify(data).slice(0, 300));
  }

  return results.slice(0, count).map((r) => ({
    title: r.title || r.name || "",
    url: r.url || r.link,
    snippet: r.snippet || r.description || "",
  }));
}

/** Step 2: run the Agent API against a single URL, parse the SSE stream, return extracted JSON */
async function extractDetailsFromUrl(targetUrl, timeoutMs = 90_000) {
  const goal = `
Extract the following details from this page (and, if needed, an obvious "Contact" or "About" page linked from it). Return ONLY JSON with this exact shape:

{
  "emails": [string],
  "phones": [string],
  "locations": [string],
  "documents": [{"url": string, "type": "pdf" | "ppt" | "doc"}]
}

Rules:
- "documents" = any links pointing to files ending in .pdf, .ppt, .pptx, .doc, or .docx.
- If a field has no data, return an empty array for it.
- Do not invent data that is not present on the page.
`.trim();

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(AGENT_URL, {
      method: "POST",
      headers: {
        "X-API-Key": TINYFISH_API_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url: targetUrl,
        goal,
        browser_profile: "stealth", // helps on bot-protected sites; drop if not needed
      }),
      signal: controller.signal,
    });

    if (!res.ok || !res.body) {
      throw new Error(`Agent API failed: ${res.status} ${await res.text()}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalResult = null;
    let failureReason = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep incomplete last line in buffer

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        let event;
        try {
          event = JSON.parse(line.slice(6));
        } catch {
          continue; // skip malformed/heartbeat lines
        }

        if (event.type === "COMPLETE") {
          if (event.status === "COMPLETED") {
            // handle both "result" (docs) and "resultJson" (seen in some SDKs/skills)
            const payload = event.result ?? event.resultJson;
            if (payload && payload.status === "failure") {
              failureReason = payload.reason || "goal failed";
            } else {
              finalResult = payload;
            }
          } else {
            failureReason = event.error?.message || `run failed with status ${event.status}`;
          }
        }
      }
    }

    if (finalResult) return { url: targetUrl, ...finalResult };
    return { url: targetUrl, error: failureReason || "no result returned" };
  } catch (err) {
    return { url: targetUrl, error: err.message };
  } finally {
    clearTimeout(timer);
  }
}

/** simple concurrency-limited map */
async function mapWithConcurrency(items, limit, fn) {
  const results = new Array(items.length);
  let i = 0;

  async function worker() {
    while (i < items.length) {
      const idx = i++;
      results[idx] = await fn(items[idx], idx);
    }
  }

  await Promise.all(Array.from({ length: limit }, worker));
  return results;
}

async function main() {
  const query = process.argv.slice(2).join(" ") || "example search query";

  console.error(`Searching for: "${query}" ...`);
  const searchResults = await getTopSearchResults(query, RESULT_COUNT);

  console.error(`Got ${searchResults.length} results. Extracting details from each URL ...`);
  const details = await mapWithConcurrency(searchResults, CONCURRENCY, async (r) => {
    console.error(`  -> scanning ${r.url}`);
    const extracted = await extractDetailsFromUrl(r.url);
    return {
      title: r.title,
      url: r.url,
      snippet: r.snippet,
      ...extracted,
    };
  });

  const output = {
    query,
    count: details.length,
    results: details,
  };

  console.log(JSON.stringify(output, null, 2));
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});