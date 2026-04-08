from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping

from playwright.sync_api import Page

from .browser import with_page


def fill_and_submit(page: Page, fields: Mapping[str, str], submit_selector: str | None = None) -> None:
    """Fill a set of selectors and submit the form if a selector is supplied."""

    for selector, value in fields.items():
        page.locator(selector).fill(value)

    if submit_selector:
        page.locator(submit_selector).click()


def login(
    page: Page,
    *,
    username_selector: str,
    password_selector: str,
    submit_selector: str,
    username: str,
    password: str,
) -> None:
    """Perform a basic username/password login flow."""

    fill_and_submit(
        page,
        {
            username_selector: username,
            password_selector: password,
        },
        submit_selector,
    )


def click_and_download(page: Page, selector: str, destination: str | Path) -> Path:
    """Click an element and save the resulting download to disk."""

    destination_path = Path(destination)
    with page.expect_download() as download_info:
        page.locator(selector).click()
    download = download_info.value
    download.save_as(destination_path)
    return destination_path


def _resolve_secret(value: str | None, env_name: str | None, label: str) -> str:
    if value:
        return value
    if env_name:
        resolved = os.getenv(env_name)
        if resolved:
            return resolved
        raise ValueError(f"{label} environment variable '{env_name}' is not set.")
    raise ValueError(f"{label} is required.")


def login_and_save_state(
    *,
    url: str,
    state_output_path: str | Path,
    username_selector: str,
    password_selector: str,
    submit_selector: str,
    username: str | None = None,
    password: str | None = None,
    username_env: str | None = None,
    password_env: str | None = None,
    headless: bool = True,
    wait_until: str = "load",
    wait_for_selector: str | None = None,
    post_login_wait_for: str | None = None,
    post_login_wait_url_contains: str | None = None,
    timeout_ms: int = 30_000,
    settle_ms: int = 0,
) -> dict[str, str]:
    """Log into a site and persist Playwright storage state."""

    resolved_username = _resolve_secret(username, username_env, "Username")
    resolved_password = _resolve_secret(password, password_env, "Password")
    output_path = Path(state_output_path)

    with with_page(headless=headless, save_storage_state_path=output_path) as page:
        page.goto(url, wait_until=wait_until, timeout=timeout_ms)
        if wait_for_selector:
            page.wait_for_selector(wait_for_selector, timeout=timeout_ms)
        login(
            page,
            username_selector=username_selector,
            password_selector=password_selector,
            submit_selector=submit_selector,
            username=resolved_username,
            password=resolved_password,
        )
        if post_login_wait_for:
            page.wait_for_selector(post_login_wait_for, timeout=timeout_ms)
        if post_login_wait_url_contains:
            page.wait_for_function(
                "expected => window.location.href.includes(expected)",
                post_login_wait_url_contains,
                timeout=timeout_ms,
            )
        if settle_ms > 0:
            page.wait_for_timeout(settle_ms)

        return {
            "state_path": str(output_path.resolve()),
            "url": page.url,
        }
