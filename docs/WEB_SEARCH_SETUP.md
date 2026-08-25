# Web Search / Research Setup

This is the single runtime configuration guide for both Study Agent search paths:

- ordinary chat research (`WebLookupRun`), which must return visible sources or a truthful failure;
- the durable `NewsRun` workflow used by the Lab/group-news compatibility surface.

Current pass/fail evidence and latency measurements belong in
[`PROJECT_STATUS.md`](PROJECT_STATUS.md). The NewsRun implementation contract belongs in
[`NEWS_PIPELINE.md`](NEWS_PIPELINE.md).

The checked-in example keeps optional network providers disabled. The locally validated
production setup enables a loopback SearXNG instance for ordinary research; DuckDuckGo HTML
is only the final fallback because challenge pages are common.

```env
NEWS_ENABLE_SEARXNG=false
NEWS_ENABLE_JINA_READER=false
NEWS_ENABLE_FIRECRAWL_READER=false
```

## 1. Search Paths

### Ordinary research

```text
User query
→ local SearXNG (preferred)
→ Bing Web RSS (fallback)
→ DuckDuckGo HTML (last fallback)
→ validate title + public URL
→ optional relevant page read
→ ResearchRun truth + visible sources
```

Provider challenge, timeout, connection and HTTP failures are structured errors. Empty or
failed calls do not become `found` and do not enter model evidence.

Recommended local configuration:

```env
WEB_ENABLE_SEARXNG=true
SEARXNG_BASE_URL=http://127.0.0.1:8080
SEARXNG_ALLOW_LOOPBACK=true
WEB_SEARXNG_CATEGORIES=general
WEB_SEARCH_PROVIDER_TIMEOUT_SECONDS=6
WEB_SEARCH_TOTAL_TIMEOUT_SECONDS=8
WEB_ENABLE_BING_RSS=true
WEB_ENABLE_DUCKDUCKGO=true
WEB_TOOL_TOTAL_BUDGET_SECONDS=12
```

The search budget is shared across sequential provider fallbacks. These 12/20-second limits now
describe the quick-query path only. Explicit “研究/调查/验证/比较” intent is being repaired under
RQ1 as a separate 45/60-second bounded-research tier; current evidence and its NO-GO status remain
owned by `PROJECT_STATUS.md`.

### NewsRun

```text
User query
→ optional SearXNG search source
→ Google News RSS / Bing News RSS / RSSHub fallback
→ redirect resolution
→ canonical URL dedup
→ domain policy scoring/filtering
→ local reader extraction
→ optional Firecrawl fallback
→ optional Jina fallback
→ digest
→ group discussion
→ source trace
```

## 2. NewsRun Configurations

### A. Most stable default

Use this first if you only want the existing behavior:

```env
NEWS_ENABLE_SEARXNG=false
NEWS_ENABLE_JINA_READER=false
NEWS_ENABLE_FIRECRAWL_READER=false
```

This uses RSS feeds and local article extraction only.

### B. Better search candidates with local SearXNG

Use this when you have a working local SearXNG instance:

```env
NEWS_ENABLE_SEARXNG=true
SEARXNG_BASE_URL=http://127.0.0.1:8080
SEARXNG_ALLOW_LOOPBACK=true
NEWS_SEARXNG_CATEGORIES=news
NEWS_SOURCE_TIMEOUT_SECONDS=8
NEWS_SOURCE_MAX_ATTEMPTS=2
NEWS_SEARCH_DEADLINE_SECONDS=20
NEWS_RESOLVE_DEADLINE_SECONDS=10
NEWS_ARTICLE_DEADLINE_SECONDS=20
NEWS_ENABLE_JINA_READER=false
NEWS_ENABLE_FIRECRAWL_READER=false
```

SearXNG is used as an extra candidate source. If it returns 403, HTML, non-JSON, or times out, the pipeline falls back to RSS.

`NEWS_SEARXNG_CATEGORIES` is forwarded to SearXNG and defaults to `news`.
Search providers, redirect resolution, and selected article reads run concurrently.
`NEWS_SOURCE_TIMEOUT_SECONDS` is clamped to 1-30 seconds and
`NEWS_SOURCE_MAX_ATTEMPTS` is clamped to 1-3 attempts.

### C. Local/self-hosted extraction fallback with Firecrawl-compatible API

Use this when local trafilatura/readability extraction often fails and you have a self-hosted Firecrawl-compatible server:

```env
NEWS_ENABLE_SEARXNG=true
SEARXNG_BASE_URL=http://127.0.0.1:8080
NEWS_ENABLE_FIRECRAWL_READER=true
FIRECRAWL_BASE_URL=http://127.0.0.1:3002
FIRECRAWL_ALLOW_LOOPBACK=true
# FIRECRAWL_API_KEY=your_optional_key
NEWS_ENABLE_JINA_READER=false
```

Firecrawl fallback is attempted only after local extraction fails.

### D. Hosted Jina fallback

Use this only if you accept sending public article URLs to hosted Jina Reader:

```env
NEWS_ENABLE_JINA_READER=true
```

Jina fallback is attempted only after local extraction fails and, if enabled, after Firecrawl fallback fails.

## 3. Repository-managed SearXNG (SX1)

The loopback instance is defined by:

- `infra/searxng/compose.yml`: a single SearXNG service pinned to an image digest;
- `infra/searxng/settings.yml`: JSON enabled, limiter/public-instance/image-proxy disabled;
- ignored `infra/searxng/.env.local`: the machine secret and optional proxy values.

Normal startup never pulls or updates an image. It can recreate the service only from the pinned
image already present locally. Run the explicit upgrade entrypoint for first migration or after a
reviewed digest change:

```powershell
.\tools\upgrade-searxng.bat
```

The upgrade performs these operations in order:

1. create the ignored local env once; an existing secret is never rotated automatically;
2. make a timestamped same-directory backup of the active `settings.yml`;
3. pull only the digest already pinned in the tracked Compose file;
4. start an isolated candidate on `127.0.0.1:18080`;
5. require `/healthz`, exact image/config identity, and at least one valid real search;
6. stop and rename the old active container, then start the candidate configuration on `8080`;
7. automatically restore the old container if the new active fails deterministic identity/health checks;
8. remove the temporary candidate while retaining the stopped old container for at least seven days.

Inspect the active and retained containers without exposing the local secret:

```powershell
.\tools\manage-searxng.bat -Action Status -ProbeSearch
.\tools\manage-searxng.bat -Action ListRetained
```

Retained containers are never deleted automatically. After seven days, deletion requires the
exact timestamped name and `-ConfirmRemoval`; the command refuses early deletion. Upstream CAPTCHA,
rate limiting, or engine timeouts can make the live search probe `degraded` without changing the
fixed-image/config identity or triggering an update loop.

This SX1 surface remains loopback-only. It does not implement the separately frozen G17 LAN mode.

## 4. SearXNG Runtime Check

Start SearXNG, then open:

```text
http://127.0.0.1:8080/search?q=python&format=json
```

Expected result: JSON containing a non-empty `results` array for an ordinary query.

If you get 403 or HTML, JSON output is disabled on that instance. Ordinary research may fall
back to Bing RSS and DuckDuckGo; NewsRun may fall back to configured RSS. A fallback is not a
successful SearXNG health check.

Use three representative ordinary queries for release validation. Each query must return at
least three results with non-empty title and public URL in under 10 seconds. Also test challenge,
timeout and repeated-timeout fixtures; unit tests alone do not prove the local provider is up.

The API exposes a read-only diagnostic that does not delay the core `/health` readiness check:

```text
GET http://127.0.0.1:8000/health/providers
GET http://127.0.0.1:8000/health/providers?probe=false
```

The live form first checks SearXNG `/healthz`, then performs one search with a five-second cap.
The response distinguishes `enabled`, `configured`, service `reachable` and
`search_capable`; a reachable service with slow/unresponsive engines is reported as degraded.
Fallback switches are reported as unprobed and never promoted to reachable without an actual
search.

## 5. Quick Firecrawl-compatible Check

The adapter assumes a Firecrawl-compatible scrape endpoint:

```text
POST {FIRECRAWL_BASE_URL}/v1/scrape
```

With a body similar to:

```json
{
  "url": "https://example.com/article",
  "formats": ["markdown"],
  "onlyMainContent": true
}
```

The adapter reads `data.markdown`, `markdown`, `data.content`, or `content` from the JSON response.

## 6. Safety Boundaries

- SearXNG is disabled unless `NEWS_ENABLE_SEARXNG=true`.
- Firecrawl is disabled unless `NEWS_ENABLE_FIRECRAWL_READER=true`.
- Jina is disabled unless `NEWS_ENABLE_JINA_READER=true`.
- Article target URLs must be public HTTP(S) URLs.
- Local SearXNG/Firecrawl service endpoints require explicit loopback flags.
- `file://`, localhost, loopback, private IP, and unsafe targets are rejected before hosted reader calls.
- Login/account/auth pages are filtered by domain policy before article reading.

## 7. Test Commands

```bash
ruff check src/ tests/
pytest tests/test_url_normalizer.py tests/test_news_redirect_dedup.py tests/test_domain_policy.py -v
pytest tests/test_reader_backends.py tests/test_searxng_source.py tests/test_firecrawl_reader.py -v
pytest tests/test_web_query_normalizer.py tests/test_persistent_web_agent.py tests/test_web_lookup_research_contract.py -v
pytest tests/ -v
```

## 8. Suggested Validation Queries

Use these to compare source quality:

```text
python urllib.parse redirect
Godot 4 export error
OpenAI API docs
LiteCDNet remote sensing change detection
```

For ordinary research, check that every claimed online result has a visible title and URL, and
that failure never reports `found`. For NewsRun, check the source block for:

- `来源：SearXNG/...` if SearXNG is enabled and working.
- `正文已读｜本地 trafilatura` or similar if local extraction works.
- `正文已读｜Firecrawl` if Firecrawl fallback was used.
- `正文已读｜Jina Reader` if Jina fallback was used.
