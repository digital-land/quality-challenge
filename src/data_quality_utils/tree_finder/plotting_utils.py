import math
import os

import cv2
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.figure import Figure

COLOR = "#00625E"


def _generate_boxes(
    image: np.ndarray, pred_boxes: list[dict[str, float]] | dict[str, float]
) -> None:
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


def _generate_point(image: np.ndarray, point: tuple[int, int]) -> None:
    """Draw a point on the image."""
    radius = max(5, (image.shape[0] // 500) * 5)
    cv2.circle(image, point, radius=radius, color=(0, 0, 255), thickness=-1)


def generate_image(
    image: np.ndarray,
    pred_boxes: list[dict[str, float]] | dict[str, float],
    point: tuple[int, int] | None = None,
) -> np.ndarray:
    """Overlay bounding boxes and optional point on the image."""
    image_copy = image.copy()
    _generate_boxes(image_copy, pred_boxes)
    if point:
        _generate_point(image_copy, point)
    return image_copy


def _show_single(image: np.ndarray, image_title: str | None) -> Figure:
    """Display a single image"""
    fig, ax = plt.subplots(1, 1, figsize=(5, 5))
    ax.imshow(image)
    if image_title:
        ax.set_title(image_title)
    ax.axis("off")
    return fig


def _show_multiple(
    image_list: list[np.ndarray], image_title_list: list[str] | None
) -> Figure:
    """Display multiple images side by side."""
    num_images = len(image_list)
    if image_title_list is None:
        image_title_list = []
    fig, axes = plt.subplots(1, num_images, figsize=(5 * num_images, 5))
    for ax, image, title in zip(axes, image_list, image_title_list):
        ax.imshow(image)
        if title:
            ax.set_title(title)
        ax.axis("off")
    return fig


def show_image(
    images: np.ndarray | list[np.ndarray],
    image_titles: str | list[str] | None = None,
    save_path: str | None = None,
) -> None:
    """Show one or more images."""
    if isinstance(images, list):
        fig = _show_multiple(images, image_titles)
    else:
        fig = _show_single(images, image_titles)
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()


def show_stats(stats_dict: dict[str, list[float]]) -> None:
    """Plot histograms of tree detection distances for each image type."""
    max_distance = math.ceil(max(max(type_stats) for type_stats in stats_dict.values()))
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
