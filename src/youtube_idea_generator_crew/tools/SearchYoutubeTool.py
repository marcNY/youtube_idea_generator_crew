import os
from typing import Type
from crewai.tools import BaseTool
import requests
from pydantic import BaseModel, Field


class VideoSearchResult(BaseModel):
    title: str
    channel_id: str
    video_id: str
    channel_title: str
    days_since_published: str


class VideoDetails(BaseModel):
    title: str
    url: str
    view_count: int


class YoutubeVideoSearchAndDetailsToolInput(BaseModel):
    """Input schema for YoutubeVideoSearchAndDetailsTool."""

    keywords: str = Field(
        ..., description="A list of keywords to search for in YouTube videos."
    )
    max_results: int = Field(3, description="The maximum number of results to return.")


class YoutubeVideoSearchAndDetailsTool(BaseTool):
    """Tool that searches YouTube videos."""

    name: str = "Search and get details of YouTube videos"
    description: str = """
        Searches Youtube vdeos bases on a keyword and retrieves details for each video.
    """
    args_schema: Type[BaseModel] = YoutubeVideoSearchAndDetailsToolInput
    api_key: str = Field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY"))

    def fetch_video_details_sync(self, video_id: str) -> VideoDetails:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {"part": "statistics,snippet", "id": video_id, "key": self.api_key}
        response = requests.get(url, params=params)
        response.raise_for_status()
        # now get the details
        item = response.json().get("items", [])[0]
        title = item["snippet"]["title"]
        view_count = int(item["statistics"]["viewCount"])
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        return VideoDetails(title=title, url=video_url, view_count=view_count)

    def _run(self, keyword: str, max_results: int = 3) -> str:
        try:
            # Search for videos
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                "part": "id,snippet",
                "q": keyword,
                "maxResults": max_results,
                "type": "video",
                "key": self.api_key,
            }

            search_response = requests.get(search_url, params=search_params)
            search_response.raise_for_status()
            search_data = search_response.json()
            items = search_data.get("items", [])

            # Get details for each video found

            video_details = [
                self.fetch_video_details_sync(item["id"]["videoId"]) for item in items
            ]

            # Convert results to list of dicts for return
            return [video.model_dump() for video in video_details]

        except requests.exceptions.RequestException as e:
            return f"An HTTP error occurred: {str(e)}"
        except Exception as e:
            return f"An error occurred: {str(e)}"
