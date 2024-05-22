from geopandas import GeoDataFrame

from bressen import read_directory


def test_bressen(bressen_dir):
    gdf = read_directory(bressen_dir)
    assert isinstance(gdf, GeoDataFrame)
    assert len(gdf) == 10
