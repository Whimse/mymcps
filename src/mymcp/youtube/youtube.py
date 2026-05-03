import os
from googleapiclient.discovery import build
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from ..url import Resource

from youtube_transcript_api import YouTubeTranscriptApi

def get_youtube_transcript(video_url):
    """
    Fetches the full text transcript for a given YouTube video URL.

    Args:
        video_url: The full watch URL (e.g., https://www.youtube.com/watch?v=...).
    """
    yt_prefix = "https://www.youtube.com/watch?v="
    assert video_url.startswith(yt_prefix)
    
    # Remove youtube initial stuff
    video_id = video_url.replace(yt_prefix, "")
    
    # Remove trailing parameters
    video_id = video_id.split("&")[0]
    
    ytt_api = YouTubeTranscriptApi()
    subs = ytt_api.fetch(video_id)
    transcripts = []
    for ts in subs.snippets:
        transcripts.append(ts.text.strip())
    return " ".join(transcripts)

class YouTubeHelper:
    def __init__(self):
        """
        Initializes the YouTube Data API client with the provided API key.
        """
        
        assert os.environ['GOOGLE_API_KEY'], f"Missing GOOGLE_API_KEY"
        
        self.api_key = os.environ['GOOGLE_API_KEY']
        self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def _ensure_video_id(self, video_input: str) -> str:
        """
        Ensures the input is a video ID. If it's a URL, extracts the ID.
        """
        if len(video_input) == 11 and '/' not in video_input:
            return video_input  # Likely a video ID
        return self._extract_video_id(video_input)

    def _extract_video_id(self, url: str) -> str:
        """
        Extracts the video ID from a YouTube URL.
        Supports full and short formats.
        """
        parsed_url = urlparse(url)
        if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
            return parse_qs(parsed_url.query).get('v', [None])[0]
        elif parsed_url.hostname == 'youtu.be':
            return parsed_url.path.strip('/')
        return None

    def tools(self, write_permission = False):

        read_tools = [
            self.get_video_snippet,
            self.get_channel_name,
            self.get_channel_id,
            self.get_video_date,
            self.get_channel_snippet,
            self.get_video_channel_logo_url,
            self.get_recent_videos_by_channel_name,
            self.get_top_viewed_videos_by_channel_name,
            self.search_videos,
        ]
        
        write_tools = [
        ]
        
        if write_permission:
            return read_tools + write_tools
        else:
            return read_tools


    def get_video_snippet(self, video_input: str) -> dict:
        """
        Returns the video snippet (metadata) for a given video URL or ID.
        """
        video_id = self._ensure_video_id(video_input)
        if not video_id:
            raise ValueError("Invalid or unsupported YouTube video input")

        response = self.youtube.videos().list(
            part='snippet',
            id=video_id
        ).execute()

        if not response['items']:
            raise ValueError(f"No video found for ID: {video_id}")

        return response['items'][0]['snippet']
    
    def get_channel_name(self, video_input: str) -> str:
            """
            Returns the channel name and upload date as a datetime object for a video.
            """
            snippet = self.get_video_snippet(video_input)

            channel_title = snippet['channelTitle']

            return channel_title

    def get_channel_id(self, video_input: str) -> str:
            """
            Returns the channel name and upload date as a datetime object for a video.
            """
            snippet = self.get_video_snippet(video_input)
            return snippet['channelId']
            
    def get_video_date(self, video_input: str) -> tuple[str, datetime]:
        """
        Returns the channel name and upload date as a datetime object for a video.
        """
        snippet = self.get_video_snippet(video_input)

        upload_date_str = snippet['publishedAt']  # Example: "2023-06-15T12:34:56Z"
        return datetime.strptime(upload_date_str, "%Y-%m-%dT%H:%M:%SZ")

    def get_channel_snippet(self, channel_id:str):
        """
        Retrieves metadata (title, description, thumbnails) for a YouTube channel.

        Args:
            channel_id: The unique YouTube ID (e.g., 'UCxxxxxxxxxxxx').
        """        
        response = self.youtube.channels().list(
            part='snippet',
            id=channel_id
        ).execute()

        if not response['items']:
            raise ValueError(f"No channel found for ID: {channel_id}")

        return response['items'][0]['snippet']

    def get_video_channel_logo_url(self, video_input: str) -> str:
        """
        Retrieves the channel logo (profile picture) URL given a video URL or ID.
        Internally also accesses the channel name and upload date.
        """
        snippet = self.get_video_snippet(video_input)
        channel_id = snippet['channelId']

        thumbnails = self.get_channel_snippet(channel_id)['thumbnails']
        return thumbnails.get('high', thumbnails.get('default'))['url']
    

    def get_recent_videos_by_channel_name(self, channel_name: str, days: int) -> list[Resource]:
        """
        Retrieves a list of recent videos published on the specified channel in the last `days` days.
        Returns a list of URL dataclass instances.
        """
        # Search for the channel ID using the channel name
        search_response = self.youtube.search().list(
            part="snippet",
            q=channel_name,
            type="channel",
            maxResults=1
        ).execute()

        if not search_response['items']:
            raise ValueError(f"Channel not found for name: {channel_name}")

        channel_id = search_response['items'][0]['snippet']['channelId']

        # Get Uploads playlist ID for the channel
        playlist_response = self.youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()

        uploads_playlist_id = playlist_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Calculate datetime threshold
        since_date = datetime.utcnow() - timedelta(days=days)

        # Get videos from the uploads playlist
        videos = []
        next_page_token = None
        stop_fetching = False

        while not stop_fetching:
            
            video_snippets_response = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            # Extract video IDs and map them to snippets
            video_snippets = {
                item['snippet']['resourceId']['videoId']: item['snippet']
                for item in video_snippets_response['items']
            }

            # Batch fetch statistics for those video IDs
            video_stats_response = self.youtube.videos().list(
                part="statistics",
                id=",".join(video_snippets.keys())
            ).execute()

            # Extract statistics keyed by video ID
            video_stats = {
                item['id']: item['statistics']
                for item in video_stats_response['items']
            }

            # Combine snippets and statistics into a final dict
            video_data = {
                video_id: (video_snippets[video_id], video_stats[video_id])
                for video_id in video_snippets
                if video_id in video_stats  # ensures we don't crash if stats missing
            }

            # Correctly unpack the tuple from the dict values
            for video_id, (snippet, statistics) in video_data.items():

                like_count = int(statistics['likeCount'])
                view_count = int(statistics['viewCount'])
                #comment_count = statistics['commentCount']
                
                published_at = datetime.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")

                if published_at < since_date:
                    stop_fetching = True
                    break  # Stop processing this page and don't continue to next page

                video_url = f"https://www.youtube.com/watch?v={snippet['resourceId']['videoId']}"
                url_obj = Resource(
                    location=video_url,
                    title=snippet.get('title'),
                    date=published_at,
                    votes=like_count,                                        
                    source=snippet.get('channelTitle'),
                    description=snippet.get('description'),
                    thumbnail=snippet['thumbnails'].get('high', snippet['thumbnails'].get('default'))['url'],
                )
                videos.append(url_obj)

            next_page_token = video_snippets_response.get('nextPageToken')
            if not next_page_token or stop_fetching:
                break

        return videos

    def get_top_viewed_videos_by_channel_name(self, channel_name: str, max_results: int = 10) -> list[Resource]:
        """
        Retrieves the videos with the highest view counts from the given channel.
        Returns a list of URL dataclass instances sorted by view count (descending).
        """
        # Find the channel ID
        search_response = self.youtube.search().list(
            part="snippet",
            q=channel_name,
            type="channel",
            maxResults=1
        ).execute()

        if not search_response['items']:
            raise ValueError(f"Channel not found for name: {channel_name}")

        channel_id = search_response['items'][0]['snippet']['channelId']

        # Get the uploads playlist ID
        playlist_response = self.youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()

        uploads_playlist_id = playlist_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Collect all videos with their stats
        videos = []
        next_page_token = None

        while True:
            playlist_items = self.youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_playlist_id,
                maxResults=50,
                pageToken=next_page_token
            ).execute()

            video_ids = [item['snippet']['resourceId']['videoId'] for item in playlist_items['items']]

            stats_response = self.youtube.videos().list(
                part="statistics,snippet",
                id=",".join(video_ids)
            ).execute()

            for item in stats_response['items']:
                snippet = item['snippet']
                stats = item.get('statistics', {})
                view_count = int(stats.get('viewCount', 0))

                url_obj = Resource(
                    location=f"https://www.youtube.com/watch?v={item['id']}",
                    title=snippet.get('title'),
                    date=datetime.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ"),
                    votes=int(stats.get('likeCount', 0)),
                    source=snippet.get('channelTitle'),
                    description=snippet.get('description'),
                    thumbnail=snippet['thumbnails'].get('high', snippet['thumbnails'].get('default'))['url'],
                )
                url_obj.views = view_count
                videos.append(url_obj)

            next_page_token = playlist_items.get('nextPageToken')
            if not next_page_token:
                break

        # Sort all videos by view count and return the top ones
        videos.sort(key=lambda v: getattr(v, 'views', 0), reverse=True)
        return videos[:max_results]


    def search_videos(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Searches YouTube for videos matching the given query.
        Returns a list of dictionaries with video title, URL, channel, and publish date.
        """
        response = self.youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results
        ).execute()

        if not response['items']:
            return []

        results = []
        for item in response['items']:
            video_id = item['id']['videoId']
            snippet = item['snippet']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            results.append({
                "title": snippet['title'],
                "url": video_url,
                "channel": snippet['channelTitle'],
                "published_at": snippet['publishedAt'],
                "thumbnail": snippet['thumbnails'].get('high', snippet['thumbnails'].get('default'))['url']
            })

        return results