"""Uses pywright to load a webpage and get the cookie"""
from playwright.sync_api import sync_playwright


def get_browser_cookie(url: str, headless=True) -> dict:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        page.goto(url)
        cookies = context.cookies()
        browser.close()
    return cookies
