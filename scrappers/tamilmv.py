#!/usr/bin/env python3

import argparse
import asyncio
import logging
import math
import random
import re

from bs4 import BeautifulSoup
from dateutil.parser import parse as dateparser
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

from db import database
from scrappers.helpers import (
    get_page_content,
    get_scrapper_session,
    download_and_save_torrent,
)

HOMEPAGE = "https://www.1tamilmv.prof"
TAMIL_MV_LINKS = {
    "tamil": {
        "hdrip": [
            "11-web-hd-itunes-hd-bluray",
            "12-hd-rips-dvd-rips-br-rips",
            "14-hdtv-sdtv-hdtv-rips",
        ],
        "tcrip": "10-predvd-dvdscr-cam-tc",
        "dubbed": "17-hollywood-movies-in-multi-audios",
        "series": "19-web-series-tv-shows",
    },
    "malayalam": {
        "hdrip": [
            "36-web-hd-itunes-hd-bluray",
            "37-hd-rips-dvd-rips-br-rips",
            "39-hdtv-sdtv-hdtv-rips",
        ],
        "tcrip": "35-predvd-dvdscr-cam-tc",
        "dubbed": "42-malayalam-dubbed-subtitled-movies",
        "series": "44-web-series-tv-shows",
    },
    "telugu": {
        "tcrip": "23-predvd-dvdscr-cam-tc",
        "hdrip": [
            "24-web-hd-itunes-hd-bluray",
            "25-hd-rips-dvd-rips-br-rips",
            "27-hdtv-sdtv-hdtv-rips",
        ],
        "dubbed": "31-telugu-dubbed-movies",
        "series": "33-web-series-tv-shows",
    },
    "hindi": {
        "tcrip": "57-predvd-dvdscr-cam-tc",
        "hdrip": [
            "58-web-hd-itunes-hd-bluray",
            "59-hd-rips-dvd-rips-br-rips",
            "61-hdtv-sdtv-hdtv-rips",
        ],
        "dubbed": "64-hindi-dubbed-movies",
        "series": "66-web-series-tv-shows",
    },
    "kannada": {
        "tcrip": "68-predvd-dvdscr-cam-tc",
        "hdrip": [
            "69-web-hd-itunes-hd-bluray",
            "70-hd-rips-dvd-rips-br-rips",
            "72-hdtv-sdtv-hdtv-rips",
        ],
        "dubbed": "75-watch-kannada-movies-online",
        "series": "77-web-series-tv-shows",
    },
    "english": {
        "tcrip": "46-predvd-dvdscr-cam-tc",
        "hdrip": ["49-web-hd-itunes-hd-bluray", "50-hd-rips-dvd-rips-br-rips"],
        "series": "55-web-series-tv-shows",
    },
}


async def process_movie(
    movie,
    scraper=None,
    page=None,
    keyword=None,
    language=None,
    media_type=None,
    supported_forums=None,
):
    if keyword:
        movie_link = movie.find("a", {"data-linktype": "link"})
        forum_link = movie.find("a", href=re.compile(r"forums/forum/")).get("href")
        forum_id = re.search(r"forums/forum/([^/]+)/", forum_link)[1]
        if forum_id not in supported_forums:
            logging.error(f"Unsupported forum {forum_id}")
            return
        # Extracting language and media_type from supported_forums
        language = supported_forums[forum_id]["language"]
        media_type = supported_forums[forum_id]["media_type"]
    else:
        movie_link = movie.find("a")

    if not movie_link:
        logging.error(f"Movie link not found")
        return

    page_link = movie_link.get("href")

    try:
        if scraper:  # If using the scraper
            response = scraper.get(page_link)
            movie_page_content = response.content
        else:  # If using playwright
            movie_page_content = await get_page_content(page, page_link)

        movie_page = BeautifulSoup(movie_page_content, "html.parser")

        # Extracting other details
        poster_element = movie_page.select_one("div[data-commenttype='forums'] img")
        poster = poster_element.get("src") if poster_element else None

        datetime_element = movie_page.select_one("time")
        created_at = (
            dateparser(datetime_element.get("datetime")) if datetime_element else None
        )

        # Define metadata
        metadata = {
            "catalog": f"{language}_{media_type}",
            "poster": poster,
            "created_at": created_at,
            "scrap_language": language.title(),
            "source": "TamilMV",
        }

        # Extracting torrent details
        torrent_elements = movie_page.select("a[data-fileext='torrent']")

        if not torrent_elements:
            logging.error(f"No torrents found for {page_link}")
            return

        for torrent_element in torrent_elements:
            await download_and_save_torrent(
                torrent_element,
                scraper=scraper,
                page=page,
                metadata=metadata.copy(),
                media_type=media_type,
                page_link=page_link,
            )

        return True
    except Exception as e:
        logging.error(
            f"Error processing movie {page_link}: {e}", exc_info=True, stack_info=True
        )
        return False


async def scrap_page(url, language, media_type, proxy_url=None):
    scraper = get_scrapper_session(proxy_url)
    response = scraper.get(url)
    if response.status_code == 403:
        logging.error(
            "Cloudflare validation required. Run with --scrap-with-playwright"
        )
        return

    response.raise_for_status()
    tamil_blasters = BeautifulSoup(response.content, "html.parser")
    movies = tamil_blasters.select("li[data-rowid]")

    for movie in movies:
        await process_movie(
            movie, scraper=scraper, language=language, media_type=media_type
        )


async def scrap_page_with_playwright(url, language, media_type, proxy_url=None):
    async with async_playwright() as p:
        # Launch a new browser session
        browser = await p.firefox.launch(
            headless=False,
            proxy={"server": proxy_url} if proxy_url else None,
        )
        page = await browser.new_page()
        await stealth_async(page)
        await asyncio.sleep(2)

        page_content = await get_page_content(page, url)
        tamil_blasters = BeautifulSoup(page_content, "html.parser")

        movies = tamil_blasters.select("li[data-rowid]")

        for movie in movies:
            await process_movie(
                movie, page=page, language=language, media_type=media_type
            )

        await browser.close()


async def get_search_results(scraper, keyword, page_number=1):
    search_link = f"{HOMEPAGE}/index.php?/search/&q={keyword}&type=forums_topic&page={page_number}&search_and_or=or&search_in=titles&sortby=relevancy"
    # Get page content and initialize BeautifulSoup
    response = scraper.get(search_link)
    response.raise_for_status()
    page_content = response.content
    soup = BeautifulSoup(page_content, "html.parser")

    return soup


async def scrap_search_keyword(keyword, proxy_url=None):
    supported_forums = {}
    for language in TAMIL_MV_LINKS:
        for video_type in TAMIL_MV_LINKS[language]:
            forum_ids = TAMIL_MV_LINKS[language][video_type]
            if isinstance(forum_ids, list):
                for forum_id in forum_ids:
                    supported_forums[forum_id] = {
                        "language": language,
                        "media_type": video_type,
                    }
            else:
                supported_forums[forum_ids] = {
                    "language": language,
                    "media_type": video_type,
                }

    scraper = get_scrapper_session(proxy_url)
    soup = await get_search_results(scraper, keyword)
    results_element = soup.find("div", {"data-role": "resultsArea"})

    results_count = int(re.search(r"\d+", results_element.find("p").text).group())
    logging.info(f"Found {results_count} results for {keyword}")

    movies = results_element.select("li[data-role='activityItem']")
    if results_count > 25:
        number_of_pages = math.ceil(results_count / 25)
        logging.info(f"Found {number_of_pages} pages for {keyword}")
        for page_number in range(2, number_of_pages + 1):
            soup = await get_search_results(scraper, keyword, page_number)
            movies.extend(soup.select("li[data-role='activityItem']"))
            await asyncio.sleep(random.randint(2, 5))

    for movie in movies:
        await process_movie(
            movie, scraper=scraper, keyword=keyword, supported_forums=supported_forums
        )


async def run_scraper(
    language: str = None,
    video_type: str = None,
    pages: int = None,
    start_page: int = None,
    search_keyword: str = None,
    scrap_with_playwright: bool = None,
    proxy_url: str = None,
):
    await database.init()
    if search_keyword:
        await scrap_search_keyword(search_keyword, proxy_url)
        return
    link_prefix = f"{HOMEPAGE}/index.php?/forums/forum/"
    try:
        forum_ids = TAMIL_MV_LINKS[language][video_type]
        scrap_links = (
            [link_prefix + link for link in forum_ids]
            if isinstance(forum_ids, list)
            else [link_prefix + forum_ids]
        )
    except KeyError:
        logging.error(f"Unsupported language or video type: {language}_{video_type}")
        return
    for scrap_link_prefix in scrap_links:
        for page in range(start_page, pages + start_page):
            scrap_link = f"{scrap_link_prefix}/page/{page}/"
            logging.info(f"Scrap page: {scrap_link}")
            if scrap_with_playwright is True:
                await scrap_page_with_playwright(
                    scrap_link, language, video_type, proxy_url
                )
            else:
                await scrap_page(scrap_link, language, video_type, proxy_url)

    logging.info(f"Scrap completed for : {language}_{video_type}")


async def run_schedule_scrape(
    pages: int = 1,
    start_page: int = 1,
    scrap_with_playwright: bool = None,
    proxy_url: str = None,
):
    for language in TAMIL_MV_LINKS:
        for video_type in TAMIL_MV_LINKS[language]:
            await run_scraper(
                language,
                video_type,
                pages=pages,
                start_page=start_page,
                scrap_with_playwright=scrap_with_playwright,
                proxy_url=proxy_url,
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrap Movie metadata from TamilMV")
    parser.add_argument(
        "--all", action="store_true", help="scrap all type of movies & series"
    )
    parser.add_argument(
        "-l",
        "--language",
        help="scrap movie language",
        default="tamil",
        choices=["tamil", "malayalam", "telugu", "hindi", "kannada", "english"],
    )
    parser.add_argument(
        "-t",
        "--video-type",
        help="scrap movie video type",
        default="hdrip",
        choices=["hdrip", "tcrip", "dubbed", "series"],
    )
    parser.add_argument(
        "-p", "--pages", type=int, default=1, help="number of scrap pages"
    )
    parser.add_argument(
        "-s", "--start-pages", type=int, default=1, help="page number to start scrap."
    )
    parser.add_argument(
        "-k",
        "--search-keyword",
        help="search keyword to scrap movies & series. ex: 'bigg boss'",
        default=None,
    )
    parser.add_argument(
        "--scrap-with-playwright", action="store_true", help="scrap with playwright"
    )
    parser.add_argument(
        "--proxy-url",
        help="proxy url to scrap. ex: socks5://127.0.0.1:1080",
        default=None,
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(levelname)s::%(asctime)s - %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
        level=logging.INFO,
    )
    if args.all:
        asyncio.run(
            run_schedule_scrape(
                args.pages, args.start_pages, args.scrap_with_playwright, args.proxy_url
            )
        )
    else:
        asyncio.run(
            run_scraper(
                args.language,
                args.video_type,
                args.pages,
                args.start_pages,
                args.search_keyword,
                args.scrap_with_playwright,
                args.proxy_url,
            )
        )
