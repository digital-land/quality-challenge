import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Tuple

logger = logging.getLogger(__name__)


class MapExtractor(ABC):
    """Abstract base class for all map image extractors."""

    @abstractmethod
    def download_image(
        self,
        lat: float,
        lon: float,
        img_size: Tuple[int, int],
        filename: str,
        *args,
        **kwargs,
    ) -> None:
        """
        Download a map image and save it with metadata.
        :param lat: Latitude of the desired location
        :param lon: Longitude of the desired location
        :param img_size: Tuple representing width and height in pixels
        :param filename: Path to save the downloaded image
        :return: None
        """
        pass

    def save_metadata(self, filename: str, metadata: dict) -> None:
        """
        Save the metadata to a JSON file.
        :param filename: Path to save the metadata
        :param metadata: Metadata dictionary to be saved
        :return: None
        """
        meta_filename = filename.replace(".png", ".json")
        os.makedirs(os.path.dirname(meta_filename), exist_ok=True)
        with open(meta_filename, "w") as f_meta:
            json.dump(metadata, f_meta)
            logger.info(f"Saved metadata at {meta_filename}")
