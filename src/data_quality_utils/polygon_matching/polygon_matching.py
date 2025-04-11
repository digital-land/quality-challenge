import geopandas as gpd
import osmnx as ox
from brdr.aligner import Aligner
from brdr.enums import OpenbaarDomeinStrategy
from brdr.loader import DictLoader
from shapely import MultiPolygon
from shapely.ops import unary_union
from shapely.wkt import loads


def download_osm_polygons(
    polygon_for_osm,
    osm_tags,
    osm_query_crs,
    brdr_crs,
    line_buffer,
):
    # Download Open Street Map polygons
    osm_features_df = gpd.GeoDataFrame(geometry=[], crs=osm_query_crs)
    osm_features_base = ox.features_from_polygon(polygon_for_osm, osm_tags)
    # Check of standard formats.
    osm_features_df = osm_features_base[
        osm_features_base.geometry.geom_type.isin(
            ["Polygon", "MultiPolygon", "LineString"]
        )
    ]
    # This ensures that LineStrings are also interpreted as v.small polygons - shortcut for all in one solution.
    osm_features_df = osm_features_df.to_crs(brdr_crs)
    line_mask = osm_features_df["geometry"].geom_type == "LineString"
    osm_features_df.loc[line_mask, "geometry"] = osm_features_df.loc[
        line_mask, "geometry"
    ].buffer(line_buffer)

    # Buffer of zero is to ensure it is a GeoPandas series, rather than a df with other args.
    osm_features_df = osm_features_df.buffer(0)

    # Align OSM co-ordinate systems
    print(f"Downloaded {len(osm_features_df)} polygons.")

    # Final check for crs matching - maybe not necessary
    # FUTURE OLI LOOK AT THIS
    if osm_features_df.crs == brdr_crs:
        osm_features_proj = osm_features_df
    else:
        osm_features_proj = osm_features_df.to_crs(brdr_crs)
    return osm_features_proj


def process_osm_polygons(osm_features_proj, used_osm_indices):
    reference_geom = None
    geometries_to_combine = None

    if used_osm_indices is None:
        # Here we use ALL downloaded features
        print("Using all polygons.")
        geometries_to_combine = osm_features_proj.geometry
    elif isinstance(used_osm_indices, list) and used_osm_indices:
        # Here we only use features at specific indices
        print(f"Selecting polygons at indices {used_osm_indices}.")
        geometries_to_combine = osm_features_proj.iloc[used_osm_indices].geometry

    # Combine all the geometries we need
    combined_reference = unary_union(geometries_to_combine)
    if not combined_reference.is_empty:
        reference_geom = combined_reference
    else:
        print("Empty osm polygons when combining")
    return reference_geom


def get_snapped_polygon(
    reference_geom,
    original_proj,
    brdr_distance,
    brdr_strategy,
    brdr_threshold,
    brdr_crs,
):
    aligned_df = None
    thematic_geom = original_proj["geometry"].iloc[0]
    if not thematic_geom.is_valid:
        # Fix for funky geoms.
        thematic_geom = thematic_geom.buffer(0)

    # Alignment logic
    aligner = Aligner(crs=brdr_crs)
    loader_thematic = DictLoader({"theme_id_1": thematic_geom})
    aligner.load_thematic_data(loader_thematic)
    loader_reference = DictLoader({"ref_id_1": reference_geom})
    aligner.load_reference_data(loader_reference)

    # Perform alignment
    process_result = aligner.process(
        relevant_distance=brdr_distance,
        od_strategy=brdr_strategy,
        threshold_overlap_percentage=brdr_threshold,
    )

    aligned_geom = process_result["theme_id_1"][brdr_distance]["result"]
    diff_geom = process_result["theme_id_1"][brdr_distance]["result_diff"]

    # Weird geom fixes
    if not aligned_geom.is_valid:
        aligned_geom = aligned_geom.buffer(0)

    aligned_df = gpd.GeoDataFrame([1], geometry=[aligned_geom], crs=brdr_crs)

    if not diff_geom.is_valid:
        diff_geom = diff_geom.buffer(0)

    diff_df = gpd.GeoDataFrame([1], geometry=[diff_geom], crs=brdr_crs)

    return aligned_df, diff_df, process_result


def process_areas(
    original_wkt: str,
    initial_crs: str = "EPSG:4326",
    osm_tags: dict | None = None,
    brdr_distance: float = 20,
    brdr_threshold: float = 10,
    brdr_strategy=OpenbaarDomeinStrategy.SNAP_ONLY_VERTICES,
    brdr_crs: str = "EPSG:3857",
    osm_query_crs: str = "EPSG:4326",
    used_osm_indices: list | None = None,
    polygon_detection_buffer: float = 0.00001,
    line_buffer: float = 0.00001,
):

    # Load datasette polygon for area
    original_geom = loads(original_wkt)
    original_df = gpd.GeoDataFrame([1], geometry=[original_geom], crs=initial_crs)
    adding_buffer_df = original_df.to_crs(brdr_crs).boundary.buffer(
        polygon_detection_buffer
    )
    df_for_query = adding_buffer_df.to_crs(osm_query_crs)

    # Need to add a small buffer to ensure that all nearby features are captured. May need testing.
    polygon_for_osm = df_for_query.geometry.iloc[0]
    original_proj = original_df.to_crs(brdr_crs)

    # # Download Open Street Map polygons
    try:
        osm_features_proj = download_osm_polygons(
            polygon_for_osm=polygon_for_osm,
            osm_tags=osm_tags,
            osm_query_crs=osm_query_crs,
            brdr_crs=brdr_crs,
            line_buffer=line_buffer,
        )
    except Exception as e:
        print(f"Error: {e}")
        print("Returning 'None'")
        return None

    # Prep features
    reference_geom = process_osm_polygons(osm_features_proj, used_osm_indices)

    # Brdr for snapping polygons
    aligned_df, diff_df, process_result = get_snapped_polygon(
        reference_geom=reference_geom,
        original_proj=original_proj,
        brdr_distance=brdr_distance,
        brdr_strategy=brdr_strategy,
        brdr_threshold=brdr_threshold,
        brdr_crs=brdr_crs,
    )
    # Prep all the borders needed for plotting in meter based crs.
    # Note, some to_crs functions could definitely be simplified here, just wanted to be 100% sure.

    # original_border = original_df["geometry"].to_crs("EPSG:3857")[0]
    original_border = original_df["geometry"].to_crs("EPSG:4326")[0]
    # new_border = aligned_df["geometry"][0]
    new_border = aligned_df["geometry"].to_crs("EPSG:4326")[0]
    red_area_calcs = [
        geom.area
        for geom in MultiPolygon(list(osm_features_proj.explode()))
        .intersection(diff_df["geometry"])
        .explode()
        if geom.area >= 100
    ]
    base_features = MultiPolygon(list(osm_features_proj.explode().to_crs("EPSG:4326")))
    difference_area = base_features.intersection(
        diff_df["geometry"].to_crs("EPSG:4326")
    )
    difference_area = difference_area.explode()
    difference_area = difference_area[
        difference_area.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    ]
    difference_area = MultiPolygon(list(difference_area))

    # Print relevant areas.
    print(f"Areas of red areas over 100m^2: {red_area_calcs}")
    print(
        f"Ratio of red areas in total area as percentage: {100*difference_area.area/new_border.area}%"
    )

    return original_border, new_border, difference_area, base_features
