from __future__ import annotations

import argparse
import csv
import json
from io import StringIO
from pathlib import Path
from typing import Any, Sequence

from .automate import login_and_save_state
from .browser import open_page
from .scrape import (
    FieldSpec,
    ScrapeJob,
    crawl_pages,
    extract_links,
    load_recipe,
    page_snapshot,
    parse_field_mapping,
    scrape_current_page,
    wait_for_page,
)


def _add_browser_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--headed", action="store_true", help="Show the browser window.")
    parser.add_argument("--wait-for", help="Wait for a selector after navigation.")
    parser.add_argument(
        "--wait-until",
        choices=["load", "domcontentloaded", "networkidle", "commit"],
        help="Playwright wait mode for navigation.",
    )
    parser.add_argument("--timeout-ms", type=int, help="Navigation and selector timeout in milliseconds.")
    parser.add_argument("--storage-state", type=Path, help="Load Playwright storage state from a JSON file.")
    parser.add_argument("--save-storage-state", type=Path, help="Write Playwright storage state to a JSON file.")


def _add_output_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--format", choices=["json", "csv"], help="Output format.")
    parser.add_argument("--output", type=Path, help="Optional output file path.")


def _add_field_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        metavar="NAME=SELECTOR",
        help="Extract text content into a named field.",
    )
    parser.add_argument(
        "--attr-field",
        action="append",
        default=[],
        metavar="NAME=SELECTOR@ATTR",
        help="Extract an element attribute into a named field.",
    )


def _resolve_path(path: str | Path | None, *, base_dir: Path | None = None) -> Path | None:
    if path is None:
        return None
    candidate = Path(path)
    if candidate.is_absolute() or base_dir is None:
        return candidate
    return (base_dir / candidate).resolve()


def _parse_assignment(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise ValueError(f"Expected NAME=VALUE format, got '{value}'.")
    name, parsed = value.split("=", 1)
    if not name or not parsed:
        raise ValueError(f"Expected NAME=VALUE format, got '{value}'.")
    return name, parsed


def _parse_attr_assignment(value: str) -> tuple[str, str, str]:
    name, parsed = _parse_assignment(value)
    if "@" not in parsed:
        raise ValueError(f"Expected NAME=SELECTOR@ATTR format, got '{value}'.")
    selector, attr = parsed.rsplit("@", 1)
    if not selector or not attr:
        raise ValueError(f"Expected NAME=SELECTOR@ATTR format, got '{value}'.")
    return name, selector, attr


def _cli_fields(args: argparse.Namespace) -> list[FieldSpec]:
    fields: dict[str, FieldSpec] = {}
    for assignment in args.field:
        name, selector = _parse_assignment(assignment)
        fields[name] = FieldSpec(name=name, selector=selector)
    for assignment in args.attr_field:
        name, selector, attr = _parse_attr_assignment(assignment)
        fields[name] = FieldSpec(name=name, selector=selector, attr=attr)
    return list(fields.values())


def _load_recipe_context(recipe_path: Path | None) -> tuple[dict[str, Any], Path | None]:
    if recipe_path is None:
        return {}, None
    recipe = load_recipe(recipe_path)
    return recipe, recipe_path.parent.resolve()


def _recipe_fields(recipe: dict[str, Any]) -> list[FieldSpec]:
    return parse_field_mapping(recipe.get("fields"), recipe.get("attr_fields"))


def _value_from_args(
    args: argparse.Namespace,
    recipe: dict[str, Any],
    name: str,
    default: Any = None,
) -> Any:
    value = getattr(args, name, None)
    if value not in (None, [], ""):
        return value
    if name in recipe:
        return recipe[name]
    return default


def _build_job(args: argparse.Namespace, *, expect_pagination: bool) -> tuple[ScrapeJob, dict[str, Any], Path | None]:
    recipe_path = args.recipe.resolve() if args.recipe else None
    recipe, recipe_base_dir = _load_recipe_context(recipe_path)
    cli_fields = _cli_fields(args)
    fields = cli_fields or _recipe_fields(recipe)

    url = _value_from_args(args, recipe, "url")
    if not url:
        raise ValueError("A URL or recipe with a URL is required.")

    list_selector = _value_from_args(args, recipe, "list_selector")
    next_selector = _value_from_args(args, recipe, "next_selector")
    max_pages = _value_from_args(args, recipe, "max_pages", 10 if expect_pagination else 1)
    wait_for = _value_from_args(args, recipe, "wait_for")
    wait_until = _value_from_args(args, recipe, "wait_until", "load")
    timeout_ms = _value_from_args(args, recipe, "timeout_ms", 30_000)
    if expect_pagination and not next_selector:
        raise ValueError("The crawl command requires --next-selector or a recipe next_selector.")

    job = ScrapeJob(
        url=url,
        fields=fields,
        list_selector=list_selector,
        next_selector=next_selector if expect_pagination else next_selector,
        max_pages=max_pages if expect_pagination else 1,
        wait_for=wait_for,
        wait_until=wait_until,
        timeout_ms=timeout_ms,
    )
    return job, recipe, recipe_base_dir


def _output_config(
    args: argparse.Namespace,
    recipe: dict[str, Any],
    recipe_base_dir: Path | None,
) -> tuple[str, Path | None]:
    output_format = _value_from_args(args, recipe, "format", "json")
    output_path = _resolve_path(_value_from_args(args, recipe, "output"), base_dir=recipe_base_dir)
    return output_format, output_path


def _browser_config(
    args: argparse.Namespace,
    recipe: dict[str, Any],
    recipe_base_dir: Path | None,
) -> dict[str, Any]:
    storage_state = _resolve_path(_value_from_args(args, recipe, "storage_state"), base_dir=recipe_base_dir)
    save_storage_state = _resolve_path(
        _value_from_args(args, recipe, "save_storage_state"),
        base_dir=recipe_base_dir,
    )
    return {
        "headless": not args.headed,
        "storage_state_path": storage_state,
        "save_storage_state_path": save_storage_state,
    }


def _collect_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    if "items" in result:
        return result["items"]
    if "pages" in result:
        rows: list[dict[str, Any]] = []
        for page in result["pages"]:
            if "items" in page:
                rows.extend(page["items"])
            elif "data" in page:
                rows.append({"page_url": page["url"], **page["data"]})
        return rows
    if "data" in result:
        return [result["data"]]
    return []


def _render_csv(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return ""
    header = list(rows[0].keys())
    for row in rows:
        if any(isinstance(value, (dict, list, tuple)) for value in row.values()):
            raise ValueError("CSV export only supports flat records.")
        if list(row.keys()) != header:
            raise ValueError("CSV export requires consistent columns across records.")
    stream = StringIO()
    writer = csv.DictWriter(stream, fieldnames=header)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _write_output(payload: dict[str, Any], *, output_format: str, output_path: Path | None) -> None:
    if output_format == "json":
        rendered = json.dumps(payload, indent=2)
    else:
        rendered = _render_csv(_collect_csv_rows(payload))

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        print(output_path)
        return
    print(rendered)


def _handle_scrape_like(args: argparse.Namespace, *, expect_pagination: bool) -> None:
    job, recipe, recipe_base_dir = _build_job(args, expect_pagination=expect_pagination)
    output_format, output_path = _output_config(args, recipe, recipe_base_dir)
    browser_config = _browser_config(args, recipe, recipe_base_dir)

    with open_page(
        job.url,
        headless=browser_config["headless"],
        wait_until=job.wait_until,
        wait_for_selector=job.wait_for,
        timeout_ms=job.timeout_ms,
        storage_state_path=browser_config["storage_state_path"],
        save_storage_state_path=browser_config["save_storage_state_path"],
    ) as page:
        if expect_pagination:
            result = crawl_pages(page, job)
        else:
            wait_for_page(page, wait_for=job.wait_for, timeout_ms=job.timeout_ms)
            result = scrape_current_page(page, job)
    _write_output(result, output_format=output_format, output_path=output_path)


def _handle_login_state(args: argparse.Namespace) -> None:
    result = login_and_save_state(
        url=args.url,
        state_output_path=args.output,
        username_selector=args.username_selector,
        password_selector=args.password_selector,
        submit_selector=args.submit_selector,
        username=args.username,
        password=args.password,
        username_env=args.username_env,
        password_env=args.password_env,
        headless=not args.headed,
        wait_until=args.wait_until or "load",
        wait_for_selector=args.wait_for,
        post_login_wait_for=args.post_login_wait_for,
        post_login_wait_url_contains=args.post_login_wait_url_contains,
        timeout_ms=args.timeout_ms or 30_000,
        settle_ms=args.settle_ms,
    )
    print(json.dumps(result, indent=2))


def _handle_browse(args: argparse.Namespace) -> None:
    with open_page(args.url, headless=not args.headed) as page:
        print(json.dumps(page_snapshot(page), indent=2))


def _handle_links(args: argparse.Namespace) -> None:
    with open_page(args.url, headless=not args.headed) as page:
        for item in extract_links(page):
            print(f"{item['text']}\t{item['href']}")


def _handle_screenshot(args: argparse.Namespace) -> None:
    with open_page(args.url, headless=not args.headed) as page:
        page.screenshot(path=str(args.output), full_page=True)
    print(args.output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Playwright Python scraping and automation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scrape = subparsers.add_parser("scrape", help="Scrape a single page.")
    scrape.add_argument("url", nargs="?")
    scrape.add_argument("--recipe", type=Path, help="Path to a JSON scrape recipe.")
    scrape.add_argument("--list-selector", help="Selector for repeated item containers.")
    _add_field_options(scrape)
    _add_browser_options(scrape)
    _add_output_options(scrape)
    scrape.set_defaults(handler=lambda args: _handle_scrape_like(args, expect_pagination=False))

    crawl = subparsers.add_parser("crawl", help="Scrape multiple pages with pagination.")
    crawl.add_argument("url", nargs="?")
    crawl.add_argument("--recipe", type=Path, help="Path to a JSON scrape recipe.")
    crawl.add_argument("--list-selector", help="Selector for repeated item containers.")
    crawl.add_argument("--next-selector", help="Selector for the next page link or button.")
    crawl.add_argument("--max-pages", type=int, help="Maximum number of pages to crawl.")
    _add_field_options(crawl)
    _add_browser_options(crawl)
    _add_output_options(crawl)
    crawl.set_defaults(handler=lambda args: _handle_scrape_like(args, expect_pagination=True))

    login_state = subparsers.add_parser("login-state", help="Create a reusable Playwright storage state file.")
    login_state.add_argument("url")
    login_state.add_argument("output", type=Path)
    login_state.add_argument("--username-selector", required=True)
    login_state.add_argument("--password-selector", required=True)
    login_state.add_argument("--submit-selector", required=True)
    login_state.add_argument("--username")
    login_state.add_argument("--password")
    login_state.add_argument("--username-env")
    login_state.add_argument("--password-env")
    login_state.add_argument("--post-login-wait-for")
    login_state.add_argument("--post-login-wait-url-contains")
    login_state.add_argument("--settle-ms", type=int, default=0)
    _add_browser_options(login_state)
    login_state.set_defaults(handler=_handle_login_state)

    browse = subparsers.add_parser("browse", help="Open a URL and print a page snapshot.")
    browse.add_argument("url")
    browse.add_argument("--headed", action="store_true")
    browse.set_defaults(handler=_handle_browse)

    links = subparsers.add_parser("links", help="Open a URL and list links.")
    links.add_argument("url")
    links.add_argument("--headed", action="store_true")
    links.set_defaults(handler=_handle_links)

    screenshot = subparsers.add_parser("screenshot", help="Open a URL and save a screenshot.")
    screenshot.add_argument("url")
    screenshot.add_argument("output", type=Path)
    screenshot.add_argument("--headed", action="store_true")
    screenshot.set_defaults(handler=_handle_screenshot)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.handler(args)


if __name__ == "__main__":
    main()
