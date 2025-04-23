from brdr.enums import OpenbaarDomeinStrategy
from geopandas import GeoDataFrame, GeoSeries
from shapely import MultiPolygon, Polygon

from data_quality_utils.polygon.polygon_matcher import PolygonMatcher


def test_matcher_initialization():
    matcher = PolygonMatcher()

    assert matcher is not None
    assert matcher.base_crs == "EPSG:4326"
    assert matcher.polygon_snap_distance == 20
    assert matcher.overlap_sensitivity == 10
    assert matcher.snapping_strategy == OpenbaarDomeinStrategy.SNAP_ONLY_VERTICES
    assert matcher.mercator_crs == "EPSG:3857"
    assert matcher.polygon_detection_buffer == 1.0
    assert matcher.line_buffer == 5.0


def test_custom_matcher_initialization():
    matcher = PolygonMatcher(
        polygon_snap_distance=200,
        overlap_sensitivity=50,
        snapping_strategy=OpenbaarDomeinStrategy.SNAP_NO_PREFERENCE,
        base_crs="EPSG:3857",
        mercator_crs="EPSG:4326",
        line_buffer=3,
        polygon_detection_buffer=100,
    )

    assert matcher is not None
    assert matcher.base_crs == "EPSG:3857"
    assert matcher.polygon_snap_distance == 200
    assert matcher.overlap_sensitivity == 50
    assert matcher.snapping_strategy == OpenbaarDomeinStrategy.SNAP_NO_PREFERENCE
    assert matcher.mercator_crs == "EPSG:4326"
    assert matcher.polygon_detection_buffer == 100.0
    assert matcher.line_buffer == 3.0


def test_near_tags():
    matcher = PolygonMatcher()
    lat = 51.495662
    long = -0.129605
    poly_list = [
        (long + add[0], lat + add[1])
        for add in [(0.01, 0.01), (0.01, -0.01), (-0.01, -0.01), (-0.01, 0.01)]
    ]
    poly = Polygon(poly_list)
    poly_df = GeoDataFrame([1], geometry=[poly], crs=matcher.base_crs)
    tag_keys = ["landuse", "natural"]
    found_tags = matcher.find_near_tags(poly_df, tag_keys=tag_keys)

    assert isinstance(found_tags, dict)
    assert set(found_tags.keys()) == set(tag_keys)


def test_downloaded_osm_polygons():
    matcher = PolygonMatcher()
    lat = 51.495662
    long = -0.129605
    poly_list = [
        (long + add[0], lat + add[1])
        for add in [(0.01, 0.01), (0.01, -0.01), (-0.01, -0.01), (-0.01, 0.01)]
    ]
    poly = Polygon(poly_list)
    poly_df = GeoDataFrame([1], geometry=[poly], crs=matcher.base_crs)
    feature_tags = {"landuse": ["residential"], "natural": ["wood"]}
    downloaded_polygons = matcher.download_osm_polygons(
        poly_df, feature_tags=feature_tags
    )

    assert isinstance(downloaded_polygons, GeoSeries)
    assert len(downloaded_polygons) > 0
    assert isinstance(downloaded_polygons.iloc[0], (MultiPolygon, Polygon))
