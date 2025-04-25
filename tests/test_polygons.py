from geopandas import GeoDataFrame
from shapely import Polygon, unary_union

from data_quality_utils.polygon.polygon_matcher import PolygonMatcher


def create_square_coords(lat: int = 0, long: int = 0, add_buffer=0.01) -> Polygon:
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


def test_identical_polygons():
    matcher = PolygonMatcher()
    base_list = create_square_coords()
    base_df = create_polygon_df(base_list, matcher.base_crs)
    features_list = create_square_coords()
    features_df = create_polygon_df(features_list, matcher.base_crs)
    features_series = features_df.buffer(0)
    aligned_df, diff_df = matcher.match_polygon_to_features(base_df, features_series)
    diff_area = diff_df.geometry[0].area
    aligned_area = aligned_df.geometry[0].area

    assert diff_area == 0.0
    assert base_df.to_crs(matcher.mercator_crs).geometry[0].area == aligned_area


def test_overlapping_polygons():
    matcher = PolygonMatcher(polygon_snap_distance=100)
    lat, long = (0, 0)
    base_list = create_square_coords(lat, long, add_buffer=0.001)
    base_df = create_polygon_df(base_list, matcher.base_crs)
    features_df = create_polygon_df(
        [
            (long - 0.0001 + add[0], lat + add[1])
            for add in [
                (0.001, 0.001),
                (0.0015, 0),
                (0.001, -0.001),
                (0.0009, -0.001),
                (0.0009, 0.001),
            ]
        ],
        matcher.base_crs,
    )
    features_df = features_df.to_crs(matcher.mercator_crs)
    features_series = features_df.buffer(0)
    aligned_df, diff_df = matcher.match_polygon_to_features(base_df, features_series)
    diff_area = diff_df.geometry[0].area
    aligned_area = aligned_df.geometry[0].area

    assert diff_area is not None
    assert aligned_area is not None
    assert diff_area > 0.0
    assert aligned_area > 0.0


def test_large_areas_list():
    matcher = PolygonMatcher()
    lat, long = (0, 0)
    aligned_df = create_polygon_df(
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
        matcher.base_crs,
    )
    diff_df = create_polygon_df(
        [
            (long + add[0], lat + add[1])
            for add in [(0.001, 0.001), (0.0015, 0), (0.001, -0.001)]
        ],
        matcher.base_crs,
    )
    aligned_df = aligned_df.to_crs(matcher.mercator_crs)
    diff_df = diff_df.to_crs(matcher.mercator_crs)
    aligned_series = aligned_df.buffer(0)
    large_area_list = matcher.calculate_area_of_large_discrepancies(
        aligned_series, diff_df
    )
    large_area_empty_list = matcher.calculate_area_of_large_discrepancies(
        aligned_series, diff_df, area_threshold=2 * aligned_df.area[0]
    )

    assert isinstance(large_area_list, list)
    assert diff_df.area[0] in large_area_list
    assert not large_area_empty_list


def test_large_areas_total():
    matcher = PolygonMatcher()
    lat, long = (0, 0)
    aligned_df = create_polygon_df(
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
        matcher.base_crs,
    )
    diff_df = create_polygon_df(
        [
            (long + add[0], lat + add[1])
            for add in [(0.001, 0.001), (0.0015, 0), (0.001, -0.001)]
        ],
        matcher.base_crs,
    )
    aligned_df = aligned_df.to_crs(matcher.mercator_crs)
    diff_df = diff_df.to_crs(matcher.mercator_crs)
    aligned_series = aligned_df.buffer(0)
    large_area_total = matcher.calculate_total_area_of_discrepancies(
        aligned_series, diff_df
    )

    assert isinstance(large_area_total, float)
    assert sum(diff_df.area) == large_area_total


def test_area_proportions():
    matcher = PolygonMatcher()
    lat, long = (0, 0)
    base_df = create_polygon_df(
        [
            (long + add[0], lat + add[1])
            for add in [(0.001, 0.001), (0.001, -0.001), (0, -0.001), (0, 0.001)]
        ],
        matcher.base_crs,
    )
    diff_df = create_polygon_df(
        [
            (long + add[0], lat + add[1])
            for add in [(0.001, 0.001), (0.0015, 0), (0.001, -0.001)]
        ],
        matcher.base_crs,
    )
    features_df = create_polygon_df(
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
        matcher.base_crs,
    )
    aligned_poly = unary_union([base_df.geometry, features_df.geometry])
    aligned_df = GeoDataFrame([1], geometry=[aligned_poly], crs=matcher.base_crs)
    diff_df = diff_df.to_crs(matcher.mercator_crs)
    aligned_df = aligned_df.to_crs(matcher.mercator_crs)
    features_df = features_df.to_crs(matcher.mercator_crs)
    features_series = features_df.buffer(0)
    area_proportion = matcher.large_discrepancy_proportion(
        features_series, aligned_df, diff_df
    )

    assert isinstance(area_proportion, float)
    assert area_proportion == 100 * sum(diff_df.area) / sum(aligned_df.area)
