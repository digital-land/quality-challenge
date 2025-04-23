from pyproj import Geod
from shapely import MultiPolygon
from shapely.ops import nearest_points


def shortest_distance(
    a: MultiPolygon, b: MultiPolygon, ellisoid_config: str = "WGS84"
) -> float:
    """Find the shortest distance between two polygons.

    :param a: A shapely polygon
    :param b: A shapely polygon
    :param ellipsoid_config: pyproj ellipsoid setting, defaults to "WGS84"
    :return: distance in km
    """
    geod = Geod(ellps="WGS84")
    point_a, point_b = nearest_points(a, b)
    _, _, distance = geod.inv(point_a.x, point_a.y, point_b.x, point_b.y)
    return 1e-3 * distance


def overlap_ratio(a: MultiPolygon, b: MultiPolygon) -> float:
    """Find the overlap between two polygons as fraction of their
    shared, non-duplicative area. ie. total area only counts
    the overlap once.

    :param a: A shapely polygon
    :param b: A shapely polygon
    :return: Fraction of total area that is overlap.
    """
    overlap = a.intersection(b).area
    return overlap / (a.area + b.area - overlap)
