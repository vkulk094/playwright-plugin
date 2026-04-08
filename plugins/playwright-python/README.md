# Playwright Python

<div align="center">

<h3>Browse, scrape, and automate the web with Python Playwright.</h3>

A focused Codex plugin for real browser work: extract structured data, crawl paginated pages, save login state, and reuse it across runs.

[Quick start](#quick-start) - [Scraping](#scraping) - [Recipes](#recipes) - [Login state](#login-state) - [Smoke tests](#smoke-tests)

</div>

---

## What this plugin is for

`playwright-python` gives you a practical starter kit for browser tasks that come up all the time:

- scrape a page into JSON or CSV
- crawl list pages with pagination
- save authenticated session state
- fill forms, click buttons, and capture screenshots
- build small browser automations without a lot of boilerplate

It is intentionally opinionated, but not narrow. The CLI covers the common cases, the recipe format keeps repeat work tidy, and the Python helpers give you room to customize when a site needs special handling.

## Included pieces

- `src/playwright_python/cli.py` for `scrape`, `crawl`, and `login-state`
- `src/playwright_python/browser.py` for browser setup and storage-state handling
- `src/playwright_python/scrape.py` for field extraction, list scraping, and pagination
- `src/playwright_python/automate.py` for login, form fill, download, and session-state flows
- `examples/catalog_recipe.json` for a reusable recipe example
- `scripts/smoke_test.py` for a browser helper demo
- `scripts/cli_smoke_test.py` for an end-to-end CLI smoke test
- `skills/playwright-python/SKILL.md` for Codex-facing usage guidance

## Quick start

```bash
cd plugins/playwright-python
pip install -e .
playwright install chromium
py -m playwright_python --help
```

If you installed the package, you can also use the console script:

```bash
playwright-python --help
```

## Scraping

Use `scrape` for one-page extractions and quick checks.

```bash
py -m playwright_python scrape https://example.com ^
  --field heading=h1 ^
  --field body=body
```

To export a flat list of records, add a list selector and switch to CSV:

```bash
py -m playwright_python scrape https://example.com/products ^
  --list-selector ".card" ^
  --field title=".title" ^
  --field price=".price" ^
  --attr-field href="a@href" ^
  --format csv ^
  --output products.csv
```

## Recipes

Recipes keep repeatable scraping jobs easy to reuse. They are plain JSON and work well for stable pages, catalog views, and small crawls.

Example recipe:

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

Run it with:

```bash
py -m playwright_python crawl --recipe examples/catalog_recipe.json
```

## Login state

When a site requires authentication, use `login-state` to create a reusable Playwright storage file.

```bash
py -m playwright_python login-state https://example.com/login state.json ^
  --username-selector "#email" ^
  --password-selector "#password" ^
  --submit-selector "button[type=submit]" ^
  --username-env SITE_USERNAME ^
  --password-env SITE_PASSWORD ^
  --post-login-wait-for ".dashboard"
```

Then reuse that saved state on later runs:

```bash
py -m playwright_python scrape https://example.com/account ^
  --storage-state state.json ^
  --field name=".account-name"
```

## Output

- JSON is the default and includes page metadata plus the extracted data.
- CSV is available for flat row data.
- Output is printed to stdout unless you pass `--output`.

## Smoke tests

```bash
py scripts/smoke_test.py
py scripts/cli_smoke_test.py
```

## Notes

- The plugin uses Playwright's synchronous API to keep scripts direct and readable.
- Recipes are JSON-only in v1 to stay lightweight.
- Storage state uses Playwright's native storage-state format, so it can be reused across runs without extra glue.
