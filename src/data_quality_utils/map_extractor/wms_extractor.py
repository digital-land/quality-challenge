import logging
import os
from dataclasses import asdict

from owslib.wms import WebMapService

from .map_extractor import MapExtractor
from .map_utils import WMSMetadata

logger = logging.getLogger(__name__)


class WMSExtractor(MapExtractor):
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
        img_size: tuple[int, int] = (500, 500),
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
        metadata = WMSMetadata(
            lat=lat,
            lon=lon,
            bbox=bbox,
            img_size=img_size,
        )
        self.save_metadata(filename, asdict(metadata))
