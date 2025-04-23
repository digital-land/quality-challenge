from typing import Any

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


def extract_coordinates(
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


def _make_slider_steps(
    base_color: tuple[int, int, int], slider_index: int, n_steps=11
) -> list[dict[Any, Any]]:
    """Generates the configure dictionary for a transparency slider, adding n_steps
    alpha values to the base colour to give different opacity settings.

    :param base_color: Colour to generate opacity levels for as an RGB tuple.
    :param slider_index: Index of slider in plotly figure
    :param n_steps: Number of alpha values to include, defaults to 11
    :return: Config dict for slider.
    """
    return [
        dict(
            method="restyle",
            args=[
                {
                    "fillcolor": [
                        f"rgba({base_color[0]}, {base_color[1]}, {base_color[2]}, {alpha_step:.2f})"
                    ]
                },
                [slider_index],
            ],
            label=f"{alpha_step:.2f}",
        )
        for alpha_step in np.linspace(0, 1, n_steps)
    ]


def plot_multipolygon(
    polygon: MultiPolygon,
    fig: go.Figure,
    name: str,
    fill_color: None | tuple[int, int, int] = None,
    fill_alpha: None | float = 0.3,
    line_color: str = "black",
    line_width: int = 1,
) -> go.Figure:
    """Plot a (Multi)polygon on a plotly figure.

    :param polygon: Polygon to plot
    :param fig: Plotly figure to plot onto
    :param name: Name to give the trace that is added to the plot
    :param fill_color: Optionally fill polygon with RGB colour, defaults to None
    :param fill_alpha: Optional opacity if filling polygon, defaults to 0.3
    :param line_color: Outline colour for polygon, defaults to "black"
    :param line_width: Width of polygon outline, defaults to 1
    :return: modified figure
    """
    lons, lats = extract_coordinates(polygon)

    if fill_color:
        fill_color_str = (
            f"rgba({fill_color[0]}, {fill_color[1]}, {fill_color[2]}, {fill_alpha})"
        )
        fill = "toself"
    else:
        fill_color_str = None
        fill = "none"

    fig.add_trace(
        go.Scattermap(
            lon=lons,
            lat=lats,
            mode="lines",
            fill=fill,
            fillcolor=fill_color_str,
            line=dict(color=line_color, width=line_width),
            name=name,
            showlegend=True,
        )
    )
    return fig


def plot_area_with_sliders(
    original_border: MultiPolygon,
    base_features: MultiPolygon,
    new_border: MultiPolygon,
    difference_area: MultiPolygon,
    area_name: str,
    diff_rgb: tuple[int, int, int] = (255, 0, 0),
    base_rgb: tuple[int, int, int] = (0, 0, 255),
    alpha: float = 0.3,
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

    # Find centre for plotting
    boundary_centre = original_border.centroid
    centre_lon, centre_lat = boundary_centre.x, boundary_centre.y

    # Get colours and adjust alphas
    diff_line_colour = (
        f"rgba({diff_rgb[0]}, {diff_rgb[1]}, {diff_rgb[2]}, {min(alpha+0.1, 1)})"
    )
    feature_line_colour = (
        f"rgba({base_rgb[0]}, {base_rgb[1]}, {base_rgb[2]}, {min(alpha+0.1, 1)})"
    )

    # Prep dicts for plotly alpha sliders - steps of 0.1
    diff_steps = _make_slider_steps(base_color=diff_rgb, slider_index=0)
    feature_steps = _make_slider_steps(base_color=base_rgb, slider_index=1)

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
    fig = plot_multipolygon(
        difference_area,
        fig=fig,
        name="Concerning Areas",
        fill_color=diff_rgb,
        fill_alpha=alpha,
        line_color=diff_line_colour,
    )

    fig = plot_multipolygon(
        base_features,
        fig=fig,
        name="Base Features",
        fill_color=base_rgb,
        fill_alpha=alpha,
        line_color=feature_line_colour,
    )

    fig = plot_multipolygon(
        original_border, fig=fig, name="Original Boundary", line_width=3
    )

    fig = plot_multipolygon(new_border, fig=fig, name="New Boundary", line_color="red")

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
                direction="down",
                buttons=map_switch,
                pad={"r": 10, "t": 10},
                showactive=True,
                x=1.2,
                xanchor="right",
                y=-0.15,
                yanchor="top",
            ),
        ],
    )

    fig.show()

    return None
