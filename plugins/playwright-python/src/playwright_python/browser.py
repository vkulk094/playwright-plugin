from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


def _context_options(
    *,
    viewport: Optional[dict[str, int]] = None,
    storage_state_path: str | Path | None = None,
) -> dict[str, object]:
    options: dict[str, object] = {}
    if viewport is not None:
        options["viewport"] = viewport
    if storage_state_path is not None:
        options["storage_state"] = str(Path(storage_state_path))
    return options


@contextmanager
def with_page(
    *,
    headless: bool = True,
    viewport: Optional[dict[str, int]] = None,
    slow_mo: int = 0,
    storage_state_path: str | Path | None = None,
    save_storage_state_path: str | Path | None = None,
) -> Iterator[Page]:
    """Create a Chromium browser page and close it automatically."""

    with sync_playwright() as playwright:
        browser: Browser = playwright.chromium.launch(headless=headless, slow_mo=slow_mo)
        context: BrowserContext = browser.new_context(
            **_context_options(viewport=viewport, storage_state_path=storage_state_path)
        )
        page = context.new_page()
        try:
            yield page
        finally:
            if save_storage_state_path is not None:
                target = Path(save_storage_state_path)
                target.parent.mkdir(parents=True, exist_ok=True)
                context.storage_state(path=str(target))
            context.close()
            browser.close()


@contextmanager
def open_page(
    url: str,
    *,
    headless: bool = True,
    wait_until: str = "networkidle",
    viewport: Optional[dict[str, int]] = None,
    wait_for_selector: str | None = None,
    timeout_ms: int = 30_000,
    storage_state_path: str | Path | None = None,
    save_storage_state_path: str | Path | None = None,
) -> Iterator[Page]:
    """Open a URL in a fresh page and yield the page object."""

    with with_page(
        headless=headless,
        viewport=viewport,
        storage_state_path=storage_state_path,
        save_storage_state_path=save_storage_state_path,
    ) as page:
        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        if wait_for_selector:
            page.wait_for_selector(wait_for_selector, timeout=timeout_ms)
        yield page
