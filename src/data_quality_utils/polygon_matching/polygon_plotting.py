import numpy as np
import plotly.graph_objects as go
from geopandas import GeoDataFrame, GeoSeries
from shapely import LineString, MultiLineString, MultiPolygon
from shapely.validation import make_valid


def get_plotting_polygons(
    original_df: GeoDataFrame,
    base_features_df: GeoSeries,
    aligned_df: GeoDataFrame,
    diff_df: GeoDataFrame,
    base_crs: str,
) -> tuple[
    MultiPolygon,
    MultiPolygon,
    MultiPolygon,
    MultiPolygon,
]:
    """Standardises forms of polygon_matching polygons for plotting.

    :param original_df: GeoDataFrame with original boundary.
    :param base_features_df: GeoSeries with base polygon features from Open Street Map.
    :param aligned_df: GeoDataFrame with new boundary.
    :param diff_df: GeoDataFrame with areas that differ to original boundary.
    :param base_crs: Co-ordinate reference system we use as a base.
    :return: Tuple of standardised Polygons/Multipolygons in same order.
    """
    original_border = original_df["geometry"].to_crs(base_crs)[0]

    new_border = MultiPolygon(list(aligned_df["geometry"].explode().to_crs(base_crs)))
    base_features = MultiPolygon(list(base_features_df.explode().to_crs(base_crs)))
    difference_area = make_valid(base_features).intersection(
        diff_df["geometry"].to_crs(base_crs)
    )
    difference_area = difference_area.explode()
    difference_area = difference_area[
        difference_area.geometry.geom_type.isin(["Polygon", "MultiPolygon"])
    ]
    difference_area = MultiPolygon(list(difference_area))

    return original_border, base_features, new_border, difference_area


def polygon_prep(
    multi_polygon: MultiPolygon,
) -> tuple[list[float | None], list[float | None]]:
    """Prepares polygons for plotting.

    :param polygon: MultiPolygon to plot.
    :return: Two lists of co-ordinates to plot.
    """
    # Need to convert from crs to co-ords for this plotly method
    lons: list[float | None] = []
    lats: list[float | None] = []

    for poly in multi_polygon.geoms:
        boundary = poly.boundary
        if isinstance(boundary, MultiLineString):
            single_boundary = boundary.geoms[0]
            x_coords, y_coords = single_boundary.coords.xy
            lon, lat = x_coords, y_coords
            lons += list(lon)
            lats += list(lat)
            lons.append(None)
            lats.append(None)
        elif isinstance(boundary, LineString):
            x_coords, y_coords = boundary.coords.xy
            lon, lat = x_coords, y_coords
            lons += list(lon)
            lats += list(lat)
            lons.append(None)
            lats.append(None)

    return lons, lats


def plot_area_with_sliders(
    original_border: MultiPolygon,
    base_features: MultiPolygon,
    new_border: MultiPolygon,
    difference_area: MultiPolygon,
    diff_rgb: tuple[int, int, int],
    base_rgb: tuple[int, int, int],
    alpha: float,
    area_name: str,
) -> None:
    """Creates interactive plot for all areas.

    :param original_border: Original area border.
    :param base_features: Base feature Polygons
    :param new_border: New area border.
    :param difference_area: Polygons where areas differ.
    :param diff_rgb: RGB colour for areas that differ and intersect base features.
    :param base_rgb: RGB colour for base features.
    :param alpha: Initial opacity of base_features and area differences.
    :param area_name: Name of area
    :return: None
    """

    diff_lons, diff_lats = polygon_prep(difference_area)
    feature_lons, feature_lats = polygon_prep(base_features)
    original_lons, original_lats = polygon_prep(original_border)
    new_lons, new_lats = polygon_prep(new_border)

    # Find centre for plotting
    boundary_centre = original_border.centroid
    centre_lon, centre_lat = boundary_centre.x, boundary_centre.y

    # Get colours and adjust alphas
    diff_fill_colour = f"rgba({diff_rgb[0]}, {diff_rgb[1]}, {diff_rgb[2]}, {alpha})"
    diff_line_colour = (
        f"rgba({diff_rgb[0]}, {diff_rgb[1]}, {diff_rgb[2]}, {min(alpha+0.1, 1)})"
    )
    feature_fill_colour = f"rgba({base_rgb[0]}, {base_rgb[1]}, {base_rgb[2]}, {alpha})"
    feature_line_colour = (
        f"rgba({base_rgb[0]}, {base_rgb[1]}, {base_rgb[2]}, {min(alpha+0.1, 1)})"
    )

    # Prep dicts for plotly alpha sliders - steps of 0.1
    diff_steps = []
    feature_steps = []
    alphas = np.linspace(0, 1, 11)
    for _, alpha_step in enumerate(alphas):
        alpha_step = round(alpha_step, 2)
        diff_step_color = (
            f"rgba({diff_rgb[0]}, {diff_rgb[1]}, {diff_rgb[2]}, {alpha_step})"
        )
        feature_step_color = (
            f"rgba({base_rgb[0]}, {base_rgb[1]}, {base_rgb[2]}, {alpha_step})"
        )

        diff_step = dict(
            method="restyle",
            args=[{"fillcolor": [diff_step_color]}, [0]],
            label=str(alpha_step),
        )
        diff_steps.append(diff_step)

        feature_step = dict(
            method="restyle",
            args=[{"fillcolor": [feature_step_color]}, [1]],
            label=str(alpha_step),
        )
        feature_steps.append(feature_step)

    diff_sliders = [
        dict(
            active=3,
            currentvalue={"prefix": "Added Area alpha: ", "visible": True},
            pad={"t": 20},
            steps=diff_steps,
        )
    ]

    feature_sliders = [
        dict(
            active=3,
            currentvalue={"prefix": "Base Features alpha: ", "visible": True},
            pad={"t": 120},
            steps=feature_steps,
        )
    ]

    # Start base plots and figure
    fig = go.Figure()
    fig.add_trace(
        go.Scattermap(
            lon=diff_lons,
            lat=diff_lats,
            mode="lines",
            fill="toself",
            fillcolor=diff_fill_colour,
            line=dict(color=diff_line_colour, width=1),
            name="Concerning Areas",
            showlegend=True,
        )
    )

    fig.add_trace(
        go.Scattermap(
            lon=feature_lons,
            lat=feature_lats,
            mode="lines",
            fill="toself",
            fillcolor=feature_fill_colour,
            line=dict(color=feature_line_colour, width=1),
            name="Base Features",
            showlegend=True,
        )
    )

    # Now plot boundary lines
    fig.add_trace(
        go.Scattermap(
            lon=original_lons,
            lat=original_lats,
            mode="lines",
            fill="none",
            line=dict(color="black", width=3),
            name="Original Boundary",
            showlegend=True,
        )
    )

    fig.add_trace(
        go.Scattermap(
            lon=new_lons,
            lat=new_lats,
            mode="lines",
            fill="none",
            line=dict(color="red", width=1),
            name="New Boundary",
            showlegend=True,
        )
    )

    # Zoom in for plot - gets in close to area
    initial_zoom = 15

    # Satellite works differently - plotly in-built in 'style' arg doesn't work when zoomed in
    satellite_layer = [
        dict(
            below="traces",
            sourcetype="raster",
            source=[
                "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            ],
        )
    ]

    # Button for changing styles
    map_switch = [
        dict(
            args=[{"map.style": "open-street-map", "map.layers": None}],
            label="OSM",
            method="relayout",
        ),
        dict(
            args=[{"map.style": None, "map.layers": satellite_layer}],
            label="Satellite",
            method="relayout",
        ),
    ]

    # Add formatting changes with sliders and button
    fig.update_layout(
        title_text=f"Conservation area anomalies in {area_name}",
        geo_scope="europe",
        map=dict(
            style="open-street-map",
            center=dict(lon=centre_lon, lat=centre_lat),
            zoom=initial_zoom,
        ),
        showlegend=True,
        margin={"r": 100, "t": 50, "l": 100, "b": 50},
        sliders=diff_sliders + feature_sliders,
        height=800,
        width=1000,
        updatemenus=[
            dict(
                type="buttons",
                direction="left",
                buttons=map_switch,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=0.7,
                xanchor="right",
                y=1.15,
                yanchor="top",
            ),
        ],
    )

    fig.show()

    return None
