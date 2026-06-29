import os
import time
from typing import List, Optional
import praw
import prawcore
from datetime import datetime
from mymcp.url import Resource, Comment
import re

REDDIT_MEDIA_RE = re.compile(
    r'^https?://(?:i|v)\.redd\.it/[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)?$'
)

def is_url_from_reddit(url: str) -> bool:
    if url.startswith("https://www.reddit.com/"):
        return True
    return bool(REDDIT_MEDIA_RE.fullmatch(url))

def serialize_data(data):
    if type(data) in [int, bool, float]:
        return data
    elif type(data) in [str]:
        return data
    elif type(data) in [list, dict]:
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
            import html
            preview_url = html.unescape(preview_url)
        except (KeyError, IndexError):
            pass

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

    return sorted(result, key=lambda c: c.votes, reverse=True)

def reddit_submission_to_URL(submission, just_headline=False) -> Resource:
    return Resource(
        location=f"https://www.reddit.com{submission.permalink}",
        title=submission.title,
        flair=submission.link_flair_text,
        date=datetime.utcfromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
        votes=submission.ups,
        forward_url=None if is_url_from_reddit(submission.url) else submission.url,
        source=f"r/{submission.subreddit}",
        thumbnail=reddit_submission_preview_url(submission),
        content=None if just_headline else submission.selftext.rstrip(),
        comments=None if just_headline else parse_comments(submission.comments)
    )

def check_time_filter(time_filter):
    valid_time_filters = ['all', 'year', 'month', 'week', 'day', 'hour']
    if time_filter not in valid_time_filters:
        raise ValueError(f"Invalid value for 'time_filter': must be one of {', '.join(valid_time_filters)}, got '{time_filter}'")

def URLs_to_headlines(URLs: List[Resource]) -> List[Resource]:
    return [url.to_headline() for url in URLs]

def _praw_error_message(e: Exception) -> str:
    if isinstance(e, prawcore.exceptions.NotFound):
        return "Reddit returned 404: the post, subreddit, or resource was not found (deleted, removed, or banned)."
    elif isinstance(e, prawcore.exceptions.Forbidden):
        return "Reddit returned 403: access is forbidden (private subreddit or insufficient permissions)."
    elif isinstance(e, prawcore.exceptions.Redirect):
        return "Reddit returned a redirect: the subreddit may not exist."
    elif isinstance(e, prawcore.exceptions.TooManyRequests):
        return "Reddit rate limit exceeded: too many requests. Please try again later."
    elif isinstance(e, prawcore.exceptions.ServerError):
        return f"Reddit server error: {e}"
    elif isinstance(e, prawcore.exceptions.RequestException):
        return f"Network error when contacting Reddit: {e}"
    else:
        return f"Unexpected error: {e}"


class RedditCrawler:
    def __init__(self, num_posts: int = 10):
        self.num_posts = num_posts

        reddit_credentials = dict(
            client_id=os.environ.get('REDDIT_CLIENT_ID', None),
            client_secret=os.environ.get('REDDIT_CLIENT_SECRET', None),
            user_agent=os.environ.get('REDDIT_USER_AGENT', None),
            username=os.environ.get('REDDIT_USERNAME', None),
            password=os.environ.get('REDDIT_PASSWORD', None),
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

    def get_top_headlines_in_subreddit(self, subreddit: str, time_filter: str) -> List[Resource] | str:
        """
        Provides the headlines for the top most recent submissions in a subreddit (or the whole Reddit) within a time frame.

        Args:
            subreddit (str): Name of the subreddit to search.
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour'.

        Returns:
            A list of Reddit submission headlines, or an error string if the request failed.
        """
        check_time_filter(time_filter)
        try:
            submissions = self.__get_node(subreddit).top(limit=self.num_posts, time_filter=time_filter)
            return self.__submissions_to_URLs(submissions, just_headlines=True)
        except (prawcore.exceptions.PrawcoreException, Exception) as e:
            return _praw_error_message(e)

    def get_top_submissions_in_subreddit(self, subreddit: str, time_filter: str) -> List[Resource] | str:
        """
        Provides the top most recent submissions in a subreddit (or the whole Reddit) within a time frame.

        Args:
            subreddit (str): Name of the subreddit to search.
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour'.

        Returns:
            A list of Reddit submissions, or an error string if the request failed.
        """
        check_time_filter(time_filter)
        try:
            submissions = self.__get_node(subreddit).top(limit=self.num_posts, time_filter=time_filter)
            return self.__submissions_to_URLs(submissions)
        except (prawcore.exceptions.PrawcoreException, Exception) as e:
            return _praw_error_message(e)

    def search_submissions_in_subreddit(self, query: str, subreddit: str, time_filter: str) -> List[Resource] | str:
        """
        Searches for the most recent Reddit submissions within a given subreddit and time frame.

        Args:
            query (str): The query to use in the Reddit search.
            subreddit (str): Name of the subreddit to search.
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour'.

        Returns:
            A list of Reddit submissions, or an error string if the request failed.
        """
        check_time_filter(time_filter)
        try:
            submissions = self.__get_node(subreddit).search(query, time_filter=time_filter, limit=self.num_posts)
            return self.__submissions_to_URLs(submissions)
        except (prawcore.exceptions.PrawcoreException, Exception) as e:
            return _praw_error_message(e)

    ###############
    # Headers
    ###############

    def search_submission_headers_in_subreddit(self, query: str, subreddit: str, time_filter: str) -> List[Resource] | str:
        """
        Searches for the most recent Reddit submission headlines within a given subreddit and time frame.

        Args:
            query (str): The query to use in the Reddit search.
            subreddit (str): Name of the subreddit to search.
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour'.

        Returns:
            A list of Reddit submission headlines, or an error string if the request failed.
        """
        result = self.search_submissions_in_subreddit(query, subreddit, time_filter)
        if isinstance(result, str):
            return result
        return URLs_to_headlines(result)

    def get_top_submission_headers_in_subreddit(self, subreddit: str, time_filter: str) -> List[Resource] | str:
        """
        Provides the top most recent submission headlines in a subreddit within a time frame.

        Args:
            subreddit (str): Name of the subreddit to search.
            time_filter (str): Set to 'all', 'year', 'month', 'week', 'day' or 'hour'.

        Returns:
            A list of Reddit submission headlines, or an error string if the request failed.
        """
        result = self.get_top_submissions_in_subreddit(subreddit, time_filter)
        if isinstance(result, str):
            return result
        return URLs_to_headlines(result)

    def get_top_submission_headers(self, time_filter: str) -> List[Resource] | str:
        """
        Provides the top most recent submission headlines across all of Reddit within a time frame.

        Args:
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour'.

        Returns:
            A list of Reddit submission headlines, or an error string if the request failed.
        """
        return self.get_top_submission_headers_in_subreddit('all', time_filter)

    def search_submission_headers(self, query: str, time_filter: str) -> List[Resource] | str:
        """
        Searches for the most recent Reddit submission headlines within a time frame.

        Args:
            query (str): The query to use in the Reddit search.
            time_filter (str): Set it to 'all', 'year', 'month', 'week', 'day' or 'hour'.

        Returns:
            A list of Reddit submission headlines, or an error string if the request failed.
        """
        return self.search_submission_headers_in_subreddit(query, 'all', time_filter)

    #####################
    # Single submission
    #####################

    def get_submission(self, submission_url: str) -> Resource | str:
        """
        Retrieves the whole content of a Reddit submission, including full body and top comments.

        Args:
            submission_url (str): The submission URL.

        Returns:
            The full contents of the submission, or an error string if the request failed.
        """
        assert submission_url.startswith('https://www.reddit.com/r')
        try:
            submission_id = submission_url.strip('/').split('/')[6]
            submission = self.reddit.submission(id=submission_id)
            submission.comments.replace_more(limit=None)
            return reddit_submission_to_URL(submission)
        except (prawcore.exceptions.PrawcoreException, Exception) as e:
            return _praw_error_message(e)