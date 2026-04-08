# Playwright Plugin

<div align="center">

<h3>Open the page. Read the data. Reuse the session. Ship the result.</h3>

A polished home for a Python Playwright Codex plugin that helps you browse websites, scrape real pages, and run practical automations without turning the project into a maze.

[Plugin docs](plugins/playwright-python/README.md) · [Recipe example](plugins/playwright-python/examples/catalog_recipe.json) · [CLI smoke test](plugins/playwright-python/scripts/cli_smoke_test.py)

</div>

---

## What this repo does

This repo packages a focused Playwright plugin named `playwright-python`. It is designed for the kind of browser work people actually need:

- Scrape pages into JSON or CSV
- Crawl paginated lists and catalog pages
- Save login state and reuse it later
- Take screenshots, fill forms, and automate repeatable browser tasks

## What makes it useful

The plugin keeps the surface area small while still feeling capable. The core idea is simple: use the CLI for common work, use recipes when the workflow repeats, and drop into Python helpers when you need more control.

- `scrape` for single pages and structured extraction
- `crawl` for multi-page runs and pagination
- `login-state` for reusable authenticated sessions
- Small helper modules for scripting and extensions

## What is inside

- `plugins/playwright-python/README.md` for plugin-specific setup and usage
- `plugins/playwright-python/src/playwright_python/` for the Python helpers and CLI
- `plugins/playwright-python/examples/` for reusable recipe examples
- `plugins/playwright-python/scripts/` for smoke tests and verification
- `plugins/playwright-python/skills/` for Codex-facing guidance

## Quick start

```bash
cd plugins/playwright-python
pip install -e .
playwright install chromium
py -m playwright_python --help
```

## Typical workflows

One-off scrape:

```bash
py -m playwright_python scrape https://example.com ^
  --field heading=h1 ^
  --field body=body
```

Reusable recipe:

```bash
py -m playwright_python crawl --recipe plugins/playwright-python/examples/catalog_recipe.json
```

Saved login state:

```bash
py -m playwright_python login-state https://example.com/login state.json ^
  --username-selector "#email" ^
  --password-selector "#password" ^
  --submit-selector "button[type=submit]"
```

## Why this layout

The repo root stays clean and welcoming, while the actual plugin lives in one focused folder. That makes it easy to understand at a glance, easy to extend, and easy to publish or reuse later.
