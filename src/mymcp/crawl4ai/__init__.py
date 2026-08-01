#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (C) 2026 Whimse <antlerolop@gmail.com> (https://github.com/Whimse)
# SPDX-License-Identifier: AGPL-3.0-only

# DEPRECATED by Crawl4ai MCP

import os
import asyncio
# Tell Node.js to suppress all deprecation warnings
os.environ["NODE_OPTIONS"] = "--no-deprecation"

from urllib.parse import urlparse  

def get_main_domain(url: str) -> str:
    netloc = urlparse(url).netloc or url
    parts = netloc.split('.')
    #if len(parts) >= 2:
    #    return parts[-2]
    return netloc

from crawl4ai import (
    BrowserConfig,
    AsyncWebCrawler,
    CacheMode,
    CrawlerRunConfig,
    ProxyConfig,
)

from ...config import Config
from ...context.tools import ToolSet
from crawl4ai.async_logger import AsyncLogger, LogLevel
import warnings

class Crawler:
    
    def __init__(self,
        config: Config,
        # Get paths with command line 'crwl profiles / 1. List profiles'
        #user_data_dir = None
        ):
        
        user_data_dir = config.path / "web_crawling_data"

        self.proxy_config = None        
        
        try:        
            self.proxy_config = ProxyConfig(
                server = os.environ['PROXY_SERVER'],
                username = os.environ['PROXY_USERNAME'],
                password = os.environ['PROXY_PASSWORD'],
            )
        except KeyError as e:
            warn_msg = f"Could not find proxy config variables in environment: {', '.join(e.args)}. Launching crawler without proxy"
            warnings.warn(warn_msg, UserWarning)            

        
        self.user_data_dir = user_data_dir
        self.config = config
    
    # make the tool method async
    async def crawl_failsafe(self, url: str):
        """
        Retrieves the contents of a web page given its url.
        Provides the contents in markdown format.

        Use this tool if calls to 'crawl' fail.
        
        Args:
            url (str): The url to crawl.

        Returns:
            str: The contents of the page in markdown format.
        """

        return await self.__crawl(url, markdown=True)

    # make the tool method async
    async def crawl(self, url: str):
        """
        Retrieves the contents of a web page given its url.
        Provides the contents in markdown format.

        Use this tool instead of `cral_failsafe`, under normal conditions.
        
        Args:
            url (str): The url to crawl.

        Returns:
            str: The contents of the page in markdown format.
        """

        return await self.__crawl(url, markdown=True, headless=True)

    # make the tool method async
    async def crawl_proxy(self, url: str):
        """
        Retrieves the contents of a web page given its url.
        Provides the contents in markdown format.
        Uses a proxy, for a more reliable and/or robust crawling.

        Args:
            url (str): The url to crawl.

        Returns:
            str: The contents of the page in markdown format.
        """

        return await self.__crawl(url, markdown=True, use_proxy = True)

    async def open_browser_blocking(self, url: str) -> None:
        """
        Opens a visible browser window with the given URL and waits until the user closes it before returning.
        
        Use it when the content in a page is blocked, and the user might help with it.
        
        E.g. page is behind a captcha, or needs credentials.

        Args:
            url (str): The URL to open in the browser window.
        """
        await self.__crawl(url, persistent = True)

    
    async def __crawl(
        self,
        url:str,
        headless:bool = False,        
        markdown:bool = False,
        persistent:bool = False,
        incognito: bool = False,
        use_proxy: bool = False,
        ):

        logger = AsyncLogger(log_level = LogLevel.FATAL)
        
        extra_args = [ ]        
        if incognito:
            extra_args.append("--incognito")
                    

        if use_proxy and self.proxy_config is None:
            raise Exception("Crawl4ai: requested proxy use, but no proxy configured")
        
        browser_config = BrowserConfig(
            verbose=False, 
            headless=headless,
            user_data_dir=None if incognito else self.user_data_dir,
            use_managed_browser=True,
            proxy_config = self.proxy_config if use_proxy else BrowserConfig().proxy_config,
            extra_args=extra_args,
        )

        config=CrawlerRunConfig(
            wait_for="css:non-existant_selector" if persistent else None,
            magic = True,
            cache_mode=CacheMode.BYPASS,
        )

        async with AsyncWebCrawler(config=browser_config, logger = logger) as crawler:
            result = await crawler.arun(url=url, config=config)

        if markdown:
            return result.markdown
        else:
            return result.html
        

    @property
    def tools(self):
        
        tools = [ self.crawl, self.crawl_failsafe, self.open_browser_blocking ]
        
        if self.proxy_config:
            tools += [ self.crawl_proxy ]
            
        return ToolSet(tools)
    
