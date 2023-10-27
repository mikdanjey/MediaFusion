from datetime import datetime
from typing import Optional

import pymongo
from beanie import Document, Link
from pydantic import BaseModel, Field
from pymongo import IndexModel, ASCENDING


class Episode(BaseModel):
    episode_number
    filename
    size
    file_index


class Season(BaseModel):
    season_number
    episodes: list[Episode]


class Streams(Document):
    id
    torrent_name
    size
    season: Optional[Season] = None
    filename: Optional[str] = None
    file_index: Optional[int] = None
    announce_list: list[str]
    languages: list[str]
    source
    catalog: list[str]
    created_at: datetime = Field(default_factory=datetime.now)
    resolution: Optional[str]
    codec: Optional[str]
    quality: Optional[str]
    audio: Optional[str]
    encoder: Optional[str]
    seeders: Optional[int] = None
    cached: Optional[bool] = None

    def get_episode(self, season_number, episode_number):
        """
        Returns the Episode object for the given season and episode number.
        """
        if self.season and self.season.season_number == season_number:
            for episode in self.season.episodes:
                if episode.episode_number == episode_number:
                    return episode
        return None


class MediaFusionMetaData(Document):
    id
    title
    year: Optional[int]
    poster
    background
    streams: list[Link[Streams]]
    type

    class Settings:
        is_root = True
        indexes = [
            IndexModel([("title", ASCENDING), ("year", ASCENDING)], unique=True),
            IndexModel([("title", pymongo.TEXT)]),
        ]


class MediaFusionMovieMetaData(MediaFusionMetaData):
    type = "movie"


class MediaFusionSeriesMetaData(MediaFusionMetaData):
    type = "series"
