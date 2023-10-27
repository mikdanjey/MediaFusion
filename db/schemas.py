from typing import Optional, Any, Literal

from pydantic import BaseModel, Field

from utils.const import CATALOG_ID_DATA


class Catalog(BaseModel):
    id: str
    name: str
    type: str


class Meta(BaseModel):
    id: str = Field(alias="_id")
    name: str = Field(alias="title")
    type: str = Field(default="movie")
    poster: str
    background: str
    videos: list = None


class MetaItem(BaseModel):
    meta: Meta


class Metas(BaseModel):
    metas: list[Meta] = []


class Stream(BaseModel):
    name: str
    description: str
    infoHash: str = None
    fileIdx: int = None
    url: str = None
    behaviorHints: dict[str, Any] = None


class Streams(BaseModel):
    streams: Optional[list[Stream]] = []


class StreamingProvider(BaseModel):
    service: Literal["realdebrid", "seedr", "debridlink"]
    token: str

    class Config:
        extra = "ignore"


class UserData(BaseModel):
    streaming_provider: StreamingProvider = None
    selected_catalogs: list[str] = Field(default=CATALOG_ID_DATA)

    class Config:
        extra = "ignore"


class AuthorizeData(BaseModel):
    device_code: str


class MetaIdProjection(BaseModel):
    id: str = Field(alias="_id")
