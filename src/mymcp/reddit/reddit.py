import os
import time
from typing import List, Annotated
from tqdm import tqdm
import praw
import time
from datetime import datetime
from mymcp.url import Resource, Comment
import re

REDDIT_MEDIA_RE = re.compile(
    r'^https?://(?:i|v)\.redd\.it/[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)?$'
)

def is_url_from_reddit(url: str) -> bool:
    
    if url.startswith("https://www.reddit.com/"):
        return True
    
    """Return True if *url* looks like i.redd.it or v.redd.it media."""
    return bool(REDDIT_MEDIA_RE.fullmatch(url))

# Parses data to return something serialisable
def serialize_data(data):
    if type(data) in [ int, bool, float ]:
        return data
    elif type(data) in [ str ]:
        return data
    elif type(data) in [ list, dict ]:
        return 
    elif data is None:
        return None
    else:
        return str(data)
        
def reddit_submission_preview_url(submission):
    preview_url = None

    if hasattr(submission, "preview"):
        try:
            preview_url = submission.preview["images"][0]["source"]["url"]
            # Unescape HTML characters
            import html
            preview_url = html.unescape(preview_url)
        except (KeyError, IndexError):
            pass

    # Fallback to thumbnail
    if not preview_url or not preview_url.startswith("http"):
        if submission.thumbnail.startswith("http"):
            preview_url = submission.thumbnail    

    return preview_url

def parse_comments(comments):
    
    result = []    
    for comment in comments:
        if not hasattr(comment, "ups") or not comment.ups:
            continue
        
        if not hasattr(comment, 'author') or not comment.author:
            continue

        if hasattr(comment, "comments") and comment.comments:
            nested_comments = parse_comments(comment.comments)
        else:
            nested_comments = []
        
        comment_ = Comment(
            comment.author.name,
            comment.ups,
            comment.body,
            nested_comments,
            )

        result.append(comment_)

    return sorted(result, key = lambda c: c.votes, reverse=True)   
    
def reddit_submission_to_URL(submission, just_headline = False) -> Resource:
    
    # Convert submission data into dictionary
    return Resource(
        location =  f"https://www.reddit.com{submission.permalink}",
        title = submission.title,
        flair = submission.link_flair_text,
        date = datetime.utcfromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
        votes = submission.ups,
        forward_url = None if is_url_from_reddit(submission.url) else submission.url,
        source = f"r/{submission.subreddit}",
        thumbnail = reddit_submission_preview_url(submission),
        content = None if just_headline else submission.selftext.rstrip(),
        comments = None if just_headline else parse_comments(submission.comments)  
        )

def check_time_filter(time_filter):
    valid_time_filters = ['all', 'year', 'month', 'week', 'day', 'hour']
    if time_filter not in valid_time_filters:
        raise Exception(f"Provided invalid value for 'time_filter' in Reddit request, Must be one in {', '.join(valid_time_filters)}, not '{time_filter}'")

def URLs_to_headlines(URLs:List[Resource]) -> List[Resource]:
    
    return [ url.to_headline()  for url in URLs ]

class RedditCrawler:
    def __init__(
            self,
            num_posts: int = 10,
        ):
        self.num_posts = num_posts
        
        reddit_credentials = dict(
            client_id = os.environ.get('REDDIT_CLIENT_ID', None),
            client_secret = os.environ.get('REDDIT_CLIENT_SECRET', None),
            user_agent = os.environ.get('REDDIT_USER_AGENT', None),
            username = os.environ.get('REDDIT_USERNAME', None),
            password = os.environ.get('REDDIT_PASSWORD', None),
        )
        
        self.reddit = praw.Reddit(**reddit_credentials)
        
    def __get_node(self, subreddit):
        if subreddit.startswith('r/'):
            subreddit = subreddit[2:]
            
        if '.' in subreddit:
            return self.reddit.domain(subreddit)
        else:
            return self.reddit.subreddit(subreddit)
        
             
    def __submissions_to_URLs(
        self,
        submissions,
        time_delay: int = 0,
        just_headlines: bool = False,
        ) -> List[Resource]:
                
        stories = []

        for submission in submissions:
            url: Resource = reddit_submission_to_URL(submission, just_headlines)
            time.sleep(time_delay)
            stories.append(url)

        return stories

    def get_top_headlines_in_subreddit(self, subreddit: str, time_filter: str) -> List[Resource]:
        """
        Provides the headlines for the top most recent submissions in a subreddit (or the whole Reddit) within a time frame
        
        Args:
            subreddit (str): Name of the subreddit to search.
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour' to select the search timeframe.
            
        Returns:
            str: A list of Reddit submissions that match the query
        """        
        check_time_filter(time_filter)
        submissions = self.__get_node(subreddit).top(limit=self.num_posts, time_filter=time_filter)
        return self.__submissions_to_URLs(submissions, just_headlines=True)


    def get_top_submissions_in_subreddit(self, subreddit: str, time_filter: str) -> List[Resource]:
        """
        Provides the top most recent submissions in a subreddit (or the whole Reddit) within a time frame
        
        Args:
            subreddit (str): Name of the subreddit to search.
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour' to select the search timeframe.
            
        Returns:
            str: A list of Reddit submissions that match the query
        """        
        check_time_filter(time_filter)
        submissions = self.__get_node(subreddit).top(limit=self.num_posts, time_filter=time_filter)
        return self.__submissions_to_URLs(submissions)

    def search_submissions_in_subreddit(self, query: str, subreddit:str, time_filter: str) -> List[Resource]:
        """
        Searches for the most recent Reddit submissions, within a given subreddit and time frame, that match a given query search
        
        This function provides just their headlines (title, url and date).

        Args:
            query (str): The query to use in the Reddit search.
            subreddit (str): Name of the subreddit to search.
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour' to select the search timeframe.
            
        Returns:
            str: A list of headers of reddit submissions that match the query
        """       
        check_time_filter(time_filter)
        submissions = self.__get_node(subreddit).search(query, time_filter=time_filter, limit=self.num_posts)
        return self.__submissions_to_URLs(submissions)
    
    ###############
    # Headers
    ###############    

    def search_submission_headers_in_subreddit(self, query: str, subreddit:str, time_filter: str) -> List[Resource]:
        """
        Searches for the most recent Reddit submissions, within a given subreddit and time frame, that match a given query search
        
        This function provides just their headlines (title, url and date).

        Args:
            query (str): The query to use in the Reddit search.
            subreddit (str): Name of the subreddit to search.
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour' to select the search timeframe.
            
        Returns:
            str: A list of headers of reddit submissions that match the query
        """       
        return URLs_to_headlines(self.search_submissions_in_subreddit(query, subreddit, time_filter))
    
    def get_top_submission_headers_in_subreddit(self, subreddit: str, time_filter: str) -> List[Resource]:
        """
        Provides the top most recent submissions in a subreddit within a time frame.

        Args:
            subreddit: Name of the subreddit to search.
            time_filter: Set to 'all', 'year', 'month', 'week', 'day' or 'hour'.

        Returns:
            A list of headers of reddit submissions that match the query.
        """
        return URLs_to_headlines(self.get_top_submissions_in_subreddit(subreddit, time_filter))


    def get_top_submission_headers(self, time_filter: str) -> List[Resource]:
        """
        Provides the top most recent submissions in the whole Reddit space, within a time frame

        This function provides just their headlines (title, url and date).
        
        Args:
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour' to select the search timeframe.
            
        Returns:
            str: A list of headers of reddit submissions that match the query
        """                
        return self.get_top_submission_headers_in_subreddit('all', time_filter)
    
    def search_submission_headers(self, query: str, time_filter: str) -> List[Resource]:
        """
        Searches for the most recent Reddit submissions within a time frame that match a given query search
        
        This function provides just their headlines (title, url and date).

        Args:
            query (str): The query to use in the Reddit search.
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour' to select the search timeframe
            
        Returns:
            str: A list of headers of reddit submissions that match the query
        """
        return self.search_submission_headers_in_subreddit(query, 'all', time_filter)

    #####################
    # Single submission
    #####################   
    def get_submission(self, submission_url: str) -> Resource:
        """
        Retrieves the whole content of a Reddit submission, including
        full body and top comments.

        Args:
            submission_url (str): The submission URL.

        Returns:
            Resource: The full contents of the submission, including
                      full body and top comments.
        """
        assert submission_url.startswith('https://www.reddit.com/r')

        submission_id = submission_url.strip('/').split('/')[6]
        submission = self.reddit.submission(id=submission_id)
        submission.comments.replace_more(limit=None)

        return reddit_submission_to_URL(submission)
    
    