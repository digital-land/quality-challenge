import numpy as np
import pytest

from data_quality_utils.tree_finder import TreeFinder
from data_quality_utils.tree_finder.distance_utils import (
    calculate_distances,
    epsg3857_to_tile,
    epsg4326_to_pixel,
    get_coordinate_point,
    pixel_to_epsg4326,
    tile_to_epsg3857,
)

LAT = 51.607777
LON = -0.570024
IMG_SIZE = (500, 500)
BBOX = [-0.5705239999999999, 51.607276999999996, -0.569524, 51.608277]
ZOOM = 18
SCALE = 2
IMG_WIDTH, IMG_HEIGHT = IMG_SIZE


class MockModel:
    def predict_tile(self, image, return_plot=False, **kwargs):
        import pandas as pd

        return pd.DataFrame(
            [
                {"xmin": 10, "ymin": 20, "xmax": 30, "ymax": 40},
                {"xmin": 50, "ymin": 60, "xmax": 70, "ymax": 80},
            ]
        )


TreeFinder.model = MockModel()


def test_predict_boxes():
    image = np.zeros((500, 500, 3), dtype=np.uint8)
    tree_finder = TreeFinder()
    tree_finder.model = MockModel()  # inject the mock

    boxes = tree_finder._predict_boxes(image)

    assert isinstance(boxes, list)
    assert boxes == [
        {"xmin": 10, "ymin": 20, "xmax": 30, "ymax": 40},
        {"xmin": 50, "ymin": 60, "xmax": 70, "ymax": 80},
    ]


def test_pixel_to_epsg4326():
    x, y = 250, 250

    lon, lat = pixel_to_epsg4326(x, y, *IMG_SIZE, BBOX)

    expected_lon = -0.57
    expected_lat = 51.60
    assert abs(lon - expected_lon) < 0.1
    assert abs(lat - expected_lat) < 0.1


def test_epsg4326_to_pixel():
    x, y = epsg4326_to_pixel(LAT, LON, BBOX, IMG_SIZE)

    expected_x = 250
    expected_y = 250
    assert x == expected_x
    assert y == expected_y


def test_epsg3857_to_tile():
    x, y = epsg3857_to_tile(LAT, LON, ZOOM, SCALE)

    expected_x, expected_y = 66896343.64, 44570627.75
    assert abs(x - expected_x) <= 0.01
    assert abs(y - expected_y) <= 0.01


def test_tile_to_epsg3857():
    x, y = 66896343.64, 44570627.75

    lat, lon = tile_to_epsg3857(x, y, ZOOM, SCALE)

    expected_lat, expected_lon = 51.60, -0.57
    assert abs(lat - expected_lat) <= 0.01
    assert abs(lon - expected_lon) <= 0.01


@pytest.mark.parametrize(
    "convert_coords, pred_boxes, img_width, img_height, bbox, zoom, scale, expected",
    [
        (
            True,
            [
                {"xmin": 63.0, "ymin": 800.0, "xmax": 102.0, "ymax": 840.0},
                {"xmin": 589.0, "ymin": 624.0, "xmax": 628.0, "ymax": 664.0},
            ],
            IMG_WIDTH * SCALE,
            IMG_HEIGHT * SCALE,
            None,
            ZOOM,
            SCALE,
            [97.65, 33.44],
        ),
        (
            False,
            [
                {"xmin": 319.0, "ymin": 178.0, "xmax": 340.0, "ymax": 200.0},
                {"xmin": 364.0, "ymin": 396.0, "xmax": 388.0, "ymax": 420.0},
            ],
            IMG_WIDTH,
            IMG_HEIGHT,
            BBOX,
            None,
            None,
            [17.48, 39.25],
        ),
    ],
)
def test_calculate_distances(
    convert_coords, pred_boxes, img_width, img_height, bbox, zoom, scale, expected
):
    distances = calculate_distances(
        LAT,
        LON,
        img_width,
        img_height,
        pred_boxes,
        convert_coords,
        bbox,
        zoom,
        scale,
    )
    assert len(distances) == len(expected)
    for dist, exp in zip(distances, expected):
        assert abs(dist[1] - exp) <= 0.01


@pytest.mark.parametrize(
    "convert_coords, bbox, expected",
    [
        (True, None, (250, 250)),
        (False, BBOX, (250, 250)),
    ],
)
def test_get_coordinate_point(convert_coords, bbox, expected):
    point = get_coordinate_point(LAT, LON, bbox, IMG_SIZE, convert_coords)
    assert isinstance(point, tuple)
    assert len(point) == 2
    assert point == expected
