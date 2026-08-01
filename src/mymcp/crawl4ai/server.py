             
        
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
        
 import subprocess
import threading
import time

def start_chrome_headless():
    def _run():
        process = subprocess.Popen(
            [
                "/opt/playwright-browsers/chromium-1234/chrome-linux64/chrome",
                "--headless=new",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--remote-debugging-port=9222",
                "--remote-debugging-address=0.0.0.0",
                "about:blank"
            ],
            stdout=open("/tmp/chrome.log", "w"),
            stderr=subprocess.DEVNULL
        )
        start_chrome_headless.process = process
        time.sleep(4)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread         

from ..server import MCPServer
from . import Crawler

crawler = Crawler()

def run():

    ensure_playwright_browsers()
    start_chrome_headless()
    
    crawler = Crawler()
    
    server = MCPServer()
    server.start(crawler.tools)

