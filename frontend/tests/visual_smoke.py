import os
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "ui"
BASE_URL = os.environ.get("VISUAL_TEST_BASE_URL", "http://127.0.0.1:3000")


def inspect(browser, path: str, screenshot: str, width: int, height: int, runtime_errors: list[str]) -> list[str]:
    issues: list[str] = []
    page = browser.new_page(viewport={"width": width, "height": height})
    page.route(
        "**/api/**",
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body='{"detail":"Visual test: API intentionally offline"}',
        ),
    )
    page.on("pageerror", lambda error: runtime_errors.append(f"pageerror: {error}"))
    page.on(
        "console",
        lambda message: runtime_errors.append(f"console: {message.text}")
        if message.type == "error"
        else None,
    )
    page.goto(f"{BASE_URL}{path}", wait_until="domcontentloaded", timeout=30_000)
    try:
        page.wait_for_load_state("networkidle", timeout=10_000)
    except PlaywrightTimeoutError:
        # The application intentionally polls live status on some routes.
        page.wait_for_timeout(750)
    page.locator("h1").first.wait_for(state="visible")
    if path == "/":
        page.wait_for_timeout(3_400)
    overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    if overflow > 1:
        issues.append(f"{path} at {width}px has {overflow}px horizontal overflow")

    if path == "/":
        handwriting = page.get_by_role("img", name="proof, attached.")
        if handwriting.count() != 1 or not handwriting.is_visible():
            issues.append(f"Landing handwriting SVG is missing at {width}px")
        else:
            path_metrics = handwriting.locator("path").evaluate(
                """path => {
                  const box = path.getBBox();
                  return { width: box.width, fillOpacity: Number(getComputedStyle(path).fillOpacity) };
                }"""
            )
            if path_metrics["width"] < 300 or path_metrics["fillOpacity"] < 0.95:
                issues.append(f"Landing handwriting did not finish drawing at {width}px: {path_metrics}")

    page.screenshot(path=str(ARTIFACTS / screenshot), full_page=True)
    page.close()
    return issues


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    issues: list[str] = []
    runtime_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
        )
        scenarios = [
            ("/", "landing-desktop.png", 1440, 1000),
            ("/", "landing-mobile.png", 390, 844),
            ("/inbox", "inbox-desktop.png", 1440, 1000),
            ("/console", "console-mobile.png", 390, 844),
            ("/usage", "usage-desktop.png", 1440, 1000),
            ("/approvals", "approvals-desktop.png", 1440, 1000),
        ]
        for scenario in scenarios:
            issues.extend(inspect(browser, *scenario, runtime_errors))
        browser.close()

    meaningful_runtime_errors = [
        error for error in runtime_errors
        if "Failed to load resource" not in error and "ERR_CONNECTION_REFUSED" not in error
    ]
    issues.extend(meaningful_runtime_errors)

    if issues:
        raise SystemExit("\n".join(f"- {issue}" for issue in issues))
    print("Visual smoke test passed: 6 responsive screenshots, no overflow or runtime errors.")


if __name__ == "__main__":
    main()
