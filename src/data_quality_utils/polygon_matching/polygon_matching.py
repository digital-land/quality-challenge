import geopandas as gpd
import osmnx as ox
from brdr.aligner import Aligner
from brdr.enums import OpenbaarDomeinStrategy
from brdr.loader import DictLoader
from geopandas import GeoDataFrame, GeoSeries
from shapely import MultiPolygon, Polygon
from shapely.ops import unary_union
from shapely.validation import make_valid


class PolygonMatcher:
    """
    Polygon matching class with functionalities for providing new boundaries
    based on existing feature polygons
    :param base_crs: Co-ordinate reference system we use as a base.
    :param polygon_snap_distance: Distance (m) our new boundary can snap to features within.
        Lower means less features are likely to be snapped to, but higher can snap to irrelevant polygons.
    :param overlap_sensitivity: Threshold (%) of overlap between base features and original border for brdr to
        consider snapping to base features. Lower means more sensitive.
    :param snapping_strategy: Strategy for brdr's snapping algorithm. Please consult their documentation for the full list.
    :param mercator_crs: Co-ordinate reference system for mercator projection. Used for Brdr and distances.
    :param polygon_detection_buffer: Radius of buffer around our boundary (m) for polygons to consider snapping to.
    :param line_buffer: Radius of small buffer to expand linestring objects to be considered polygons
    """

    def __init__(
        self,
        base_crs: str = "EPSG:4326",
        polygon_snap_distance: float = 20,
        overlap_sensitivity: float = 10,
        snapping_strategy: int = OpenbaarDomeinStrategy.SNAP_ONLY_VERTICES,
        mercator_crs: str = "EPSG:3857",
        polygon_detection_buffer: float = 1.0,
        line_buffer: float = 5.0,
    ):
        self.base_crs = base_crs
        self.polygon_snap_distance = polygon_snap_distance
        self.overlap_sensitivity = overlap_sensitivity
        self.snapping_strategy = snapping_strategy
        self.mercator_crs = mercator_crs
        self.base_crs = base_crs
        self.polygon_detection_buffer = polygon_detection_buffer
        self.line_buffer = line_buffer

    def find_near_tags(
        self, original_df: GeoDataFrame, tag_keys: list[str] = ["landuse", "natural"]
    ) -> dict:
        """Finds OSM tags near the original border. These tags can be directly
        fed in to downstream tasks.

        :param original_df: Dataframe with original area polygon.
        :param tag_keys: List of tag keys for the search.
            This function returns all features under this more general
            tag key, defaults to ["landuse", "natural"].
        :return: Dictionary of tags formatted for use in download_osm_polygons.
        """
        nearby_tags = dict()
        added_buffer_df = original_df.to_crs(self.mercator_crs).boundary.buffer(
            self.polygon_detection_buffer
        )
        df_for_query = added_buffer_df.to_crs(self.base_crs)
        polygon_for_osm = df_for_query.geometry.iloc[0]
        query_all_tags: dict[str, bool | str | list[str]] = {
            feature: True for feature in tag_keys
        }
        downloaded_features_df = ox.features_from_polygon(
            polygon_for_osm, query_all_tags
        )

        for tag in tag_keys:
            specific_tags = list(downloaded_features_df[tag].dropna().unique())
            nearby_tags[tag] = specific_tags
        return nearby_tags

    def download_osm_polygons(
        self,
        original_df: GeoDataFrame,
        feature_tags: dict,
    ) -> GeoSeries:
        """Downloads polygons within boundary from Open Street Map.

        :param original_df: Dataframe with original area polygon.
        :param feature_tags: Dictionary with Open Street Map tags for which polygon types we wish to consider.
        :return: GeoSeries with all polygons found in our downloading search.
        """

        added_buffer_df = original_df.to_crs(self.mercator_crs).boundary.buffer(
            self.polygon_detection_buffer
        )
        df_for_query = added_buffer_df.to_crs(self.base_crs)
        polygon_for_osm = df_for_query.geometry.iloc[0]

        base_features_df = gpd.GeoDataFrame(geometry=[], crs=self.base_crs)
        downloaded_features_df = ox.features_from_polygon(polygon_for_osm, feature_tags)

        base_features_df = downloaded_features_df[
            downloaded_features_df.geometry.geom_type.isin(
                ["Polygon", "MultiPolygon", "LineString"]
            )
        ]
        # This ensures that LineStrings are also interpreted as v.small polygons - shortcut for all in one solution.
        base_features_df = base_features_df.to_crs(self.mercator_crs)
        linestring_mask = base_features_df["geometry"].geom_type == "LineString"
        base_features_df.loc[linestring_mask, "geometry"] = base_features_df.loc[
            linestring_mask, "geometry"
        ].buffer(self.line_buffer)

        # Buffer of zero is to ensure it is a GeoPandas series, rather than a df with other args.
        base_features_df = base_features_df.buffer(0)

        if base_features_df.crs != self.mercator_crs:
            return base_features_df.to_crs(self.mercator_crs)
        return base_features_df

    def _combine_osm_polygons(
        self,
        base_features_df: GeoSeries,
    ) -> Polygon | MultiPolygon:
        """Utility for combining and standardising base features.

        :param base_features_df: GeoSeries with all the relevant base polygons.
        :return: Combined Polygon or MultiPolygon for base features.
        """
        geometries_to_combine = base_features_df.geometry
        # Combine all the geometries we need
        combined_geometries = unary_union(geometries_to_combine)
        if isinstance(combined_geometries, (Polygon | MultiPolygon)):
            return combined_geometries
        else:
            raise TypeError(
                f"Non MultiPolygon or Polygon type returned by unary_union - type of {type(combined_geometries)}"
            )

    def _get_snapped_polygon(
        self,
        new_geom: Polygon | MultiPolygon,
        original_projection: GeoDataFrame,
    ) -> tuple[GeoDataFrame, GeoDataFrame]:
        """Utilise brdr to obtain a new boundary based on parameters and areas.

        :param new_geom: New geometries we want our boundary to consider. These are the base features.
        :param original_projection: The original boundary projected appropriately for this task.
        :return: tuple with aligned_df containing new boundary and diff_geom for polygons where areas changed.
        """
        aligned_df = None
        original_geom = original_projection["geometry"].iloc[0]
        if not original_geom.is_valid:
            original_geom = original_geom.buffer(0)

        # Alignment logic
        aligner = Aligner(crs=self.mercator_crs)
        original_loader = DictLoader({"theme_id_1": original_geom})
        aligner.load_thematic_data(original_loader)
        new_loader = DictLoader({"ref_id_1": new_geom})
        aligner.load_reference_data(new_loader)

        # Perform alignment
        process_result = aligner.process(
            relevant_distance=self.polygon_snap_distance,
            od_strategy=self.snapping_strategy,
            threshold_overlap_percentage=self.overlap_sensitivity,
        )
        aligned_geom = process_result["theme_id_1"][self.polygon_snap_distance][
            "result"
        ]
        diff_geom = process_result["theme_id_1"][self.polygon_snap_distance][
            "result_diff"
        ]

        if not aligned_geom.is_valid:
            aligned_geom = aligned_geom.buffer(0)

        aligned_df = gpd.GeoDataFrame(
            [1], geometry=[aligned_geom], crs=self.mercator_crs
        )

        if not diff_geom.is_valid:
            diff_geom = diff_geom.buffer(0)

        diff_df = gpd.GeoDataFrame([1], geometry=[diff_geom], crs=self.mercator_crs)

        return aligned_df, diff_df

    def match_polygon_to_features(
        self,
        original_df: GeoDataFrame,
        base_features_df: GeoSeries,
    ) -> tuple[GeoDataFrame, GeoDataFrame]:
        """From original boundary and base features from our map, this function provides the new
            aligned boundary with the line snapped to relevant features, and where this new
            boundary differs from the original.

        :param original_df: GeoDataFrame with original boundary.
        :param base_features_df: GeoSeries with base polygon features from Open Street Map.
        :return: tuple with aligned_df containing new boundary and diff_geom for polygons where areas changed.
        """
        original_projection = original_df.to_crs(self.mercator_crs)
        new_geom = self._combine_osm_polygons(base_features_df)
        aligned_df, diff_df = self._get_snapped_polygon(
            new_geom=new_geom,
            original_projection=original_projection,
        )

        return aligned_df, diff_df

    def calculate_area_of_large_discrepancies(
        self,
        base_features_df: GeoSeries,
        diff_df: GeoDataFrame,
        area_threshold: float = 100,
    ) -> list[float]:
        """Calculates the areas of large areas of concern, based on a user set threshold.

        :param base_features_df: GeoSeries with base polygon features from Open Street Map.
        :param diff_df: GeoDataFrame with areas that differ to original boundary.
        :param area_threshold: Threshold above which we return areas, defaults to 100
        :return: List of large areas.
        """
        base_features_multipolygon = make_valid(
            MultiPolygon(list(base_features_df.explode()))
        )

        red_area_calcs = [
            make_valid(geom).area
            for geom in base_features_multipolygon.intersection(
                diff_df["geometry"]
            ).explode()
            if geom.area >= area_threshold
        ]

        return red_area_calcs

    def calculate_total_area_of_discrepancies(
        self,
        base_features_df: GeoSeries,
        diff_df: GeoDataFrame,
        area_threshold: float = 100,
    ) -> float:
        """Calculates the total area of areas of concern, red on the map.

        :param base_features_df: GeoSeries with base polygon features from Open Street Map.
        :param diff_df: GeoDataFrame with areas that differ to original boundary.
        :param area_threshold: Threshold above which we return areas, defaults to 100
        :return: List of large areas.
        """
        base_features_multipolygon = make_valid(
            MultiPolygon(list(base_features_df.explode()))
        )

        red_area_calcs = [
            make_valid(geom).area
            for geom in base_features_multipolygon.intersection(
                diff_df["geometry"]
            ).explode()
        ]

        return sum(red_area_calcs)

    def large_discrepancy_proportion(
        self,
        base_features_df: GeoSeries,
        aligned_df: GeoDataFrame,
        diff_df: GeoDataFrame,
    ) -> float:
        """Calculates the percentage of our new boundary that is an area of concern.

        :param base_features_df: GeoSeries with base polygon features from Open Street Map.
        :param aligned_df: GeoDataFrame with new boundary.
        :param diff_df: GeoDataFrame with areas that differ to original boundary.
        :return: Percentage of new boundary that is of concern.
        """
        difference_area = unary_union(base_features_df).intersection(
            diff_df["geometry"][0]
        )
        new_border = aligned_df["geometry"][0]
        ratio = 100 * difference_area.area / new_border.area

        return ratio
