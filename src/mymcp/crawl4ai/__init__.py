import os
# Tell Node.js to suppress all deprecation warnings
os.environ["NODE_OPTIONS"] = "--no-deprecation"

from mymcp.utils import get_main_domain

from crawl4ai import (
    BrowserConfig,
    AsyncWebCrawler,
    CacheMode,
    CrawlerRunConfig,
    ProxyConfig,
)

from crawl4ai.async_logger import AsyncLogger, LogLevel
import warnings

'''
How to navigate with credentials for webpages (e.g. LinkedIn)

1. Create a profile:
    crwl profiles

2. List profiles, or create a new one (options 1, 2)

3. Launch a browser and log into pages with credentials:

    user_data_dir = "... path to profile data, from step 2
    crawler = Crawler(user_data_dir = user_data_dir)
    html_code = await crawler.crawl("https://www.linkedin.com", persistent_browser = True)

4. Crawl that page repeatedly, to get data:
    crawler = Crawler(user_data_dir = user_data_dir)
    html_code = await crawler.crawl("https://www.linkedin.com", persistent_browser = True)
'''
class Crawler:
    
    def __init__(self,
        # Get paths with command line 'crwl profiles / 1. List profiles'
        user_data_dir = None
        ):
        
        try:        
            self.proxy_config = ProxyConfig(
                server = os.environ['PROXY_SERVER'],
                username = os.environ['PROXY_USERNAME'],
                password = os.environ['PROXY_PASSWORD'],
            )
        except KeyError as e:
            warn_msg = f"Could not find proxy config variables in environment: {', '.join(e.args)}. Launching crawler without proxy"
            warnings.warn(warn_msg, UserWarning)            
            self.proxy_config = BrowserConfig().proxy_config
        
        self.effective_proxies = dict()
        self.user_data_dir = user_data_dir
    
    # make the tool method async
    async def crawl_tool(self, url: str):
        """
        Retrieves the contents of a web page given its url.
        Provides the contents in markdown format.

        Args:
            url (str): The url to crawl.

        Returns:
            str: The contents of the page in markdown format.
        """

        return await self.crawl(url, markdown=True)
    
    async def crawl(
        self,
        site_url:str,
        headless:bool = False,        
        num_retries = 2,    
        markdown:bool = False,
        persistent_browser:bool = False,
        ):

        domain = get_main_domain(site_url)

        logger = AsyncLogger(log_level = LogLevel.FATAL)        
        
        for retry in range(num_retries):
            
            browser_config = BrowserConfig(
                verbose=False, 
                headless=headless,
                user_data_dir = self.user_data_dir,
                use_managed_browser=True,
                proxy_config = self.effective_proxies.get(domain, BrowserConfig().proxy_config)
            )

            async with AsyncWebCrawler(config=browser_config, logger = logger) as crawler:

                    result = await crawler.arun(
                        url=site_url,
                        config=CrawlerRunConfig(
                            wait_for="css:non-existant_selector" if persistent_browser else None,
                            magic = True,
                            cache_mode=CacheMode.BYPASS,
                        )
                    )

                    # If page does contain Cloudflare, update proxy
                    # else, stop
                    if "cloudflare" in result.html.lower():
                        print(f"[CRAWLER] Cloudflare detected for domain '{domain}' in url '{site_url}'. Enabling proxy for all urls for that domain.")
                        self.effective_proxies[domain] = self.proxy_config
                    else:
                        break
                    
        if markdown:
            return result.markdown
        else:
            return result.html