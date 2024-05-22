import geopandas as gpd
from bressen.constants import VECTOR_DRIVER_EXTENSIONS
from pathlib import Path
import fiona
import pandas as pd


def read_files(
    files: list[Path], concat: bool = True, add_layer_column: bool = True
) -> gpd.GeoDataFrame | list[gpd.GeoDataFrame]:
    """read multiple feature-files into GeoDataFrame(s)

    Parameters
    ----------
    files : list[Path]
        List of feature-files
    concat : bool, optional
        Concat all to one GeoDataFrame is True, or return a list of GeoDataFrames if False, by default True
    add_layer_column : bool, optional
        Include the layer-name in a column nameed `layer` if True, by default True

    Returns
    -------
    gpd.GeoDataFrame | list[gpd.GeoDataFrame]
        One GeoDataFrame if concat is True. Otherwise a list of GeoDataFrames

    Raises
    ------
    FileNotFoundError
        If directory does not exists
    """

    # read files
    gdfs = []
    for file in files:
        layers = fiona.listlayers(file)
        for layer in layers:
            gdf = gpd.read_file(file, layer=layer, engine="pyogrio")
            # add layer name (optional)
            if add_layer_column:
                gdf.loc[:, ["layer"]] = layer
            gdfs += [gdf]

    # concat to one GeoDataFrame if True
    if concat:
        gdf = pd.concat(gdfs, ignore_index=True)
        gdf.index += 1
        return gdf
    else:
        return gdfs


def read_directory(
    directory: Path | str, concat: bool = True, add_layer_column: bool = True
) -> gpd.GeoDataFrame | list[gpd.GeoDataFrame]:
    """read a directory with feature-files into GeoDataFrame(s)

    Parameters
    ----------
    directory : Path | str
        Path to your directory
    concat : bool, optional
        Concat all to one GeoDataFrame is True, or return a list of GeoDataFrames if False, by default True
    add_layer_column : bool, optional
        Include the layer-name in a column nameed `layer` if True, by default True

    Returns
    -------
    gpd.GeoDataFrame | list[gpd.GeoDataFrame]
        One GeoDataFrame if concat is True. Otherwise a list of GeoDataFrames

    Raises
    ------
    FileNotFoundError
        If directory does not exists
    """

    # handle directory
    if isinstance(directory, str):
        directory = Path(directory)
    if (not directory.is_dir()) or (not directory.exists()):
        raise FileNotFoundError(f"{directory.absolute().resolve()} is not a directory")

    # list files, only if extensions can be interpreted by GeoPandas
    files = [
        i
        for i in directory.glob("*.*")
        if i.suffix[1:].lower() in VECTOR_DRIVER_EXTENSIONS.keys()
    ]

    return read_files(files, concat, add_layer_column)
