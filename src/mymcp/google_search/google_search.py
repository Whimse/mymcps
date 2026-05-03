import os
from googleapiclient.discovery import build
from typing import List
from dateutil.parser import parse as parse_date, ParserError

from ..url import Resource


class GoogleSearchHelper2:


'''
class GoogleSearchHelper:
    def __init__(self):
        self.api_key = os.environ['GOOGLE_API_KEY'],
        self.cse_id =  os.environ['GOOGLE_SEARCH_ENGINE_ID'],
        self.service = build("customsearch", "v1", developerKey=self.api_key)

    def search(self, query: str, num_results: int = 10) -> List[Resource]:
        res = self.service.cse().list(q=query, cx=self.cse_id, num=min(num_results, 10)).execute()
        items = res.get("items", [])
        results = []

        for item in items:
            link = item.get("link")
            title = item.get("title")
            snippet = item.get("snippet")
            pagemap = item.get("pagemap", {})

            # Try to extract date from metadata if available
            raw_date = None
            metatags = pagemap.get("metatags", [{}])
            if metatags:
                tag = metatags[0]
                raw_date = tag.get("article:published_time") or tag.get("og:updated_time")

            date = None
            if raw_date:
                try:
                    date = parse_date(raw_date)
                except (ParserError, ValueError):
                    pass

            # Extract thumbnail (usually small preview image)
            thumbnail_url = None
            thumbnails = pagemap.get("cse_thumbnail", [])
            if thumbnails:
                thumbnail_url = thumbnails[0].get("src")

            # Extract full image preview if available
            image_url = None
            images = pagemap.get("cse_image", [])
            if images:
                image_url = images[0].get("src")

            url = Resource(
                location=link,
                title=title,
                description=snippet,
                date=date,
                thumbnail=thumbnail_url,
                image=image_url
            )
            results.append(url)

        return results
'''        