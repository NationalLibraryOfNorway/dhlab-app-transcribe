"""End-to-end check of the GitHub Pages app in headless Chrome.

Usage: start `pdm run serve`, then `pdm run python tests/e2e_browser.py <audio file>`.
"""

import sys
import time

from playwright.sync_api import sync_playwright

URL = "http://localhost:8000/"


def main(audio_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page()
        page.on("pageerror", lambda e: print("pageerror:", e))
        page.on("console", lambda m: m.type == "error" and print("console error:", m.text[:500]))
        page.goto(URL)
        page.get_by_role("button", name="Transcribe").wait_for(timeout=300_000)
        print("App loaded")

        page.get_by_label("Upload file").click()
        page.locator('input[type="file"]').first.set_input_files(audio_path)
        page.wait_for_timeout(2000)
        page.get_by_label("Model").click()
        page.get_by_role("option", name="NB-Whisper tiny (~120 MB)").click()
        page.get_by_role("button", name="Transcribe").click()

        box = page.locator("#transcription textarea")
        start = time.monotonic()
        while time.monotonic() - start < 600:
            if text := box.input_value():
                print(f"Transcription after {time.monotonic() - start:.0f}s: {text!r}")
                break
            if page.locator(".toast-body.error").count():
                print("Error toast:", page.locator(".toast-body.error").first.inner_text())
                break
            page.wait_for_timeout(2000)
        else:
            print("No transcription within timeout")
        page.screenshot(path="e2e_screenshot.png", full_page=True)
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1])
