from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from playwright_python.cli import main as cli_main


INDEX_HTML = """
<html>
  <body>
    <h1>Catalog</h1>
    <div class="card">
      <a href="/items/alpha" class="title">Alpha</a>
      <span class="price">$10</span>
    </div>
    <div class="card">
      <a href="/items/beta" class="title">Beta</a>
      <span class="price">$20</span>
    </div>
    <a class="next" href="/page2.html">Next</a>
  </body>
</html>
"""

PAGE_TWO_HTML = """
<html>
  <body>
    <h1>Catalog Page 2</h1>
    <div class="card">
      <a href="/items/gamma" class="title">Gamma</a>
      <span class="price">$30</span>
    </div>
  </body>
</html>
"""

LOGIN_HTML = """
<html>
  <body>
    <form id="login-form">
      <input id="username" />
      <input id="password" type="password" />
      <button id="submit" type="button">Sign in</button>
    </form>
    <div id="status"></div>
    <script>
      document.getElementById("submit").addEventListener("click", () => {
        document.cookie = "session=ok; Path=/";
        document.getElementById("status").textContent = "Logged in";
      });
    </script>
  </body>
</html>
"""

PRIVATE_HTML = """
<html>
  <body>
    <h1>Private</h1>
    <div class="secret">swordfish</div>
  </body>
</html>
"""


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/index.html":
            self._send_html(INDEX_HTML)
            return
        if self.path == "/page2.html":
            self._send_html(PAGE_TWO_HTML)
            return
        if self.path == "/login.html":
            self._send_html(LOGIN_HTML)
            return
        if self.path == "/private.html":
            if "session=ok" in self.headers.get("Cookie", ""):
                self._send_html(PRIVATE_HTML)
            else:
                self._send_html("<html><body><div class='error'>missing session</div></body></html>", status=403)
            return
        self._send_html("<html><body>not found</body></html>", status=404)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return

    def _send_html(self, content: str, *, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_cli(args: list[str]) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        cli_main(args)
    return buffer.getvalue().strip()


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def write_recipe(path: Path, base_url: str) -> None:
    recipe = {
        "url": f"{base_url}/index.html",
        "wait_for": ".card",
        "list_selector": ".card",
        "next_selector": "a.next",
        "max_pages": 2,
        "fields": {
            "title": ".title",
            "price": ".price"
        },
        "attr_fields": {
            "href": ".title@href"
        },
        "format": "json"
    }
    path.write_text(json.dumps(recipe, indent=2), encoding="utf-8")


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)

            single_page = json.loads(
                run_cli(
                    [
                        "scrape",
                        f"{base_url}/index.html",
                        "--field",
                        "heading=h1",
                        "--field",
                        "body=body"
                    ]
                )
            )
            assert_true(single_page["data"]["heading"] == "Catalog", "single-page scrape should capture the heading")

            csv_output = workspace / "items.csv"
            run_cli(
                [
                    "scrape",
                    f"{base_url}/index.html",
                    "--list-selector",
                    ".card",
                    "--field",
                    "title=.title",
                    "--field",
                    "price=.price",
                    "--attr-field",
                    "href=.title@href",
                    "--format",
                    "csv",
                    "--output",
                    str(csv_output)
                ]
            )
            csv_text = csv_output.read_text(encoding="utf-8")
            assert_true("title,price,href" in csv_text.splitlines()[0], "CSV output should include the requested columns")
            assert_true("Alpha,$10,/items/alpha" in csv_text, "CSV output should include scraped rows")

            recipe_path = workspace / "catalog_recipe.json"
            write_recipe(recipe_path, base_url)
            crawl_result = json.loads(run_cli(["crawl", "--recipe", str(recipe_path)]))
            assert_true(crawl_result["page_count"] == 2, "recipe crawl should paginate to the second page")
            assert_true(crawl_result["item_count"] == 3, "recipe crawl should aggregate items across pages")

            state_path = workspace / "state.json"
            run_cli(
                [
                    "login-state",
                    f"{base_url}/login.html",
                    str(state_path),
                    "--username-selector",
                    "#username",
                    "--password-selector",
                    "#password",
                    "--submit-selector",
                    "#submit",
                    "--username",
                    "demo",
                    "--password",
                    "secret",
                    "--wait-for",
                    "#login-form",
                    "--post-login-wait-for",
                    "#status"
                ]
            )
            assert_true(state_path.exists(), "login-state should create a storage-state file")

            private_result = json.loads(
                run_cli(
                    [
                        "scrape",
                        f"{base_url}/private.html",
                        "--storage-state",
                        str(state_path),
                        "--field",
                        "secret=.secret"
                    ]
                )
            )
            assert_true(private_result["data"]["secret"] == "swordfish", "storage state should unlock the protected page")

        print("CLI smoke test passed")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
