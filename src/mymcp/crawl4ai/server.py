
import subprocess
import sys
from pathlib import Path

def ensure_playwright_browsers():
    """Ensure Playwright's chromium browser is installed."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
    except Exception:
        print("Installing Playwright browser (first run)...", file=sys.stderr)
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )

from ..server import MCPServer
from . import Crawler

crawler = Crawler()

def run():

    ensure_playwright_browsers()
    
    crawler = Crawler()
    
    server = MCPServer()
    server.start(crawler.tools)

