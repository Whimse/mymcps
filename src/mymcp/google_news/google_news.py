### MODULES
import time
import random
import urllib.request
from ..url import Resource

from GoogleNews import GoogleNews

def search_google_news(
    search:str = "",
    pages:int = 1,
    min_delay:float = 2.5,
    max_delay:float = 7.0,
    lang:str='en',
    period:str='7d',
    publisher_url:str = None
    ):

    # Sanity check for lang
    assert len(lang) == 2 and all(char.isalpha() for char in lang), f"'lang' parameter string must be two alphanumeric letters representing language code"
    
    # Sanity checks for 'period' input
    assert any(period.endswith(postfix) for postfix in ['h', 'd', 'm', 'y']), f"'period' parameter string must finish with 'h', 'd', 'm' or 'y'"
    assert all(char.isdigit() for char in period[:-1]), f"'period' parameter string must be an integer number followed by 'h', 'd', 'm' or 'y'"

    # Composing search string
    encode = "utf-8"

    if publisher_url:
        search_final = f"site:{publisher_url} {search}" 
    else:
        search_final = search

    search_final = urllib.request.quote(search_final.encode(encode))
    
    # Create Google News search object
    google_news = GoogleNews(lang=lang, period=period, encode = encode)  # Last 7 days

    # Set search key in Google News object
    setattr(google_news, f"_{google_news.__class__.__name__}__key", search_final)
   
    for num_page in range(1, pages+1):
        # Uniform delay
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
        google_news.get_page(num_page)
    
    news = []

    for n in google_news.result():

        story = Resource(
            location = n['link'].split("&ved=")[0],
            title = n['title'],
            flair = None,
            date = n['datetime'],
            votes = None,
            forward_url = None,
            source = n['media'],            
            media = n['img'],            
            content = n['desc'],        
            comments = None,
        )

        news.append(story)
        
    return news
