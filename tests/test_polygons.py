import pytest
from geopandas import GeoDataFrame
from shapely import Polygon, unary_union

from data_quality_utils.polygon.polygon_matcher import PolygonMatcher

BASE_CRS = "EPSG:4326"
MERCATOR_CRS = "EPSG:3857"


def create_square_coords(
    lat: int = 0, long: int = 0, add_buffer: float = 0.01
) -> Polygon:
    poly_list = [
        (long + add[0], lat + add[1])
        for add in [
            (add_buffer, add_buffer),
            (add_buffer, -add_buffer),
            (-add_buffer, -add_buffer),
            (-add_buffer, add_buffer),
        ]
    ]
    return poly_list


def create_polygon_df(coords_list: list, crs: str) -> GeoDataFrame:
    poly = Polygon(coords_list)
    gdf = GeoDataFrame([1], geometry=[poly], crs=crs)
    return gdf


@pytest.fixture
def square_df() -> GeoDataFrame:
    base_list = create_square_coords()
    return create_polygon_df(base_list, BASE_CRS)


@pytest.fixture
def small_square_df(add_buffer: float = 0.001) -> GeoDataFrame:
    base_list = create_square_coords(add_buffer=add_buffer)
    return create_polygon_df(base_list, BASE_CRS)


@pytest.fixture
def rectangle_df(long: float = 0, lat: float = 0) -> GeoDataFrame:
    return create_polygon_df(
        [
            (long + add[0], lat + add[1])
            for add in [(0.001, 0.001), (0.001, -0.001), (0, -0.001), (0, 0.001)]
        ],
        BASE_CRS,
    )


@pytest.fixture
def shifted_pentagon_df(
    long: float = 0, lat: float = 0, shift: float = 0.0001
) -> GeoDataFrame:
    return create_polygon_df(
        [
            (long - shift + add[0], lat + add[1])
            for add in [
                (0.001, 0.001),
                (0.0015, 0),
                (0.001, -0.001),
                (0.0009, -0.001),
                (0.0009, 0.001),
            ]
        ],
        BASE_CRS,
    )


@pytest.fixture
def shorter_pentagon_df(long: float = 0, lat: float = 0) -> GeoDataFrame:
    return create_polygon_df(
        [
            (long + add[0], lat + add[1])
            for add in [
                (0.001, 0.001),
                (0.0015, 0),
                (0.001, -0.001),
                (0.0005, -0.001),
                (0.0005, 0.001),
            ]
        ],
        BASE_CRS,
    )


@pytest.fixture
def pentagon_df(long: float = 0, lat: float = 0) -> GeoDataFrame:
    return create_polygon_df(
        [
            (long + add[0], lat + add[1])
            for add in [
                (0.001, 0.001),
                (0.0015, 0),
                (0.001, -0.001),
                (0, -0.001),
                (0, 0.001),
            ]
        ],
        BASE_CRS,
    )


@pytest.fixture
def triangle_df(long: float = 0, lat: float = 0) -> GeoDataFrame:
    return create_polygon_df(
        [
            (long + add[0], lat + add[1])
            for add in [(0.001, 0.001), (0.0015, 0), (0.001, -0.001)]
        ],
        BASE_CRS,
    )


def test_identical_polygons(square_df: GeoDataFrame):
    matcher = PolygonMatcher()
    base_df = square_df.copy()
    features_df = square_df.copy()
    features_series = features_df.buffer(0)
    aligned_df, diff_df = matcher.match_polygon_to_features(base_df, features_series)
    diff_area = diff_df.geometry[0].area

    assert diff_area == 0.0


def test_overlapping_polygons(
    small_square_df: GeoDataFrame, shifted_pentagon_df: GeoDataFrame
):
    matcher = PolygonMatcher(polygon_snap_distance=100)
    base_df = small_square_df.copy()
    # Create new polygon shifted from square
    features_df = shifted_pentagon_df.copy()
    features_df = features_df.to_crs(matcher.mercator_crs)
    features_series = features_df.buffer(0)
    # Align to shifted features
    aligned_df, diff_df = matcher.match_polygon_to_features(base_df, features_series)
    diff_area = diff_df.geometry[0].area
    aligned_area = aligned_df.geometry[0].area

    # Check alignment occurred
    assert diff_area > 0.0
    assert aligned_area > 0.0


def test_large_areas_list_calculations(
    pentagon_df: GeoDataFrame, triangle_df: GeoDataFrame
):
    matcher = PolygonMatcher()
    aligned_df = pentagon_df.copy()
    diff_df = triangle_df.copy()
    aligned_df = aligned_df.to_crs(matcher.mercator_crs)
    diff_df = diff_df.to_crs(matcher.mercator_crs)
    aligned_series = aligned_df.buffer(0)
    # For overlapping polygons, check area calculated correctly
    large_area_list = matcher.calculate_area_of_large_discrepancies(
        aligned_series, diff_df
    )
    # Triangular overlap area should be in list
    assert diff_df.area[0] in large_area_list


def test_large_areas_empty_list(pentagon_df: GeoDataFrame, triangle_df: GeoDataFrame):
    matcher = PolygonMatcher()
    aligned_df = pentagon_df.copy()
    diff_df = triangle_df.copy()
    aligned_df = aligned_df.to_crs(matcher.mercator_crs)
    diff_df = diff_df.to_crs(matcher.mercator_crs)
    aligned_series = aligned_df.buffer(0)
    # Set threshold too high to capture anything
    large_area_empty_list = matcher.calculate_area_of_large_discrepancies(
        aligned_series, diff_df, area_threshold=2 * aligned_df.area[0]
    )
    # Check no areas returned
    assert not large_area_empty_list


def test_large_areas_total(pentagon_df: GeoDataFrame, triangle_df: GeoDataFrame):
    matcher = PolygonMatcher()
    aligned_df = pentagon_df.copy()
    diff_df = triangle_df.copy()
    aligned_df = aligned_df.to_crs(matcher.mercator_crs)
    diff_df = diff_df.to_crs(matcher.mercator_crs)
    aligned_series = aligned_df.buffer(0)
    large_area_total = matcher.calculate_total_area_of_discrepancies(
        aligned_series, diff_df
    )
    # Check area function correctly sums areas
    assert sum(diff_df.area) == large_area_total


def test_area_proportions(
    rectangle_df: GeoDataFrame,
    triangle_df: GeoDataFrame,
    shorter_pentagon_df: GeoDataFrame,
):
    matcher = PolygonMatcher()
    base_df = rectangle_df.copy()
    diff_df = triangle_df.copy()
    features_df = shorter_pentagon_df.copy()
    aligned_poly = unary_union([base_df.geometry, features_df.geometry])
    aligned_df = GeoDataFrame([1], geometry=[aligned_poly], crs=matcher.base_crs)
    diff_df = diff_df.to_crs(matcher.mercator_crs)
    aligned_df = aligned_df.to_crs(matcher.mercator_crs)
    features_df = features_df.to_crs(matcher.mercator_crs)
    features_series = features_df.buffer(0)
    # For non-trivial overlaps calculate proportions
    area_proportion = matcher.large_discrepancy_proportion(
        features_series, aligned_df, diff_df
    )
    # Check sums are correct
    assert area_proportion == 100 * sum(diff_df.area) / sum(aligned_df.area)
