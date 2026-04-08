# Playwright Python

Opinionated Codex plugin for browser interaction, web scraping, and lightweight automations with Python Playwright.

## What is included

- `src/playwright_python/cli.py` for real-page scraping, crawling, and login-state commands
- `src/playwright_python/browser.py` for browser lifecycle and storage-state handling
- `src/playwright_python/scrape.py` for field extraction, list scraping, recipe loading, and pagination
- `src/playwright_python/automate.py` for login, form fill, screenshot, download, and storage-state flows
- `examples/catalog_recipe.json` as a reusable JSON recipe example
- `scripts/smoke_test.py` for the basic browser helper demo
- `scripts/cli_smoke_test.py` for end-to-end CLI verification against a local demo site
- `skills/playwright-python/SKILL.md` with agent-facing usage guidance

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

You can run the CLI either with the module entrypoint or the installed console script:

```bash
py -m playwright_python --help
playwright-python --help
```

## Quick scraping

Scrape a single page into JSON:

```bash
py -m playwright_python scrape https://example.com ^
  --field heading=h1 ^
  --field body=body
```

Scrape repeated cards into CSV:

```bash
py -m playwright_python scrape https://example.com/products ^
  --list-selector ".card" ^
  --field title=".title" ^
  --field price=".price" ^
  --attr-field href="a@href" ^
  --format csv ^
  --output products.csv
```

## Recipe-driven scraping

Recipes are plain JSON files. The example at `examples/catalog_recipe.json` shows the v1 shape:

```json
{
  "url": "https://example.com/products",
  "wait_for": ".card",
  "list_selector": ".card",
  "next_selector": "a.next",
  "max_pages": 3,
  "fields": {
    "title": ".title",
    "price": ".price"
  },
  "attr_fields": {
    "href": "a@href"
  },
  "format": "json"
}
```

Run a recipe with:

```bash
py -m playwright_python crawl --recipe examples/catalog_recipe.json
```

## Login state

Create reusable authenticated browser state:

```bash
py -m playwright_python login-state https://example.com/login state.json ^
  --username-selector "#email" ^
  --password-selector "#password" ^
  --submit-selector "button[type=submit]" ^
  --username-env SITE_USERNAME ^
  --password-env SITE_PASSWORD ^
  --post-login-wait-for ".dashboard"
```

Reuse the saved state on later runs:

```bash
py -m playwright_python scrape https://example.com/account ^
  --storage-state state.json ^
  --field name=".account-name"
```

## Output behavior

- JSON is the default and preserves page metadata plus structured records.
- CSV export is intended for flat row data.
- Output goes to stdout unless `--output` is supplied.

## Smoke tests

```bash
py scripts/smoke_test.py
py scripts/cli_smoke_test.py
```

## Notes

- The plugin uses the synchronous Playwright API for direct scripting and CLI workflows.
- Recipes are JSON-only in v1 to keep setup simple.
- Storage state uses Playwright's native storage-state JSON format.
