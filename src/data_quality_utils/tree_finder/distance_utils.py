import math

from geopy.distance import geodesic

TILE_SIZE = 256


def pixel_to_epsg4326(
    x: float,
    y: float,
    img_width: int,
    img_height: int,
    bbox: tuple[float, float, float, float],
) -> tuple[float, float]:
    """Convert image pixel coordinates to EPSG:4326 (lat/lon)."""
    xmin, ymin, xmax, ymax = bbox
    lon = xmin + (x / img_width) * (xmax - xmin)
    lat = ymax - (y / img_height) * (ymax - ymin)
    return lon, lat


def epsg4326_to_pixel(
    lat: float,
    lon: float,
    bbox: tuple[float, float, float, float],
    img_size: tuple[int, int],
) -> tuple[int, int]:
    """Convert EPSG:4326 (lat/lon) to pixel coordinates in an image."""
    xmin, ymin, xmax, ymax = bbox
    width, height = img_size
    x_frac = (lon - xmin) / (xmax - xmin)
    y_frac = 1 - (lat - ymin) / (ymax - ymin)
    x_pixel = int(x_frac * width)
    y_pixel = int(y_frac * height)
    return x_pixel, y_pixel


def epsg3857_to_pixel(
    lat: float, lon: float, zoom: int, scale: float
) -> tuple[float, float]:
    """Convert EPSG:3857 coordinates to pixel coordinates."""
    siny = math.sin(math.radians(lat))
    siny = min(max(siny, -0.9999), 0.9999)

    map_size = TILE_SIZE * (2**zoom) * scale
    x = (lon + 180) / 360 * map_size
    y = (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)) * map_size
    return x, y


def pixel_to_epsg3857(
    x: float, y: float, zoom: int, scale: float
) -> tuple[float, float]:
    """Convert pixel coordinates to EPSG:3857 (lat/lon)."""
    map_size = TILE_SIZE * (2**zoom) * scale
    lon = x / map_size * 360.0 - 180.0
    n = math.pi - 2.0 * math.pi * y / map_size
    lat = math.degrees(math.atan(math.sinh(n)))
    return lat, lon


def calculate_distances(
    lat: float,
    lon: float,
    img_width: int,
    img_height: int,
    pred_boxes: list[dict[str, float]],
    convert_coords: bool,
    bbox: tuple[float, float, float, float] | None = None,
    zoom: int | None = None,
    scale: float | None = None,
) -> list[tuple[tuple[float, float], float, dict[str, float]]]:
    """Calculate distances from predicted tree boxes to a given geographic location."""
    distances = []
    for box in pred_boxes:
        x_center = (box["xmin"] + box["xmax"]) / 2
        y_center = (box["ymin"] + box["ymax"]) / 2

        if convert_coords:
            center_px, center_py = epsg3857_to_pixel(lat, lon, zoom, scale)
            abs_px = center_px - (img_width / 2) + x_center
            abs_py = center_py - (img_height / 2) + y_center
            pred_lat, pred_lon = pixel_to_epsg3857(abs_px, abs_py, zoom, scale)
        else:
            pred_lon, pred_lat = pixel_to_epsg4326(
                x_center, y_center, img_width, img_height, bbox
            )

        box_dist = geodesic((pred_lat, pred_lon), (lat, lon)).meters
        distances.append(((pred_lat, pred_lon), box_dist, box))
    return distances


def get_coordinate_point(
    lat: float,
    lon: float,
    bbox: tuple[float] | None,
    img_size: tuple[int, int],
    convert_coords: bool,
):
    """Get original tree coordinate point."""
    if convert_coords:
        x_pixel = img_size[0] // 2
        y_pixel = img_size[1] // 2
    else:
        x_pixel, y_pixel = epsg4326_to_pixel(lat, lon, bbox, img_size)
    return (x_pixel, y_pixel)
