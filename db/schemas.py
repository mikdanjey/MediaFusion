from typing import Optional, Any, Literal

from pydantic import BaseModel, Field

from utils.const import CATALOG_ID_DATA


class Catalog(BaseModel):
    id
    name
    type


class Meta(BaseModel):
    id = Field(alias="_id")
    name = Field(alias="title")
    type = Field(default="movie")
    poster
    background
    videos: list | None = None


class MetaItem(BaseModel):
    meta: Meta


class Metas(BaseModel):
    metas: list[Meta] = []


class Stream(BaseModel):
    name
    description
    infoHash | None = None
    fileIdx | None = None
    url | None = None
    behaviorHints: dict[str, Any] | None = None


class Streams(BaseModel):
    streams: Optional[list[Stream]] = []


class StreamingProvider(BaseModel):
    service: Literal["realdebrid", "seedr", "debridlink"]
    token

    class Config:
        extra = "ignore"


class UserData(BaseModel):
    streaming_provider: StreamingProvider | None = None
    selected_catalogs: list[str] = Field(default=CATALOG_ID_DATA)

    class Config:
        extra = "ignore"


class AuthorizeData(BaseModel):
    device_code


class MetaIdProjection(BaseModel):
    id = Field(alias="_id")
