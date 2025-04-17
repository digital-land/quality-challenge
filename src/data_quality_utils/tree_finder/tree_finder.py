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
from geopy.distance import geodesic
from matplotlib import pyplot as plt

# silence some deepforest warnings
warnings.filterwarnings(
    "ignore", message=".*root_dir argument for the location of images.*"
)
warnings.filterwarnings(
    "ignore",
    message=".*An image was passed directly to predict_tile, the results.root_dir attribute will be None in the output dataframe, to use visualize.plot_results, please assign results.root_dir*",
)

logger = logging.getLogger(__name__)
TILE_SIZE = 256
MODEL_INFERENCE = {"patch_size": 5000, "patch_overlap": 0.9, "iou_threshold": 1}
COLOR = "#00625E"


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

    def _download_model_checkpoint(self):
        """Download and return the model checkpoint path."""
        download_path = kagglehub.dataset_download(
            "easzil/dataset", path="model.opendata_luftbild_dop60.patch400.ckpt"
        )
        destination_path = "model_checkpoint.ckpt"
        shutil.copyfile(download_path, destination_path)
        logging.info(f"Downloaded model checkpoint to {destination_path}")
        return destination_path

    def _predict_boxes(self, image):
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

    def _calculate_distances(
        self,
        lat,
        lon,
        img_width,
        img_height,
        pred_boxes,
        convert_coords,
        bbox=None,
        zoom=None,
        scale=None,
    ):
        """Calculate distances from predicted tree boxes to a given geographic location."""
        distances = []
        for box in pred_boxes:
            x_center = (box["xmin"] + box["xmax"]) / 2
            y_center = (box["ymin"] + box["ymax"]) / 2

            if convert_coords:
                center_px, center_py = TreeFinder.epsg3857_to_pixel(
                    lat, lon, zoom, scale
                )
                abs_px = center_px - (img_width / 2) + x_center
                abs_py = center_py - (img_height / 2) + y_center
                pred_lat, pred_lon = TreeFinder.pixel_to_epsg3857(
                    abs_px, abs_py, zoom, scale
                )
            else:
                pred_lon, pred_lat = TreeFinder.pixel_to_epsg4326(
                    x_center, y_center, img_width, img_height, bbox
                )

            box_dist = geodesic((pred_lat, pred_lon), (lat, lon)).meters
            distances.append(((pred_lat, pred_lon), box_dist, box))
        return distances

    def _generate_boxes(self, image, pred_boxes):
        """Draw bounding boxes on the image."""
        thickness = max(1, image.shape[0] // 500)
        if isinstance(pred_boxes, dict):
            pred_boxes = [pred_boxes]
        for box in pred_boxes:
            cv2.rectangle(
                image,
                (int(box["xmin"]), int(box["ymin"])),
                (int(box["xmax"]), int(box["ymax"])),
                (255, 165, 0),
                thickness=thickness,
                lineType=cv2.LINE_AA,
            )

    def _generate_point(self, image, point):
        """Draw a point on the image."""
        radius = max(5, (image.shape[0] // 500) * 5)
        cv2.circle(image, point, radius=radius, color=(0, 0, 255), thickness=-1)

    def _generate_image(self, image, pred_boxes, point=None):
        """Overlay bounding boxes and optional point on the image."""
        image_copy = image.copy()
        self._generate_boxes(image_copy, pred_boxes)
        if point:
            self._generate_point(image_copy, point)
        return image_copy

    def _get_image_metadata(self, filename):
        """Load and return metadata for an image."""
        metadada_filename = filename.replace(".png", ".json")
        if not os.path.exists(metadada_filename):
            return
        with open(metadada_filename) as f:
            metadata = json.load(f)
        return metadata

    def find_all_trees(self, filename):
        """
        Detects all trees in an image and overlays bounding boxes.
        :param filename: Path to the image file.
        :return: Image with tree bounding boxes overlaid.
        """
        image = cv2.imread(filename)
        pred_boxes = self._predict_boxes(image)
        result_image = self._generate_image(image, pred_boxes)
        return result_image

    def find_closest_tree(
        self,
        filename,
        convert_coords=False,
        flag_threshold=10,
    ):
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

        distances = self._calculate_distances(
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

        result_image = self._generate_image(image_copy, best_box, (x_pixel, y_pixel))
        return best_dist, flagged, result_image

    def _show_single(self, image, image_title=None):
        """Display a single image"""
        fig, ax = plt.subplots(1, 1, figsize=(5, 5))
        ax.imshow(image)
        ax.set_title(image_title)
        ax.axis("off")
        return fig

    def _show_multiple(self, image_list, image_title_list:None):
        """Display multiple images side by side."""
        num_images = len(image_list)
        fig, axes = plt.subplots(1, num_images, figsize=(5 * num_images, 5))
        for ax, image, title in zip(axes, image_list, image_title_list):
            ax.imshow(image)
            ax.set_title(title)
            ax.axis("off")
        return fig

    def show_image(self, images, image_titles=None, save=False, save_path=None):
        """Show one or more images."""
        if isinstance(images, list):
            fig = self._show_multiple(images, image_titles)
        else:
            fig = self._show_single(images, image_titles)
        if save:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            fig.savefig(save_path, dpi=300, bbox_inches="tight")
        plt.show()

    def get_stats(self, paths, types):
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

                distances = self._calculate_distances(
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

    @staticmethod
    def show_stats(stats_dict):
        """Plot histograms of tree detection distances for each image type."""
        max_distance = math.ceil(
            max(max(type_stats) for type_stats in stats_dict.values())
        )
        num_stats = len(stats_dict)

        bins = list(range(0, max_distance + 1))

        fig, axes = plt.subplots(
            num_stats, 1, sharex=True, figsize=(6, 6), height_ratios=[1, 1]
        )
        fig.subplots_adjust(hspace=0.1)

        for ax, type, type_stats in zip(axes, stats_dict.keys(), stats_dict.values()):
            ax.hist(type_stats, bins=bins, color=COLOR, label=f"{type} image")
            ax.set_title(f"{type} error distribution")
            ax.set_ylabel("Count")
            # ax.legend(loc="best")

        axes[-1].set_xlabel("Distance from true point (meters)")
        axes[-1].set_xticks(bins)

        plt.tight_layout()
        plt.savefig("data/distance_histograms.png", dpi=300, bbox_inches="tight")
        plt.show()

    @staticmethod
    def pixel_to_epsg4326(x, y, img_width, img_height, bbox):
        """Convert image pixel coordinates to EPSG:4326 (lat/lon)."""
        xmin, ymin, xmax, ymax = bbox
        lon = xmin + (x / img_width) * (xmax - xmin)
        lat = ymax - (y / img_height) * (ymax - ymin)
        return lon, lat

    @staticmethod
    def epsg4326_to_pixel(lat, lon, bbox, img_size):
        """Convert EPSG:4326 (lat/lon) to pixel coordinates in an image."""
        xmin, ymin, xmax, ymax = bbox
        width, height = img_size
        x_frac = (lon - xmin) / (xmax - xmin)
        y_frac = 1 - (lat - ymin) / (ymax - ymin)
        x_pixel = int(x_frac * width)
        y_pixel = int(y_frac * height)
        return x_pixel, y_pixel

    @staticmethod
    def epsg3857_to_pixel(lat, lon, zoom, scale):
        """Convert EPSG:3857 coordinates to pixel coordinates."""
        siny = math.sin(math.radians(lat))
        siny = min(max(siny, -0.9999), 0.9999)

        map_size = TILE_SIZE * (2**zoom) * scale
        x = (lon + 180) / 360 * map_size
        y = (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)) * map_size
        return x, y

    @staticmethod
    def pixel_to_epsg3857(x, y, zoom, scale):
        """Convert pixel coordinates to EPSG:3857 (lat/lon)."""
        map_size = TILE_SIZE * (2**zoom) * scale
        lon = x / map_size * 360.0 - 180.0
        n = math.pi - 2.0 * math.pi * y / map_size
        lat = math.degrees(math.atan(math.sinh(n)))
        return lat, lon
