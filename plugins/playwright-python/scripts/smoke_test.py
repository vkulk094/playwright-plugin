from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from playwright_python.automate import fill_and_submit
from playwright_python.browser import with_page
from playwright_python.scrape import extract_links, page_snapshot


def main() -> None:
    with with_page() as page:
        page.goto("https://example.com")
        print("BROWSE")
        print(page_snapshot(page))
        print(extract_links(page))

    with with_page() as page:
        page.set_content(
            """
            <html>
              <body>
                <form id="demo-form">
                  <input id="name" name="name" />
                  <button id="save" type="button">Save</button>
                </form>
                <div id="result"></div>
                <script>
                  document.getElementById("save").addEventListener("click", () => {
                    const value = document.getElementById("name").value;
                    document.getElementById("result").textContent = value;
                  });
                </script>
              </body>
            </html>
            """
        )
        fill_and_submit(page, {"#name": "Codex"}, "#save")
        print("AUTOMATION")
        print(page.locator("#result").text_content())


if __name__ == "__main__":
    main()
