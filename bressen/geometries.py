from shapely.geometry import Point, MultiLineString
from shapely.geometry.base import BaseGeometry
import geopandas as gpd
from shapely import ops

def get_geometry(row):
    if not isinstance(row, BaseGeometry):
        geometry = row.geometry
    else:
        geometry = row
    return geometry

def _sub_select_dataframe(geometry, gdf, tolerance=0.1):
    # get feature bounds, buffer point with tolerance
    if isinstance(geometry, Point):
        bounds = geometry.buffer(tolerance).bounds
    else:
        bounds = geometry.bounds
    
    # select with spatial index
    idx = gdf.sindex.intersection(bounds)

    return gdf.iloc[idx]

    

def get_closest_feature(row, gdf, max_distance: float | None = None, tolerance=0.1):

    # set tolerance
    if max_distance is not None:
        tolerance = max(max_distance, tolerance)

    #function works with Pandas row and with geometry
    geometry = get_geometry(row)

    # sub-select using spatial index
    gdf_select = _sub_select_dataframe(geometry, gdf, tolerance=tolerance)

    # sort by distance to geometry
    gdf_select = gdf_select.loc[gdf_select.distance(geometry).sort_values().index.to_list()]

    # return feature if found and within max_distance (optional)
    if gdf_select.empty:
        return None
    else:
        result = gdf.loc[gdf_select.index[0]]
        # check max distance
        if (max_distance is not None) and (result.geometry.distance(geometry) > max_distance):
            result = None

        return result

def get_containing_feature(row, gdf):

    #function works with Pandas row and with geometry
    geometry = get_geometry(row)
    gdf_select = _sub_select_dataframe(geometry, gdf, tolerance=0.1)

    #further select containing features
    gdf_select = gdf_select[gdf_select.contains(geometry)]
    
    if gdf_select.empty:
        return None
    elif len(gdf_select) > 1:
        raise ValueError(f"geometry is contained by multiple features with fids {gdf.index.to_list()}")
    else:
        return gdf_select.iloc[0]

def project_point(line, point) -> Point:
    return line.interpolate(line.project(point))

def get_offsets(line, distance) -> gpd.GeoSeries:
    offsets = gpd.GeoSeries([line.parallel_offset(distance, side=side) for side in ["left", "right"]])
    if (offsets.geom_type == "MultiLineString").any():
        offsets = offsets.geometry.apply(lambda x: ops.linemerge(x) if isinstance(x, MultiLineString) else x)
    return offsets