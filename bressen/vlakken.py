from typing import Literal, Optional
from geopandas import GeoDataFrame
import numpy as np


def aggregate_peil(
    gdf: GeoDataFrame,
    columns: list[str],
    method: Literal["min", "mean"] = min,
    nodata: float | None = None,
) -> GeoDataFrame:
    """Aggregate multiple peil-columns to one peil

    Parameters
    ----------
    gdf : GeoDataFrame
        Input GeoDataFrame with multiple peil-columns
    columns : list[str]
        Peil-columns to aggregate
    method : Literal["min", "mean"], optional
        Method to aggregate columns; minimum (min) or average (mean) value, by default min
    nodata : float | None, optional
        Option to filter float-values used as nodata. This prevents using these values in aggrgation, by default None

    Returns
    -------
    GeoDataFrame
        GeoDataFrame with extra column 'peil'
    """

    # handle nodata, replace to np.nan
    if nodata is not None:
        gdf.loc[:, columns] = gdf[columns].replace({nodata: np.nan})

    # aggregate
    if method == "min":
        gdf.loc[:, "peil"] = gdf[columns].min(axis=1)
    elif method == "mean":
        gdf.loc[:, "peil"] = gdf[columns].mean(axis=1)

    return gdf
