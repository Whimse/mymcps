from typing import List
from mymcp.crawl4ai import Crawler
from urllib.parse import quote_plus, parse_qs
from bs4 import BeautifulSoup
import asyncio
   
from pydantic import BaseModel

class Article(BaseModel):
    title: str
    id: str
    url: str
    citations:int

    def __str__(self):
        result = "Title: " + self.title + "\n"
        result += "ID: " + self.id + "\n"
        result += "URL: " + self.url + "\n"
        result += "Citations: " + str(self.citations) + "\n"        
        
        return result

class GoogleSearchHelper:
    
    def __init__(self):
        self.crawler = Crawler()

    def __get_articles_references(self, html:str):

        soup = BeautifulSoup(html, 'html.parser')

        # Find all <a> tags
        links = soup.find_all('a')

        result = []
        
        prev_title, prev_id, prev_url = [ None ] * 3
        
        for link in links:
                
            title = link.get_text()
            url = link.get('href')
            
            if title.startswith("Cited by"):
                assert prev_title is not None
                assert prev_id is not None
                assert prev_url is not None
                
                citations = int(title.split(" ")[2])
                
                article = Article(
                    title = prev_title,
                    id = prev_id,
                    url = url,
                    citations = citations
                )
                
                result.append(article)                

                prev_title, prev_id, prev_url = [ None ] * 3
            
                continue
            
            if '[PDF]' in title:
                continue
                
            # parse_qs returns a dictionary where values are lists
            if 'data-clk' not in link.attrs:
                continue
            
            data = link.attrs['data-clk']
            
            if 'd' not in data:
                continue

            prev_title, prev_id, prev_url = title, parse_qs(data)['d'][0], url
            
        return result

    async def search_google(self, search:str) -> List[Article]:
        """
        Search using Google.
        
        Args:
            search: Search query string
            
        Returns:
            List of urls matching the search
        """
        html = await self.crawler.crawl(f"https://www.google.com/search?q={quote_plus(search)}")
        return html
 

if __name__ == "__main__":
    h = GoogleSearchHelper()
    
    articles = asyncio.run(h.search_google("Chocolate cake"))
    print(articles)


