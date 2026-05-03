
from ..server import MCPServer
from .reddit import RedditCrawler

def run():

    tools = []

    reddit_crawler = RedditCrawler(".reddit_cache", 5)

    tools += [
        reddit_crawler.get_top_submission_headers_in_subreddit, 
        reddit_crawler.get_top_submission_headers, 
        reddit_crawler.search_submission_headers_in_subreddit,
        reddit_crawler.search_submission_headers,
        reddit_crawler.get_submission,
    ]
    
    server = MCPServer()
    server.start(tools)
