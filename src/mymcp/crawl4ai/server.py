             
        
import subprocess
import sys

def ensure_playwright_browsers():
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            browser.close()
    except Exception:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )        

from ..server import MCPServer
from . import Crawler

crawler = Crawler()

def run():

    ensure_playwright_browsers()
    
    crawler = Crawler()
    
    server = MCPServer()
    server.start(crawler.tools)

