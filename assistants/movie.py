import os
import time

import putiopy
import requests

from framework import DeclarativeAssistant

PUTIO_TOKEN = os.environ["PUTIO_TOKEN"]

JACKETT_API_KEY = os.environ["JACKETT_API_KEY"]
JACKETT_DOMAIN = os.environ["JACKETT_DOMAIN"]
JACKETT_URL = f"https://{JACKETT_DOMAIN}/api/v2.0/indexers/all/results?apikey={JACKETT_API_KEY}&Query={{query}}"


client = putiopy.Client(PUTIO_TOKEN)


class MovieAssistant(DeclarativeAssistant):
    """
    # Role
    You are a helpful assistant that helps people to search for videos on the Internet.
    Refuse help if user's intent is not related to watching movies.
    You are allowed to talk about movies, you can give suggestions about movies.
    You have access to almost every major on-demand video streaming platforms legally.
    You have access to the most recent videos, even the ones you don't know yet.

    # Operation
    - Search for a movie using search_movie function.
    - After searching for a video, pick a video to download.
        - Prefer 1080p videos.
        - Prefer h264/x264 codecs.
        - Prefer links with the most seeders.
    - Download the movie using download_movie function. The user cannot download the video directly.
    - After downloading the video, show the video link to the user.
    """

    def search_movie(self, movie: str, year: int):
        """Search for a movie on the Internet.
        Returns a list of dictionaries, each dictionary contains title and link."""
        query = f"{movie} ({year})"
        print(f"Searching for {query}...")
        response = requests.get(JACKETT_URL.format(query=query))
        results = response.json()["Results"]
        results.sort(key=lambda r: r["Seeders"], reverse=True)
        results = results[:10]
        return [{"title": r["Title"], "link": r["MagnetUri"]} for r in results]

    def download_movie(self, url):
        """Download a movie from the Internet.
        Returns a dictionary containing the video link."""
        print(f"Downloading {url}...")
        transfer = client.Transfer.add_url(url)
        seconds_left = 10
        while seconds_left > 0:
            transfer = client.Transfer.get(transfer.id)
            if transfer.status != "COMPLETED":  # type: ignore
                time.sleep(1)
                seconds_left -= 1
                continue

            file = client.File.get(transfer.file_id)  # type: ignore
            if file.content_type == "application/x-directory":  # type: ignore
                file = max(client.File.list(transfer.file_id), key=lambda f: f.size)  # type: ignore

            return {"video_link": f"https://app.put.io/files/{file.id}"}

        return "Timeout while downloading the video."


movie = MovieAssistant()
