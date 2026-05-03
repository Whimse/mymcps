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

class GoogleScholarHelper:
    
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

    async def search_google_scholar(self, search:str) -> List[Article]:
        """
        Search Google Scholar.
        
        Args:
            search: Search query string
            
        Returns:
            List of matching Article objects, containing their title, URL, ID and number of citations
        """        
        html = await self.crawler.crawl(f"https://scholar.google.com/scholar?q={quote_plus(search)}&hl=en")
        return self.__get_articles_references(html)
 
    async def get_article_citations(self, ID:str) -> List[Article]:
        """
        Get articles that cite a given article provided its ID
        
        Args:
            ID: Google Scholar article identifier
            
        Returns:
            List of citing articles, each one described by its title, URL, ID and number of citations
        """        
        html = await self.crawler.crawl(f"https://scholar.google.com/scholar?cites={ID}&hl=en")
        return self.__get_articles_references(html)      

'''
h = GoogleScholarHelper()
 
articles = asyncio.run(h.get_citations("6702537121991453445"))

for a in articles:
    print("=====")
    print(a)
''' 


