import glob
import json
import logging
import math
import os
import shutil
import sys
import warnings
from contextlib import contextmanager

import cv2
import kagglehub
import numpy as np
from deepforest import main
from matplotlib import pyplot as plt

from .distance_utils import calculate_distances
from .plotting_utils import generate_image

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

    def _get_image_metadata(self, filename: str) -> dict | None:
        """Load and return metadata for an image."""
        metadada_filename = filename.replace(".png", ".json")
        if not os.path.exists(metadada_filename):
            return
        with open(metadada_filename) as f:
            metadata = json.load(f)
        return metadata

    def find_all_trees(self, filename: str) -> np.ndarray:
        """
        Detects all trees in an image and overlays bounding boxes.
        :param filename: Path to the image file.
        :return: Image with tree bounding boxes overlaid.
        """
        image = cv2.imread(filename)
        pred_boxes = self._predict_boxes(image)
        result_image = generate_image(image, pred_boxes)
        return result_image

    def find_closest_tree(
        self,
        filename: str,
        convert_coords: bool = False,
        flag_threshold: float = 10,
    ) -> tuple[float, bool, np.ndarray] | None:
        """
        Finds the tree closest to the GPS coordinate in the image metadata.
        :param filename: Path to the image file.
        :param convert_coords: Whether to convert coordinates from pseudo Mercator.
        :param flag_threshold: Distance threshold for flagging trees.
        :return: Tuple of (distance in meters, flagged boolean, overlayed image).
        """
        image = cv2.imread(filename)
        image_copy = image.copy()
        pred_boxes = self._predict_boxes(image)

        metadata = self._get_image_metadata(filename)
        if not metadata:
            logger.error(f"No metadata found for image {filename}")
            return
        lat = metadata.get("lat")
        lon = metadata.get("lon")
        bbox = metadata.get("bbox", "")
        zoom = metadata.get("zoom", "")
        scale = metadata.get("scale", 1)
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

        best_box = distances[0][2]
        best_dist = distances[0][1]
        flagged = best_dist >= flag_threshold
        if convert_coords:
            x_pixel = img_size[0] // 2
            y_pixel = img_size[1] // 2
        else:
            x_pixel, y_pixel = TreeFinder.epsg4326_to_pixel(lat, lon, bbox, img_size)

        result_image = generate_image(image_copy, best_box, (x_pixel, y_pixel))
        return best_dist, flagged, result_image

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
                lat = metadata.get("lat")
                lon = metadata.get("lon")
                bbox = metadata.get("bbox", "")
                zoom = metadata.get("zoom", "")
                scale = metadata.get("scale", 1)
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
