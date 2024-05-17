from dataclasses import dataclass

import fiona
import geopandas as gpd
from geopandas import GeoDataFrame

from bressen.styles import add_styles_to_geopackage

LAYERS = ["keringen", "peilvlakken", "watervlakken"]


@dataclass
class BasisGegevens:
    keringen: GeoDataFrame | None = None
    peilvlakken: GeoDataFrame | None = None
    watervlakken: GeoDataFrame | None = None

    @classmethod
    def from_gpkg(cls, file_name: str):
        """Init class from a gpkg_file

        Parameters
        ----------
        gpkg_file : str
            Path to GeoPackage

        Returns
        -------
        BasisGegevens
            BasisGegevens from GeoPackage
        """
        kwargs = {i: None for i in fiona.listlayers(file_name) if i in LAYERS}
        for layer in kwargs.keys():
            kwargs[layer] = gpd.read_file(file_name, layer=layer, engine="pyogrio")
        return cls(**kwargs)

    def to_gpkg(self, gpkg_file: str):
        """Write to styled GeoPackage

        Parameters
        ----------
        gpkg_file : str
            Path to GeoPackage
        """
        for layer in LAYERS:
            df = getattr(self, layer)
            if df is not None:
                df.to_file(gpkg_file, layer=layer, engine="pyogrio")

        add_styles_to_geopackage(gpkg_file)
