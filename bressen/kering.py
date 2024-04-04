from bressen.geometries import get_closest_feature, line_merge
from shapely import ops
from shapely.geometry import LineString, MultiLineString
from itertools import chain

def get_kering_geometry(row, keringen, max_distance, min_length: int | None = None, max_line_extends=1):
    kering = get_closest_feature(row, keringen, max_distance=max_distance)
    if kering is None:
        raise ValueError(f"Geen kering gevonden binnen {max_distance} van bres met fid {row.Index}")

    kering_geometry = kering.geometry
    if min_length is not None:
        mid_point = kering_geometry.project(row.geometry)

        # extend backward if have to
        extend = 0
        passed_lines = [kering.name]
        point = kering.geometry.boundary.geoms[0]
        while (mid_point - (min_length / 2)) < 0:
            # count loops and check attempts
            if extend >= max_line_extends:
                break
            extend += 1
            #
            extra_line = get_closest_feature(
                point,
                keringen[~keringen.index.isin(passed_lines)],
                max_distance=max_distance,
                boundary=True
                )
            # if we cant find a line, we stop
            if extra_line is None:
                break
            kering_geometry = line_merge(ops.linemerge([extra_line.geometry, kering_geometry]))
            mid_point = kering_geometry.project(row.geometry)
            passed_lines += [extra_line.name]
            point = extra_line.geometry.boundary.geoms[0]

        # extend forward if have to
        extend = 0
        point = kering.geometry.boundary.geoms[1]
        while (mid_point + (min_length / 2)) > kering_geometry.length:
            # count loops and check attempts
            if extend >= max_line_extends:
                break
            extend += 1
            extra_line = get_closest_feature(
                point,
                keringen[~keringen.index.isin(passed_lines)],
                max_distance=max_distance,
                boundary=True
                )
            # if we cant find a line, we stop
            if extra_line is None:
                break
            kering_geometry = line_merge(ops.linemerge([kering_geometry, extra_line.geometry]))
            mid_point = kering_geometry.project(row.geometry)
            passed_lines += [extra_line.name]
            point = extra_line.geometry.boundary.geoms[1]
    


    return kering_geometry
