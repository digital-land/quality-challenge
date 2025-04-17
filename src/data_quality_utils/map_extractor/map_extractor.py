import json
import logging
import math
import os
from urllib.parse import urlencode

import requests
from owslib.wms import WebMapService

logger = logging.getLogger(__name__)


class GoogleMapTilesExtractor:
    """
    Extracts satellite tiles from Google Maps Tile API using x, y coordinates.

    :param google_api_key: Google Maps API key for authentication
    """

    def __init__(self, google_api_key: str):
        self._google_api_key = google_api_key

    def get_xy_coordinates(self, lon: float, lat: float, zoom: int) -> tuple[int, int]:
        """Convert latitude and longitude to x, y tile coordinates."""
        lat_rad = math.radians(lat)
        n = 2.0**zoom
        xtile = int((lon + 180.0) / 360.0 * n)
        ytile = int(
            (1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi)
            / 2.0
            * n
        )
        return xtile, ytile

    def get_session_token(self) -> str:
        """Request and return a new session token from the Google Maps Tile API."""
        url = f"https://tile.googleapis.com/v1/createSession?key={self._google_api_key}"

        payload = {"mapType": "satellite"}
        headers = {"Content-Type": "application/json"}

        response = requests.post(url, json=payload, headers=headers)
        session_token = response.json().get("session", "")
        return session_token

    def download_image(self, lat: float, lon: float, zoom: int, filename: str) -> None:
        """
        Download a satellite tile image from Google Maps Tile API and save it with metadata.
        :param lat: Latitude of the desired location
        :param lon: Longitude of the desired location
        :param zoom: Zoom level for the tile image
        :param filename: File path to save the downloaded image
        :return: None
        """
        # get image
        x, y = self.get_xy_coordinates(lon, lat, zoom)
        session_token = self.get_session_token()
        if session_token == "":
            logger.error(
                "Couldn't get session token, please check your API key is correct"
            )
            return

        url = f"https://tile.googleapis.com/v1/2dtiles/{zoom}/{x}/{y}?session={session_token}&key={self._google_api_key}"
        res = requests.get(url)

        # save image
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f_out:
            f_out.write(res.content)
            logger.info(f"Saved image at {filename}")

        # save metadata
        metadata = {
            "lat": lat,
            "lon": lon,
            "zoom": zoom,
            "img_size": (256, 256),
            "type": "tiles",
        }
        meta_filename = filename.replace(".png", ".json")
        with open(meta_filename, "w") as f_meta:
            json.dump(metadata, f_meta)


class GoogleStaticMapsExtractor:
    """
    Downloads satellite images from the Google Static Maps API.

    :param google_api_key: Google Maps API key for authentication
    """

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
        img_size = [img_size[0], img_size[1]]
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
        metadata = {
            "lat": lat,
            "lon": lon,
            "zoom": zoom,
            "scale": scale,
            "img_size": img_size,
            "type": "static",
        }
        meta_filename = filename.replace(".png", ".json")
        with open(meta_filename, "w") as f_meta:
            json.dump(metadata, f_meta)


class WMSExtractor:
    """
    Extracts satellite imagery using Web Map Service (WMS) protocols.

    :param wms_url: URL endpoint of the WMS server
    """

    def __init__(self, wms_url: str):
        self.wms = WebMapService(wms_url)

    def get_bbox(
        self, lat: float, lon: float, offset: float
    ) -> tuple[float, float, float, float]:
        """Calculate a bounding box around a coordinate with a given offset."""
        xmin = lon - offset
        ymin = lat - offset
        xmax = lon + offset
        ymax = lat + offset
        return (xmin, ymin, xmax, ymax)

    def download_image(
        self,
        lat: float,
        lon: float,
        offset: float,
        filename: str,
        img_size: tuple[int] = (500, 500),
    ) -> None:
        """
        Download a WMS image around the given coordinates and save it with metadata.
        :param lat: Latitude of the center point
        :param lon: Longitude of the center point
        :param offset: Offset in degrees to calculate bounding box
        :param filename: File path to save the image
        :param img_size: Tuple representing width and height in pixels
        :return: None
        """
        # get image
        bbox = self.get_bbox(lat, lon, offset)
        img = self.wms.getmap(
            layers=["APGB_Latest_UK_125mm"],
            srs="EPSG:4326",
            bbox=bbox,
            size=img_size,
            format="image/png",
        )

        # save image
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, "wb") as f_out:
            f_out.write(img.read())
            logger.info(f"Saved image at {filename}")

        # save metadata
        metadata = {
            "lat": lat,
            "lon": lon,
            "bbox": bbox,
            "img_size": img_size,
            "type": "wms",
        }
        meta_filename = filename.replace(".png", ".json")
        with open(meta_filename, "w") as f_meta:
            json.dump(metadata, f_meta)
