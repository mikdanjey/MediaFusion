import logging
from typing import Optional
from uuid import uuid4

from beanie import WriteRules
from beanie.operators import In

from db import schemas
from db.config import settings
from db.models import (
    MediaFusionMovieMetaData,
    MediaFusionSeriesMetaData,
    Streams,
    Season,
    Episode,
)
from db.schemas import Stream, MetaIdProjection
from utils.parser import parse_stream_data, get_catalogs, search_imdb


async def get_meta_list(
    catalog_type, catalog, skip = 0, limit = 25
) :
    if catalog_type == "movie":
        meta_class = MediaFusionMovieMetaData
    else:
        meta_class = MediaFusionSeriesMetaData

    meta_list = (
        await meta_class.find(
            In(meta_class.streams.catalog, [catalog]),
            fetch_links=True,
        )
        .sort(-meta_class.streams.created_at)
        .skip(skip)
        .limit(limit)
        .project(schemas.Meta)
        .to_list()
    )
    for meta in meta_list:
        meta.poster = f"{settings.host_url}/poster/{catalog_type}/{meta.id}.jpg"

    return meta_list


async def get_movie_data_by_id(
    movie_id, fetch_links: bool = False
):
    movie_data = await MediaFusionMovieMetaData.get(movie_id, fetch_links=fetch_links)
    return movie_data


async def get_series_data_by_id(
    series_id, fetch_links: bool = False
):
    series_data = await MediaFusionSeriesMetaData.get(
        series_id, fetch_links=fetch_links
    )
    return series_data


async def get_movie_streams(user_data, secret_str, video_id):
    movie_data = await get_movie_data_by_id(video_id, True)
    if not movie_data:
        return []

    return parse_stream_data(movie_data.streams, user_data, secret_str)


async def get_series_streams(
    user_data, secret_str, video_id, season, episode
):
    series_data = await get_series_data_by_id(video_id, True)
    if not series_data:
        return []

    matched_episode_streams = [
        stream for stream in series_data.streams if stream.get_episode(season, episode)
    ]

    return parse_stream_data(
        matched_episode_streams, user_data, secret_str, season, episode
    )


async def get_movie_meta(meta_id):
    movie_data = await get_movie_data_by_id(meta_id)

    if not movie_data:
        return {}

    return {
        "meta": {
            "_id": meta_id,
            "type": "movie",
            "title": movie_data.title,
            "poster": f"{settings.host_url}/poster/movie/{meta_id}.jpg",
            "background": movie_data.poster,
        }
    }


async def get_series_meta(meta_id):
    series_data = await get_series_data_by_id(meta_id, True)

    if not series_data:
        return {}

    metadata = {
        "meta": {
            "_id": meta_id,
            "type": "series",
            "title": series_data.title,
            "poster": f"{settings.host_url}/poster/series/{meta_id}.jpg",
            "background": series_data.poster,
            "videos": [],
        }
    }

    # Loop through streams to populate the videos list
    for stream in series_data.streams:
        stream
        if stream.season:  # Ensure the stream has season data
            for episode in stream.season.episodes:
                metadata["meta"]["videos"].append(
                    {
                        "id": f"{meta_id}:{stream.season.season_number}:{episode.episode_number}",
                        "name": f"S{stream.season.season_number} EP{episode.episode_number}",
                        "season": stream.season.season_number,
                        "episode": episode.episode_number,
                        "released": stream.created_at,
                    }
                )

    return metadata


async def save_movie_metadata(metadata: dict):
    # Try to get the existing movie
    existing_movie = await MediaFusionMovieMetaData.find_one(
        {"title": metadata["title"], "year": metadata.get("year")}
    )

    if not existing_movie:
        # If the movie doesn't exist in our DB, search for IMDb ID
        imdb_data = search_imdb(metadata["title"], metadata.get("year"))
        meta_id = imdb_data.get("imdb_id")

        if meta_id:
            # Check if the movie with the found IMDb ID already exists in our DB
            existing_movie = await MediaFusionMovieMetaData.get(meta_id)
        else:
            meta_id = f"mf{uuid4().fields[-1]}"
        # Update the poster from IMDb if available
        poster = imdb_data.get("poster") or metadata["poster"]
        background = imdb_data.get("background") or metadata["poster"]
    else:
        poster = existing_movie.poster
        background = existing_movie.background
        meta_id = existing_movie.id

    # Determine file index for the main movie file (largest file)
    largest_file = max(
        metadata["torrent_metadata"]["file_data"], key=lambda x: x["size"]
    )

    if "language" in metadata:
        languages = (
            [metadata["language"]]
            if isinstance(metadata["language"], str)
            else metadata["language"]
        )
    else:
        languages = [metadata["scrap_language"]]

    # Create the stream object
    new_stream = Streams(
        id=metadata["torrent_metadata"]["info_hash"],
        torrent_name=metadata["torrent_metadata"]["torrent_name"],
        announce_list=metadata["torrent_metadata"]["announce_list"],
        size=metadata["torrent_metadata"]["total_size"],
        filename=largest_file["filename"],
        file_index=largest_file["index"],
        languages=languages,
        resolution=metadata.get("resolution"),
        codec=metadata.get("codec"),
        quality=metadata.get("quality"),
        audio=metadata.get("audio"),
        encoder=metadata.get("encoder"),
        source=metadata["source"],
        catalog=get_catalogs(metadata["catalog"], languages),
        created_at=metadata["created_at"],
    )

    if existing_movie:
        # Check if the stream with the same info_hash already exists
        await existing_movie.fetch_all_links()
        matching_stream = next(
            (stream for stream in existing_movie.streams if stream.id == new_stream.id),
            None,
        )
        if not matching_stream:
            existing_movie.streams.append(new_stream)
        await existing_movie.save(link_rule=WriteRules.WRITE)
        logging.info("Updated movie %s", existing_movie.title)
    else:
        # If the movie doesn't exist, create a new one
        movie_data = MediaFusionMovieMetaData(
            id=meta_id,
            title=metadata["title"],
            year=metadata["year"],
            poster=poster,
            background=background,
            streams=[new_stream],
        )
        await movie_data.insert(link_rule=WriteRules.WRITE)
        logging.info("Added movie %s", movie_data.title)


async def save_series_metadata(metadata: dict):
    # Try to get the existing series
    series = await MediaFusionSeriesMetaData.find_one({"title": metadata["title"]})

    if not series:
        # If the series doesn't exist in our DB, search for IMDb ID
        imdb_data = search_imdb(metadata["title"], metadata["year"])
        meta_id = imdb_data.get("imdb_id")

        if meta_id:
            # Check if the series with the found IMDb ID already exists in our DB
            series = await MediaFusionSeriesMetaData.get(meta_id)

        if not series:
            meta_id = meta_id or f"mf{uuid4().fields[-1]}"
            poster = imdb_data.get("poster") or metadata["poster"]
            background = imdb_data.get("background") or metadata["poster"]

            # Create an initial entry for the series
            series = MediaFusionSeriesMetaData(
                id=meta_id,
                title=metadata["title"],
                year=metadata["year"],
                poster=poster,
                background=background,
                streams=[],
            )
            await series.insert()
            logging.info("Added series %s", series.title)

    await series.fetch_all_links()
    existing_stream = next(
        (
            s
            for s in series.streams
            if s.id == metadata["torrent_metadata"]["info_hash"]
        ),
        None,
    )
    if existing_stream:
        # If the stream already exists, return
        logging.info("Stream already exists for series %s", series.title)
        return

    season_number = metadata["season"]

    # Extract episodes
    episodes = [
        Episode(
            episode_number=file["episode"],
            filename=file["filename"],
            size=file["size"],
            file_index=file["index"],
        )
        for file in metadata["torrent_metadata"]["file_data"]
        if file["episode"]
    ]

    # Determine languages
    if "language" in metadata:
        languages = (
            [metadata["language"]]
            if isinstance(metadata["language"], str)
            else metadata["language"]
        )
    else:
        languages = [metadata["scrap_language"]]

    # Create the stream
    stream = Streams(
        id=metadata["torrent_metadata"]["info_hash"],
        torrent_name=metadata["torrent_metadata"]["torrent_name"],
        announce_list=metadata["torrent_metadata"]["announce_list"],
        size=metadata["torrent_metadata"]["total_size"],
        languages=languages,
        resolution=metadata.get("resolution"),
        codec=metadata.get("codec"),
        quality=metadata.get("quality"),
        audio=metadata.get("audio"),
        encoder=metadata.get("encoder"),
        source=metadata["source"],
        catalog=get_catalogs(metadata["catalog"], languages),
        created_at=metadata["created_at"],
        season=Season(season_number=season_number, episodes=episodes),
    )

    # Add the stream to the series
    series.streams.append(stream)

    await series.save(link_rule=WriteRules.WRITE)
    logging.info("Updated series %s", series.title)


async def process_search_query(search_query, catalog_type):
    if catalog_type == "movie":
        meta_class = MediaFusionMovieMetaData
    else:
        meta_class = MediaFusionSeriesMetaData

    search_results = (
        await meta_class.find({"$text": {"$search": search_query}})
        .project(MetaIdProjection)
        .to_list()
    )

    logging.info(
        "Found %s results for %s in %s", len(search_results), search_query, catalog_type
    )

    metas = []

    for item in search_results:
        # Use the appropriate function to get the meta data
        if catalog_type == "movie":
            meta = await get_movie_meta(item.id)
        else:
            meta = await get_series_meta(item.id)

        if not meta:
            continue

        metas.append(meta["meta"])

    return {"metas": metas}


async def get_stream_by_info_hash(info_hash):
    stream = await Streams.get(info_hash)
    return stream
