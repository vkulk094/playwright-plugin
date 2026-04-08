from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Locator, Page


@dataclass(frozen=True)
class FieldSpec:
    name: str
    selector: str
    attr: str | None = None


@dataclass(frozen=True)
class ScrapeJob:
    url: str
    fields: list[FieldSpec]
    list_selector: str | None = None
    next_selector: str | None = None
    max_pages: int = 1
    wait_for: str | None = None
    wait_until: str = "load"
    timeout_ms: int = 30_000


SelectorRoot = Page | Locator


def extract_text(page: Page, selector: str) -> str:
    """Return trimmed text content for the first matching element."""

    element = page.locator(selector).first
    if element.count() == 0:
        return ""
    return (element.text_content() or "").strip()


def extract_links(page: Page, selector: str = "a") -> list[dict[str, str]]:
    """Collect link text and href values from a page."""

    items: list[dict[str, str]] = []
    for link in page.locator(selector).all():
        items.append(
            {
                "text": (link.text_content() or "").strip(),
                "href": link.get_attribute("href") or "",
            }
        )
    return items


def page_snapshot(page: Page) -> dict[str, Any]:
    """Return a small structured snapshot of the current page."""

    return {
        "title": page.title(),
        "url": page.url,
        "heading": extract_text(page, "h1"),
        "body_text": extract_text(page, "body"),
    }


def load_recipe(recipe_path: str | Path) -> dict[str, Any]:
    """Load a JSON scrape recipe from disk."""

    return json.loads(Path(recipe_path).read_text(encoding="utf-8"))


def parse_field_mapping(
    fields: dict[str, Any] | None = None,
    attr_fields: dict[str, Any] | None = None,
) -> list[FieldSpec]:
    """Build a list of field specs from recipe field mappings."""

    parsed: dict[str, FieldSpec] = {}

    for name, value in (fields or {}).items():
        if isinstance(value, str):
            parsed[name] = FieldSpec(name=name, selector=value)
            continue
        if isinstance(value, dict):
            selector = value.get("selector")
            if not selector:
                raise ValueError(f"Field '{name}' is missing a selector.")
            parsed[name] = FieldSpec(name=name, selector=selector, attr=value.get("attr"))
            continue
        raise ValueError(f"Field '{name}' must be a selector string or object.")

    for name, value in (attr_fields or {}).items():
        if isinstance(value, str):
            selector, attr = value.rsplit("@", 1)
            parsed[name] = FieldSpec(name=name, selector=selector, attr=attr)
            continue
        if isinstance(value, dict):
            selector = value.get("selector")
            attr = value.get("attr")
            if not selector or not attr:
                raise ValueError(f"Attribute field '{name}' needs both selector and attr.")
            parsed[name] = FieldSpec(name=name, selector=selector, attr=attr)
            continue
        raise ValueError(f"Attribute field '{name}' must be a selector string or object.")

    return list(parsed.values())


def wait_for_page(page: Page, *, wait_for: str | None = None, timeout_ms: int = 30_000) -> None:
    """Wait for a page selector when one is supplied."""

    if wait_for:
        page.wait_for_selector(wait_for, timeout=timeout_ms)


def extract_field(root: SelectorRoot, field: FieldSpec) -> str:
    """Extract a single field from a page or locator."""

    node = root.locator(field.selector).first
    if node.count() == 0:
        return ""
    if field.attr:
        return (node.get_attribute(field.attr) or "").strip()
    return (node.text_content() or "").strip()


def extract_record(root: SelectorRoot, fields: list[FieldSpec]) -> dict[str, str]:
    """Extract a flat record from the current root."""

    return {field.name: extract_field(root, field) for field in fields}


def extract_records(page: Page, list_selector: str, fields: list[FieldSpec]) -> list[dict[str, str]]:
    """Extract repeated records from a list container selector."""

    return [extract_record(item, fields) for item in page.locator(list_selector).all()]


def scrape_current_page(page: Page, job: ScrapeJob) -> dict[str, Any]:
    """Scrape the current page according to the supplied job."""

    metadata = page_snapshot(page)
    result: dict[str, Any] = {
        "url": page.url,
        "metadata": metadata,
    }

    if job.list_selector:
        items = extract_records(page, job.list_selector, job.fields)
        result["items"] = items
        result["count"] = len(items)
    else:
        data = extract_record(page, job.fields)
        result["data"] = data
        result["count"] = 1 if data else 0

    return result


def _go_to_next_page(page: Page, job: ScrapeJob) -> bool:
    next_selector = job.next_selector
    if not next_selector:
        return False

    next_link = page.locator(next_selector).first
    if next_link.count() == 0:
        return False

    current_url = page.url
    href = next_link.get_attribute("href")

    if href:
        destination = urljoin(current_url, href)
        if destination == current_url:
            return False
        page.goto(destination, wait_until=job.wait_until, timeout=job.timeout_ms)
    else:
        next_link.click()
        page.wait_for_load_state("load", timeout=job.timeout_ms)

    wait_for_page(page, wait_for=job.wait_for, timeout_ms=job.timeout_ms)
    return page.url != current_url


def crawl_pages(page: Page, job: ScrapeJob) -> dict[str, Any]:
    """Scrape one or more pages and aggregate the results."""

    wait_for_page(page, wait_for=job.wait_for, timeout_ms=job.timeout_ms)
    pages: list[dict[str, Any]] = []
    aggregated_items: list[dict[str, str]] = []

    for _ in range(max(job.max_pages, 1)):
        page_result = scrape_current_page(page, job)
        pages.append(page_result)
        if "items" in page_result:
            aggregated_items.extend(page_result["items"])
        if not job.next_selector or not _go_to_next_page(page, job):
            break

    result: dict[str, Any] = {
        "start_url": job.url,
        "page_count": len(pages),
        "pages": pages,
    }
    if aggregated_items:
        result["items"] = aggregated_items
        result["item_count"] = len(aggregated_items)
    return result
