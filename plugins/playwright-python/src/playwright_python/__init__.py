"""Playwright helper package for browser automation and scraping."""

from .automate import click_and_download, fill_and_submit, login, login_and_save_state
from .browser import open_page, with_page
from .scrape import (
    FieldSpec,
    ScrapeJob,
    crawl_pages,
    extract_links,
    extract_record,
    extract_records,
    extract_text,
    load_recipe,
    page_snapshot,
    parse_field_mapping,
    scrape_current_page,
)

__all__ = [
    "FieldSpec",
    "ScrapeJob",
    "click_and_download",
    "crawl_pages",
    "extract_links",
    "extract_record",
    "extract_records",
    "extract_text",
    "fill_and_submit",
    "load_recipe",
    "login",
    "login_and_save_state",
    "open_page",
    "page_snapshot",
    "parse_field_mapping",
    "scrape_current_page",
    "with_page",
]
