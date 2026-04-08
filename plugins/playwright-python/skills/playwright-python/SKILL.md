---
name: playwright-python
description: Use when you need to interact with websites in Python using Playwright for browsing, scraping, form filling, screenshots, or simple automations.
---

# Playwright Python

Use this skill when the user wants browser automation, scraping, or website interaction in Python.

## Recommended approach

- Prefer the CLI for one-off scraping and recipe-driven crawling before writing custom scripts.
- Keep browser setup in one helper and site-specific logic in separate scripts or JSON recipes.
- Reuse selectors, URLs, session-state files, and page flows from the user's request instead of inventing generic behavior.

## Included helpers

- `src/playwright_python/cli.py` for `scrape`, `crawl`, and `login-state`
- `src/playwright_python/browser.py` for launching Chromium and loading or saving storage state
- `src/playwright_python/scrape.py` for field extraction, list scraping, recipes, and pagination
- `src/playwright_python/automate.py` for fill, login, and download flows

## Typical workflow

1. Install dependencies with `pip install -r requirements.txt`.
2. Install the browser with `playwright install chromium`.
3. Start with `py -m playwright_python scrape ...` for a one-off extraction.
4. Move repeated work into a JSON recipe and run it with `crawl --recipe ...`.
5. Use `login-state` when the target site requires authentication.
6. Drop to the Python helpers only when the CLI or recipes are not enough.

## Good defaults

- Use `headless=True` unless the user explicitly needs to watch the browser.
- Prefer explicit selectors over brittle text matching when the page structure is known.
- Save authenticated session state to a local JSON file and reuse it across runs.
- Use JSON output by default and CSV only for flat list rows.

## Example

```bash
py -m playwright_python scrape https://example.com ^
  --field heading=h1 ^
  --field body=body
```
