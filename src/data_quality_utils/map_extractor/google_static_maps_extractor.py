import logging
import os
from dataclasses import asdict
from urllib.parse import urlencode

import requests

from .map_extractor import MapExtractor
from .map_utils import GoogleStaticMetadata

logger = logging.getLogger(__name__)


class GoogleStaticMapsExtractor(MapExtractor):
    def __init__(self, google_api_key: str):
        self._google_api_key = google_api_key

    def download_image(
        self,
        lat: float,
        lon: float,
        zoom: int,
        scale: int,
        img_size: tuple[int, int],
        filename: str,
    ) -> None:
        """
        Download a satellite image from Google Static Maps API and save it with metadata.
        :param lat: Latitude of the desired location
        :param lon: Longitude of the desired location
        :param zoom: Zoom level for the map image
        :param scale: Image scale (1 or 2 for normal/high res)
        :param img_size: Tuple representing width and height in pixels
        :param filename: File path to save the downloaded image
        :return: None
        """
        # get image
        static_maps_base_url = "https://maps.googleapis.com/maps/api/staticmap?"
        params = {
            "center": f"{lat},{lon}",
            "zoom": zoom,
            "size": f"{img_size[0]}x{img_size[1]}",
            "maptype": "satellite",
            "scale": scale,
            "key": self._google_api_key,
        }
        query_string = urlencode(params)
        url = f"{static_maps_base_url}{query_string}"
        res = requests.get(url)

        # save image
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f_out:
            f_out.write(res.content)
            logger.info(f"Saved image at {filename}")

        # save metadata
        metadata = GoogleStaticMetadata(
            lat=lat,
            lon=lon,
            zoom=zoom,
            scale=scale,
            img_size=img_size,
        )
        self.save_metadata(filename, asdict(metadata))
