# 09 — Data ingestion workers

Workers collect culture data from open sources, keep the raw payloads, normalize everything into one record format, aggregate it, and load it into PostgreSQL. Code: [src/backend/worker](../src/backend/worker).

## 1. Sources

| Source | Access | Authentication | What is collected | License / usage |
|---|---|---|---|---|
| `wikidata` | SPARQL API | none | Capital, official languages, currencies, neighbors, population, ISO codes | CC0 |
| `rest_countries` | REST API v5 | `Authorization: Bearer $REST_COUNTRIES_TOKEN` | Country facts (preferred over Wikidata when a token is set) | MPL-2.0; skipped without a token |
| `unesco_whc` | UNESCO DataHub API (`whc001`) | none | World Heritage sites: category, criteria, year, coordinates, summary | CC BY-SA 4.0 |
| `unesco_ich` | UNESCO DataHub API (`ich001`) | none | Intangible heritage elements: list, year, concepts, description | CC BY-SA 4.0 |
| `smithsonian` | Open Access API, paginated (`start`/`rows`) | `api_key=$SMITHSONIAN_API_KEY` (api.data.gov) | Museum objects with **CC0** media only; images downloaded | CC0 |
| `europeana` | Search API, cursor pagination | `wskey=$EUROPEANA_WSKEY` | Images with open rights only (`reusability=open`) | Per record (`rights`) |
| `wikimedia_commons` | MediaWiki API | none | Culture photos ≥ 1000 px with author + license | CC0 / CC BY / CC BY-SA / PD |
| `wikipedia` | MediaWiki parse API + **BeautifulSoup** | none | "Etiquette in X" / "Culture of X" articles split by section, with a category guess | CC BY-SA 4.0 |
| `scale` | GitHub raw files (`.xlsx`) | none | Cuisine, festivals, clothing, landmarks per country | No license published → reference only |
| `official_sites` | Sitemap → **Selenium** (headless Chrome) → **BeautifulSoup** | none | Pages from official tourism sites rendered with JavaScript | All rights reserved → ≤ 300-character excerpts + link only |

## 2. Collection rules

| Rule | How the worker applies it |
|---|---|
| Respect `robots.txt` | Every HTML page and every Selenium page is checked first; `Crawl-delay` is honored; if `robots.txt` returns 401/403 or cannot be read, the site is treated as disallowed |
| Use official APIs where they exist | UNESCO, Smithsonian, Europeana, Wikidata, Wikipedia, and Commons are read through their documented APIs, under each API's terms |
| Authenticate only with your own credentials | API keys and tokens come from environment variables and are never written to raw files or logs |
| Do not bypass protections | No CAPTCHA solving, login bypass, paywall circumvention, or anti-bot evasion. Pages that show a challenge are skipped and logged |
| Identify honestly | Every request uses the `CultureAtlasBot` User-Agent with a project URL |
| Rate limit | Minimum interval per domain (default 1 s, 3 s for Commons), retries with exponential backoff on 429/5xx |
| Licensing | Each record carries `provenance` (source, URL, license, date). Copyrighted pages keep excerpts only; only CC0/open media are stored locally |

**Sources deliberately not scraped:** `whc.unesco.org` and `ich.unesco.org`. Their `robots.txt` blocks bots and AI use without authorization, so the same data is taken from the UNESCO DataHub datasets, which are published under CC BY-SA 4.0.

## 3. Pipeline

```mermaid
flowchart LR
    S[Source.collect] -->|raw JSON / HTML / XLSX| R[(data/raw/source/run_id)]
    S -->|normalized records| N[(data/normalized/source.jsonl)]
    S -->|status, counts, skipped, errors| L[(data/runs/*.json)]
    N --> A[aggregate]
    A --> G[(data/aggregated/*.json)]
    A --> P[data/report.md]
    G --> D[load → PostgreSQL]
```

| Record | Table |
|---|---|
| `CountryRecord` (REST Countries > Wikidata when merged) | `countries` |
| `HeritageRecord` | `heritage_items`, `heritage_item_countries` |
| `MediaRecord` | `media_assets` (local file stored only when the license allows it) |
| `DocumentRecord` | `source_documents` (input for editors, never published directly) |
| Run log | `ingestion_runs` |

## 4. Usage

```bash
cd src/backend
python -m venv .venv && .venv/bin/pip install -e ".[dev]"

.venv/bin/python -m worker.cli sources                                  # list sources
.venv/bin/python -m worker.cli run unesco_whc wikipedia --countries JP,VN --limit 5
.venv/bin/python -m worker.cli run-all                                  # all sources, 10 MVP countries
.venv/bin/python -m worker.cli aggregate                                # data/aggregated + data/report.md
.venv/bin/python -m worker.cli load --dsn postgresql://atlas:atlas@localhost:5432/culture_atlas
.venv/bin/python -m worker.scheduler                                    # scheduled sync
```

Environment variables: `SMITHSONIAN_API_KEY`, `EUROPEANA_WSKEY`, `REST_COUNTRIES_TOKEN`, `WORKER_DATABASE_URL`, `WORKER_MIN_INTERVAL_S`, `WORKER_HEADLESS`, `WORKER_DATA_DIR`. See [.env.example](../.env.example).

## 5. Adding a source

1. Create `worker/sources/<name>.py` with a `Source` subclass: set `name`, `access`, `auth`, `license`, and implement `collect()` to yield records.
2. Save raw payloads with `self.raw.save(...)` before parsing.
3. Put parsing in a pure function and add a fixture test in `tests/test_worker_parsers.py`.
4. Register the class in `worker/sources/__init__.py` and add a schedule in `worker/scheduler.py`.
