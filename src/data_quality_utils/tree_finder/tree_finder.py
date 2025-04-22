import glob
import json
import logging
import os
import shutil
import sys
import warnings
from contextlib import contextmanager

import cv2
import kagglehub
import numpy as np
from deepforest import main

from data_quality_utils.map_extractor.map_utils import (
    BaseMetadata,
    GoogleStaticMetadata,
    GoogleTilesMetadata,
    WMSMetadata,
)

from .distance_utils import calculate_distances, get_coordinate_point

# silence some deepforest warnings
warnings.filterwarnings(
    "ignore", message=".*root_dir argument for the location of images.*"
)
warnings.filterwarnings(
    "ignore",
    message=".*An image was passed directly to predict_tile, the results.root_dir attribute will be None in the output dataframe, to use visualize.plot_results, please assign results.root_dir*",
)

logger = logging.getLogger(__name__)
MODEL_INFERENCE = {"patch_size": 5000, "patch_overlap": 0.9, "iou_threshold": 1}


@contextmanager
def suppress_output():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = devnull
            sys.stderr = devnull
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


class TreeFinder:
    """
    A TreeFinder class which can process an image to detect
    all visible trees, find the closest tree to a point
    and plot some statistics.
    """

    def __init__(self):
        checkpoint_path = self._download_model_checkpoint()
        self.model = main.deepforest.load_from_checkpoint(
            checkpoint_path=checkpoint_path
        )

    def _download_model_checkpoint(self) -> str:
        """Download and return the model checkpoint path."""
        destination_path = "model_checkpoint.ckpt"

        if os.path.exists(destination_path):
            logging.info(
                f"Model checkpoint already exists at {destination_path}, skipping download."
            )
            return destination_path

        download_path = kagglehub.dataset_download(
            "easzil/dataset", path="model.opendata_luftbild_dop60.patch400.ckpt"
        )
        shutil.copyfile(download_path, destination_path)
        logging.info(f"Downloaded model checkpoint to {destination_path}")
        return destination_path

    def _predict_boxes(self, image: np.ndarray) -> list[dict[str, float]]:
        """Run the model on the image and return predicted bounding boxes."""
        with suppress_output():
            pred_boxes = self.model.predict_tile(
                image=image, return_plot=False, **MODEL_INFERENCE
            )
        # convert to list of dicts
        pred_boxes = pred_boxes[["xmin", "ymin", "xmax", "ymax"]].to_dict(
            orient="records"
        )
        return pred_boxes

    def _get_image_metadata(self, filename: str) -> BaseMetadata | None:
        """Load and return metadata as a structured dataclass."""
        metadata_filename = filename.replace(".png", ".json")
        if not os.path.exists(metadata_filename):
            return None

        with open(metadata_filename) as f:
            metadata_dict = json.load(f)

        metadata_type = metadata_dict.get("type")
        if metadata_type == "static":
            return GoogleStaticMetadata(**metadata_dict)
        elif metadata_type == "tiles":
            return GoogleTilesMetadata(**metadata_dict)
        elif metadata_type == "wms":
            return WMSMetadata(**metadata_dict)
        else:
            raise ValueError(f"Unsupported metadata type: {metadata_type}")

    def find_all_trees(self, filename: str) -> list[dict[str, float]]:
        """
        Detects all trees in an image and returns bounding boxes.

        :param filename: Path to the image file.
        :return: A list of predicted bounding boxes as dictionaries.
        """
        image = cv2.imread(filename)
        pred_boxes = self._predict_boxes(image)
        return pred_boxes

    def find_closest_tree(
        self,
        filename: str,
        convert_coords: bool = False,
        flag_threshold: float = 10,
    ) -> tuple[float, bool, dict[str, float], tuple[int, int]] | None:
        """
        Finds the tree closest to the GPS coordinate in the image metadata.

        :param filename: Path to the image file.
        :param convert_coords: Whether to convert coordinates from pseudo Mercator.
        :param flag_threshold: Distance threshold for flagging trees.
        :return: Tuple of (distance in meters, flagged boolean, closest box, coordinate point).
        """
        image = cv2.imread(filename)
        metadata = self._get_image_metadata(filename)
        if metadata is None:
            raise FileNotFoundError("Metadata file not found")

        lat = metadata.lat
        lon = metadata.lon
        zoom = getattr(metadata, "zoom", None)
        scale = getattr(metadata, "scale", 1)
        bbox = getattr(metadata, "bbox", None)
        img_size = image.shape[:2]

        pred_boxes = self._predict_boxes(image)

        distances = calculate_distances(
            lat,
            lon,
            img_size[0],
            img_size[1],
            pred_boxes,
            convert_coords,
            bbox,
            zoom,
            scale,
        )
        distances.sort(key=lambda x: x[1])

        point = get_coordinate_point(lat, lon, bbox, img_size, convert_coords)

        best_box = distances[0][2]
        best_dist = distances[0][1]
        flagged = best_dist >= flag_threshold

        return best_dist, flagged, best_box, point

    def get_stats(self, paths: list[str], types: list[str]) -> dict[str, list[float]]:
        """Compute distance statistics for tree predictions across multiple image sets."""
        stats = {}
        for path, type in zip(paths, types):
            type_stats = []
            convert_coords = type == "static"

            filenames = glob.glob(f"{path}/*.png")
            for filename in filenames:
                image = cv2.imread(filename)
                pred_boxes = self._predict_boxes(image)

                metadata = self._get_image_metadata(filename)
                if not metadata:
                    logger.error(f"No metadata found for image {filename}")
                    continue

                lat = metadata.lat
                lon = metadata.lon
                zoom = getattr(metadata, "zoom", None)
                scale = getattr(metadata, "scale", 1)
                bbox = getattr(metadata, "bbox", None)
                img_size = image.shape[:2]

                distances = calculate_distances(
                    lat,
                    lon,
                    img_size[0],
                    img_size[1],
                    pred_boxes,
                    convert_coords,
                    bbox,
                    zoom,
                    scale,
                )
                distances.sort(key=lambda x: x[1])

                best_dist = distances[0][1]
                type_stats.append(best_dist)

            stats[type] = type_stats
        return stats
